# You need to start with a service account called "terraform" which has both the 'editor' and 'owner' basic permissions.
# This allows it to assign permissions to resources per https://cloud.google.com/iam/docs/understanding-roles


resource "google_service_account" "dev_thclark" {
  account_id   = "dev-thclark"
  display_name = "dev-thclark"
  project      = var.project
}


resource "google_service_account" "dev_lukasvinclav" {
  account_id   = "dev-lukasvinclav"
  display_name = "dev-lukasvinclav"
  project      = var.project
}


# For iam bindings to storage buckets see terraform/storage.tf


resource "google_project_iam_binding" "errorreporting_writer" {
  project = var.project
  role    = "roles/errorreporting.writer"
  members = [
    "serviceAccount:${google_service_account.dev_thclark.email}",
    "serviceAccount:${google_service_account.dev_lukasvinclav.email}",
  ]
}


# Allow django-gcp.tasks to create and update task queues
resource "google_project_iam_binding" "cloudtasks_admin" {
  project = var.project
  role    = "roles/cloudtasks.admin"
  members = [
    "serviceAccount:${google_service_account.dev_thclark.email}",
    "serviceAccount:${google_service_account.dev_lukasvinclav.email}",
  ]
}


# Allow django-gcp.tasks to create periodic tasks in google cloud scheduler
resource "google_project_iam_binding" "cloudscheduler_admin" {
  project = var.project
  role    = "roles/cloudscheduler.admin"
  members = [
    "serviceAccount:${google_service_account.dev_thclark.email}",
    "serviceAccount:${google_service_account.dev_lukasvinclav.email}",
  ]
}
