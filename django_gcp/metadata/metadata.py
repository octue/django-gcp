from functools import cached_property
from urllib.error import URLError
from urllib.request import Request, urlopen

from ..exceptions import NotOnCloudRunError

ENDPOINTS = {
    "project_id": "computeMetadata/v1/project/project-id",
    "project_number": "/computeMetadata/v1/project/numeric-project-id",
    "region": "/computeMetadata/v1/instance/region",
    "compute_instance_id": "/computeMetadata/v1/instance/id",
    "email": "/computeMetadata/v1/instance/service-accounts/default/email",
    "token": "/computeMetadata/v1/instance/service-accounts/default/token",
}


class CloudRunMetadata:
    """A helper class for fetching Cloud Run internal service metadata

    Based on: https://cloud.google.com/run/docs/container-contract#metadata-server

    Works while running on Cloud Run instances, excepts when not running under
    Google infrastructure.

    The email / token properties refer to / use the *runtime* service account,
    NOT the *default* service account as is suggested by the endpoint naming
    convention. See https://stackoverflow.com/questions/75770844/does-this-cloud-run-metadata-server-endpoint-provide-the-default-service-account?noredirect=1#comment133690781_75770844
    """

    def _fetch(self, endpoint):
        url = f"http://metadata.google.internal/{endpoint}"
        req = Request(url)
        req.add_header("Metadata-Flavor", "Google")
        try:
            return urlopen(req).read().decode()
        except URLError as exc:
            raise NotOnCloudRunError(
                "Attempted to fetch GCP-internal metadata, this can only be done when being run on Google Compute Engine services"
            ) from exc

    @cached_property
    def is_cloud_run(self):
        """True if currently running on Cloud Run infrastructure, False otherwise"""
        try:
            self._fetch(ENDPOINTS["project-id"])
            return True
        except NotOnCloudRunError:
            return False

    @cached_property
    def project_id(self):
        """Project ID of the project the Cloud Run service or job belongs to"""
        return self._fetch(ENDPOINTS["project_id"])

    @cached_property
    def project_number(self):
        """Project number of the project the Cloud Run service or job belongs to"""
        return self._fetch(ENDPOINTS["project_number"])

    @cached_property
    def region(self):
        """Region of this Cloud Run service or job"""
        # GCP Metadata server returns projects/PROJECT-NUMBER/regions/REGION
        return self._fetch(ENDPOINTS["region"]).split("/")[-1]

    @cached_property
    def container_instance_id(self):
        """Unique identifier of the container instance (also available in logs)"""
        return self._fetch(ENDPOINTS["container_instance_id"])

    @cached_property
    def email(self):
        """Email for the runtime service account of this Cloud Run service or job."""
        return self._fetch(ENDPOINTS["email"])

    @property
    def token(self):
        """Generates an OAuth2 access token for the service account of this Cloud Run service or job.
        The Cloud Run service agent is used to fetch a token. This endpoint will
        return a JSON response with an access_token attribute.

        Unlike the other endpoints, `token` is NOT cached since the token may rotate within
        the container lifespan.
        """
        return self._fetch(ENDPOINTS["token"])
