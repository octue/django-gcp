
resource "google_workflows_workflow" "sample_workflow" {
  name        = "sample-workflow"
  region      = var.region
  description = "Import a KMZ file via a Cloud Run job"
  #   service_account = assign a service account with roles attached if you need your workflow to do complex things like triggering jobs or processing files
  source_contents = file("${path.module}/workflows/sample_workflow.yml")
  depends_on      = [google_project_service.gcp_services]
}
