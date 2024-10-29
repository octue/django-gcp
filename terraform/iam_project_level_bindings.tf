
# PROJECT LEVEL BINDINGS
# --------------------------------------------------------------
#
# TODO In a production setup you'd scope all these to the particular
# resources. But since for django-gcp development we only have three
# buckets and they're all the same, there's not a lot of point!

locals {
    members = [
        local.github_actions_service_account.member_signature
    ]
}


resource "google_project_iam_binding" "iam_serviceaccountuser" {
  project = var.project
  role    = "roles/iam.serviceAccountUser"
  members = local.members
}


resource "google_project_iam_binding" "storage_objectadmin" {
  project = var.project
  role = "roles/storage.objectAdmin"
  members = local.members
}
