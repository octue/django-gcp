import abc
import json
import logging
import os
from typing import Any, Callable, Dict, Generator, List, Tuple, Union

from google import auth
from google.auth import iam
from google.auth.credentials import Credentials
from google.auth.impersonated_credentials import Credentials as ImpersonatedCredentials
from google.auth.transport import requests
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.protobuf.duration_pb2 import Duration
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from requests import Response

from . import exceptions

DEFAULT_PROJECT = os.environ.get("GCP_PROJECT", None)
DEFAULT_LOCATION = os.environ.get("GCP_LOCATION", None)
DEFAULT_SERVICE_ACCOUNT = os.environ.get("GCP_SERVICE_ACCOUNT", None)

TOKEN_URI = "https://accounts.google.com/o/oauth2/token"

PolicyType = Dict[str, Any]
AuthType = Tuple[Credentials, str]
ImpersonatedAuthType = Tuple[ImpersonatedCredentials, str]
ResourceType = Dict[str, Any]

logger = logging.getLogger()

_CACHED_LOCATIONS = {}  # TODO: Implement a smarter solution for caching project's location


MINIMAL_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
]


class GoogleCloudPilotAPI(abc.ABC):
    _client_class = None
    _scopes: List[str] = []
    _iam_roles: List[str] = []
    _cached_credentials: AuthType = None
    _service_name = None
    _google_managed_service = False  # Service agent requires impersonation

    def __init__(
        self,
        subject: str = None,
        location: str = None,
        project_id: str = None,
        impersonate_account: str = None,
        credentials: Credentials = None,
        **kwargs,
    ):
        if credentials:
            self.credentials, credential_project_id = credentials, getattr(credentials, "project_id", None)
        else:
            self.credentials, credential_project_id = self._set_credentials(
                subject=subject,
                impersonate_account=impersonate_account or DEFAULT_SERVICE_ACCOUNT,
            )
        self.project_id = self._set_project_id(project_id=project_id, credential_project_id=credential_project_id)

        self.client = self._build_client(**kwargs)

        self.location = self._set_location(location=location)

    def _get_client_extra_kwargs(self):
        return {}

    def _build_client(self, **kwargs) -> Union[Resource, _client_class]:
        kwargs.update(self._get_client_extra_kwargs())

        return (self._client_class or build)(credentials=self.credentials, **kwargs)

    def _set_project_id(self, project_id: str, credential_project_id: str) -> str:
        return project_id or DEFAULT_PROJECT or credential_project_id

    def _set_location(self, location: str = None) -> str:
        return location or DEFAULT_LOCATION or self._get_project_default_location()

    @classmethod
    def _impersonate_account(
        cls,
        credentials: Credentials,
        service_account: str,
        scopes: List[str],
    ) -> ImpersonatedAuthType:
        credentials = ImpersonatedCredentials(
            source_credentials=credentials,
            target_principal=service_account,
            target_scopes=scopes,
            delegates=[],
        )

        # Fetch project from service account
        # Since we are impersonating this service account, use it's own project
        # TODO: regex this
        project_id = credentials.service_account_email.split("@")[-1].replace(".iam.gserviceaccount.com", "")

        return credentials, project_id

    @classmethod
    def _delegated_credential(
        cls,
        credentials: Credentials,
        subject: str,
        scopes: List[str],
    ) -> ServiceAccountCredentials:
        try:
            admin_credentials = credentials.with_subject(subject).with_scopes(scopes)
        except AttributeError:
            # When inside GCP, the credentials provided by the metadata service are immutable.
            # https://github.com/GoogleCloudPlatform/professional-services/tree/master/examples/gce-to-adminsdk

            request = requests.Request()
            credentials.refresh(request)

            # Create an IAM signer using the bootstrap credentials.
            signer = iam.Signer(
                request,
                credentials,
                credentials.service_account_email,
            )
            # Create OAuth 2.0 Service Account credentials using the IAM-based
            # signer and the bootstrap_credential's service account email.
            admin_credentials = ServiceAccountCredentials(
                signer,
                credentials.service_account_email,
                TOKEN_URI,
                scopes=scopes,
                subject=subject,
            )

        return admin_credentials

    @classmethod
    def _set_credentials(cls, subject: str = None, impersonate_account: str = None) -> AuthType:
        # Speed up consecutive authentications
        # TODO: check if this does not break multiple client usage
        all_scopes = MINIMAL_SCOPES + cls._scopes
        if not cls._cached_credentials:
            credentials, project_id = auth.default(scopes=all_scopes)
            cls._cached_credentials = credentials, project_id
        else:
            credentials, project_id = cls._cached_credentials

        if impersonate_account and getattr(credentials, "service_account_email") != impersonate_account:
            credentials, impersonated_project_id = cls._impersonate_account(
                credentials=credentials,
                service_account=impersonate_account,
                scopes=all_scopes,
            )
            project_id = impersonated_project_id or project_id

        if subject:
            credentials = cls._delegated_credential(credentials=credentials, subject=subject, scopes=all_scopes)

        return credentials, (project_id or getattr(credentials, "project_id", None))

    def get_oidc_token(self, audience: str = None) -> Dict[str, Dict[str, str]]:
        oidc_token = {"service_account_email": self.credentials.service_account_email}
        if audience:
            # TODO: make sure that, if URL, the query params are removed
            oidc_token["audience"] = audience
        return {"oidc_token": oidc_token}

    async def set_up_permissions(self, email: str, project_id: str = None) -> None:
        from .resource import ResourceManager, ServiceAgent  # pylint: disable=import-outside-toplevel

        rm = ResourceManager()  # pylint: disable=invalid-name
        for role in self._iam_roles:
            await rm.add_member(
                email=email,
                role=role,
                project_id=project_id or self.project_id,
            )

        if self._google_managed_service:
            email = ServiceAgent.get_email(
                service_name=f"{self._service_name} Service Account",
                project_id=self.project_id,
            )

            await ResourceManager().allow_impersonation(
                email=email,
                project_id=project_id,
            )

    def _get_project_number(self, project_id: str) -> int:
        from .resource import ResourceManager  # pylint: disable=import-outside-toplevel

        project = ResourceManager().get_project(project_id=project_id)
        return project["projectNumber"]

    def _as_duration(self, seconds) -> Duration:
        return Duration(seconds=seconds) if seconds else None

    @classmethod
    def build_from(cls, client: "GoogleCloudPilotAPI", project_id: str = None):
        return cls(
            credentials=client.credentials,
            project_id=project_id or client.project_id,
        )

    def _get_project_default_location(self, project_id: str = None) -> Union[str, None]:
        location = _CACHED_LOCATIONS.get(project_id or self.project_id, None)
        if location:
            return location

        from .app_engine import AppEngine  # pylint: disable=import-outside-toplevel

        try:
            app_engine = AppEngine.build_from(client=self, project_id=project_id)
            return app_engine.location
        except exceptions.NotFound:
            return None

    def _project_path(self, project_id: str = None) -> str:
        return f"projects/{project_id or self.project_id}"

    def _location_path(self, project_id: str = None, location: str = None) -> str:
        project_path = self._project_path(project_id=project_id)
        return f"{project_path}/locations/{location or self.location}"

    @property
    def _session(self) -> requests.AuthorizedSession:
        return requests.AuthorizedSession(credentials=self.credentials)

    @property
    def _base_url(self) -> str:
        metadata = self.client._rootDesc
        return f"{metadata['baseUrl']}{metadata['version']}"


class AccountManagerMixin:
    def _as_member(self, email: str) -> str:
        if email == "allUsers":
            return email
        is_service_account = email.endswith(".gserviceaccount.com")
        prefix = "serviceAccount" if is_service_account else "member"
        return f"{prefix}:{email}"

    def _make_public(self, role: str, policy: Dict) -> Dict:
        return self._bind_email_to_policy(email="allUsers", role=role, policy=policy)

    def _make_private(self, role: str, policy: Dict) -> Dict:
        return self._unbind_email_from_policy(email="allUsers", role=role, policy=policy)

    def _bind_email_to_policy(self, email: str, role: str, policy: Dict) -> Dict:
        new_policy = policy.copy()

        role_id = role if (role.startswith("organizations/") or role.startswith("roles/")) else f"roles/{role}"
        member = self._as_member(email=email)

        try:
            binding = next(b for b in new_policy["bindings"] if b["role"] == role_id)
            if member in binding["members"]:
                return new_policy
            binding["members"].append(member)
        except (StopIteration, KeyError):
            binding = {"role": role_id, "members": [member]}

            new_bindings = new_policy.get("bindings", []).copy()
            new_bindings.append(binding)

            new_policy["bindings"] = new_bindings

        if "version" not in new_policy:
            new_policy["version"] = 1  # TODO: handle version 2 and 3 as its conditional roles
        return new_policy

    def _unbind_email_from_policy(self, email: str, role: str, policy: Dict):
        role_id = f"roles/{role}"
        member = self._as_member(email=email)

        try:
            binding = next(b for b in policy["bindings"] if b["role"] == role_id)
            if member not in binding["members"]:
                return policy
            binding["members"].remove(member)
        except (StopIteration, KeyError):
            pass
        return policy


class AppEngineBasedService:
    # This mixin must be used for all clients that uses GCP's resources that are based on App Engine
    # such as Cloud Scheduler.
    # They have a peculiar behaviour because the App Engine, when enabled the first time,
    # is created in a region and this region cannot be changed ever.
    # So these clients cannot just choose a desired region to work on, they must use the App Engine's
    # previously chosen region.
    def _set_location(self, location: str = None):
        project_location = self._get_project_default_location()

        explicit_location = location
        if explicit_location and explicit_location != project_location:
            logger.warning(
                f"Location {explicit_location} cannot be set in {self.__class__.__name__}. "
                f"It uses App Engine's default location for your project: {project_location}"
            )
        return project_location


def friendly_http_error(func):
    _reasons = {
        "notFound": exceptions.NotFound,
        "deleted": exceptions.AlreadyDeleted,
        "forbidden": exceptions.NotAllowed,
        "duplicate": exceptions.AlreadyExists,
        "push.webhookUrlUnauthorized": exceptions.PushWebhookInvalid,
        "channelIdNotUnique": exceptions.ChannelIdNotUnique,
        "notACalendarUser": exceptions.NotACalendarUser,
        "quotaExceeded": exceptions.QuotaExceeded,
        "invalid": exceptions.ValidationError,
    }
    _statuses = {
        "INVALID_ARGUMENT": exceptions.ValidationError,
        "PERMISSION_DENIED": exceptions.NotAllowed,
        "NOT_FOUND": exceptions.NotFound,
        "ALREADY_EXISTS": exceptions.AlreadyExists,
        "INVALID_PASSWORD": exceptions.InvalidPassword,
        "EMAIL_NOT_FOUND": exceptions.NotFound,
        "MISSING_ID_TOKEN": exceptions.MissingUserIdentification,
        "FAILED_PRECONDITION": exceptions.FailedPrecondition,
    }

    def inner_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HttpError as exc:
            error_content = json.loads(exc.content)
            if "issue" in error_content:
                raise exceptions.OperationError(errors=error_content["issue"]) from exc

            errors = error_content["error"]
            exception_klass = None
            details = ""

            if "errors" in errors:
                main_error = errors["errors"][0]["reason"]
                exception_klass = _reasons.get(main_error, None)
                details = errors.get("message", "")

            if not exception_klass and "message" in errors:
                exception_klass = _statuses.get(errors["message"], None)

            if not exception_klass and "status" in errors:
                exception_klass = _statuses.get(errors["status"], None)
                details = f"{errors['code']}: {errors['message']}"

            if exception_klass:
                raise exception_klass(details) from exc
            raise exc

    return inner_function


class DiscoveryMixin:
    @friendly_http_error
    def _execute(self, method: Callable, **kwargs) -> ResourceType:
        call = method(**kwargs)
        if isinstance(call, Response):
            call.raise_for_status()
            return call.json()
        return method(**kwargs).execute()

    def _list(
        self,
        method: Callable,
        result_key: str = "items",
        params: Dict[str, Any] = None,
    ) -> Generator[ResourceType, None, None]:
        results = self._execute(
            method=method,
            **params,
        )
        for item in results.get(result_key, []):
            yield item

    def _paginate(
        self,
        method: Callable,
        result_key: str = "items",
        params: Dict[str, Any] = None,
        order_by: str = None,
        limit: int = None,
    ) -> Generator[ResourceType, None, None]:
        page_token = None
        params = params or {}

        if order_by:
            if order_by.startswith("-"):
                params["sortOrder"] = "DESCENDING"
                order_by = order_by[1:]
            params["orderBy"] = order_by

        if limit:
            params["maxResults"] = limit

        while True:
            results = self._execute(
                method=method,
                **params,
                pageToken=page_token,
            )
            for item in results.get(result_key, []):
                yield item

            page_token = results.get("nextPageToken")
            if not page_token:
                break
