# You need to start with a service account called "terraform" which has both the 'editor' and 'owner' basic permissions.
# This allows it to assign permissions to resources per https://cloud.google.com/iam/docs/understanding-roles
#
# Start by assigning the permissions that it needs itself

# Allows django-gcp.tasks to create periodic tasks for you using google cloud scheduler
# resource "google_project_iam_binding" "terraform_serviceaccount_bindings" {
#   count = length(var.terraform_serviceaccount_roles)
#   project = var.project
#   role    = var.terraform_serviceaccount_roles[count.index]
#   members = [
#     "serviceAccount:terraform@octue-django-gcp.iam.gserviceaccount.com",
#   ]
# }

resource "google_service_account" "dev_thclark" {
  account_id   = "dev-thclark"
  display_name = "dev-thclark"
  project      = "octue-django-gcp"
}


# Allows django-gcp.tasks to create periodic tasks for you using google cloud scheduler
# resource "google_project_iam_binding" "cloudscheduler_jobs_update" {
#   project = var.project
#   role    = "roles/CloudSchedulerAdmin"

#   members = [
#     "serviceAccount:${google_service_account.dev_thclark.email}",
#   ]
# }
