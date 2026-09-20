# Cloud Run

## Metadata

The [container contract for Google Cloud Run](https://cloud.google.com/run/docs/container-contract#metadata-server)
specifies an internal server providing metadata about the running service. This is useful
for:

- determining whether your app is running on Cloud Run or somewhere else,
- fetching values like the `project_id`, which are required for structured logging, and
- generating tokens that can be used to sign blobs without a private key.

To avoid writing requests to the internal server yet again, `django_gcp` provides the wrapper
class `django_gcp.metadata.CloudRunMetadata`, exposing the results as properties:

```python
from django_gcp.metadata import CloudRunMetadata

meta = CloudRunMetadata()

# On your local machine, `meta.is_cloud_run` will be False, and accessing these
# attributes will raise a NotOnCloudRunError
if meta.is_cloud_run:
    print(meta.project_id)
    print(meta.project_number)
    print(meta.region)
    print(meta.compute_instance_id)
    print(meta.email)
    print(meta.token)
```
