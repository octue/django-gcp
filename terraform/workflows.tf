
resource "google_workflows_workflow" "sample_workflow" {
  name        = "sample-workflow"
  region      = var.region
  description = "Import a KMZ file via a Cloud Run job"
  # The workflow runs as the invoker service account, so any callbacks it makes into a django-gcp
  # application present an OIDC identity token for that account.
  service_account = google_service_account.invoker.email
  source_contents = file("${path.module}/workflows/sample_workflow.yml")
  depends_on      = [google_project_service.gcp_services]
}
