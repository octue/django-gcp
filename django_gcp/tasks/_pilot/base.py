import abc
import os
from typing import Dict, List, Tuple, Union

from google import auth
from google.auth import iam
from google.auth.credentials import Credentials
from google.auth.impersonated_credentials import Credentials as ImpersonatedCredentials
from google.auth.transport import requests
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.protobuf.duration_pb2 import Duration
from googleapiclient.discovery import Resource, build

DEFAULT_PROJECT = os.environ.get("GCP_PROJECT", None)
DEFAULT_LOCATION = os.environ.get("GCP_LOCATION", None)
DEFAULT_SERVICE_ACCOUNT = os.environ.get("GCP_SERVICE_ACCOUNT", None)

TOKEN_URI = "https://accounts.google.com/o/oauth2/token"

AuthType = Tuple[Credentials, str]
ImpersonatedAuthType = Tuple[ImpersonatedCredentials, str]


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
        return location or DEFAULT_LOCATION

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

    def _as_duration(self, seconds) -> Duration:
        return Duration(seconds=seconds) if seconds else None

    def _project_path(self, project_id: str = None) -> str:
        return f"projects/{project_id or self.project_id}"

    def _location_path(self, project_id: str = None, location: str = None) -> str:
        project_path = self._project_path(project_id=project_id)
        return f"{project_path}/locations/{location or self.location}"
