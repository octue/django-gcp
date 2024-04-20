from .base import _CACHED_LOCATIONS, AppEngineBasedService, DiscoveryMixin, GoogleCloudPilotAPI


class AppEngine(AppEngineBasedService, DiscoveryMixin, GoogleCloudPilotAPI):
    _scopes = [
        "https://www.googleapis.com/auth/appengine.admin",
    ]

    def __init__(self, **kwargs):
        super().__init__(
            serviceName="appengine",
            version="v1",
            cache_discovery=False,
            **kwargs,
        )

    def _set_location(self, location: str = None) -> str:
        return location or self._get_default_location()

    def get_app(self, app_id: str = None):
        app_id = app_id or self.project_id
        return self._execute(
            method=self.client.apps().get,
            appsId=app_id,
        )

    def _get_default_location(self, default_zone: str = "1") -> str:
        location = _CACHED_LOCATIONS.get(self.project_id, None)

        if not location:
            app = self.get_app()
            location = app["locationId"]
            try:
                int(location[-1])
            except ValueError:
                location = app["locationId"] + default_zone
            _CACHED_LOCATIONS[self.project_id] = location
        return location


__all__ = ("AppEngine",)
