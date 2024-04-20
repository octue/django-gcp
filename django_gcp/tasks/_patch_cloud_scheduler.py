from ._pilot.base import GoogleCloudPilotAPI
from ._pilot.scheduler import CloudScheduler as BaseCloudScheduler


class CloudScheduler(BaseCloudScheduler):
    """Override the location setter on the CloudScheduler

    GCP pilot sets default location by accessing AppEngine.
    If a project has no AppEngine instance, a NotFound exception is caught and silently handled, returning None.

    In GCP Pilot's AppEngineBasedService mixin (used by both CloudScheduler and CloudTasks), the _set_location
    method is overridden to force use of the default value (which in this case is erroneously None), and any
    other value is disallowed.

    GCP Pilot should instead use the project description to find the defaults (or otherwise determine the region
    for cloud scheduler and tasks).

    We must therefore override the override (!!) back to use the method from the original base class,
    and set the location by explicitly passing it as a parameter.
    """

    def _set_location(self, location: str = None):
        return GoogleCloudPilotAPI._set_location(self, location)  # pylint: disable=protected-access
