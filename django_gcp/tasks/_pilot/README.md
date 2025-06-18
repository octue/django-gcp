# About Pilot

This module is extracted from gcp_pilot, a third party library.

We were relying on gcp_pilot, which is mostly well engineered, to provide a better abstraction than the google cloud apis themselves. However, the authors of gcp_pilot keep shifting their python dependency range - it's super tight for no clear reason and that prevents downstream users from being able to maintain systems. It's a headache.

We also have the problem that they don't bother producing any release notes, so updating is a bear.

But, we've got very little time right now, so are simply porting some of their code here for the time being to overcome the dependency problems. We will come back and refactor the required aspects to remove this private module.

YOU SHOULD NOT IMPORT FROM OR PATCH THIS MODULE, IT IS PRIVATE AND WILL BE REMOVED WITHOUT NOTIFYING BREAKING CHANGES.
