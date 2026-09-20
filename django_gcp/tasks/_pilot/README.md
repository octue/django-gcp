# About Pilot

This module contains minimal clients for Cloud Tasks, Cloud Scheduler and Pub/Sub, ported from the third party library gcp_pilot. We ported them because gcp_pilot imposed an unreasonably tight python dependency range and shipped no release notes, which made it impractical to depend on.

Only the code used internally by the tasks module is retained; everything else from the original port has been removed.

YOU SHOULD NOT IMPORT FROM OR PATCH THIS MODULE, IT IS PRIVATE AND WILL BE REMOVED WITHOUT NOTIFYING BREAKING CHANGES.
