
locals {
  service_apis = [
    "artifactregistry.googleapis.com",
    "clouderrorreporting.googleapis.com",
    "cloudscheduler.googleapis.com",
    "cloudtasks.googleapis.com",
    "eventarc.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "logging.googleapis.com",
    "pubsub.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "workflows.googleapis.com"
  ]
}


resource "google_project_service" "gcp_services" {
  for_each = toset(local.service_apis)

  project            = var.project
  service            = each.value
  disable_on_destroy = false
}
