
resource "google_service_account" "github_actions_service_account" {
  account_id   = "github-actions"
  description  = "Allow GitHub Actions to deploy code onto resources and run integration tests and jobs via reverse shelling."
  display_name = "github-actions"
  project      = var.project
}


locals {
  github_actions_service_account = {
    email            = google_service_account.github_actions_service_account.email,
    member_signature = "serviceAccount:${google_service_account.github_actions_service_account.email}"
  }
}


resource "google_service_account" "invoker" {
  account_id   = "invoker"
  description  = "Invokes django-gcp endpoints (tasks, subscriber tasks, events, workflows) with an OIDC identity token during live integration tests."
  display_name = "invoker"
  project      = var.project
}


# Allow live integration tests to mint OIDC identity tokens as the invoker service account
resource "google_service_account_iam_binding" "invoker_token_creators" {
  service_account_id = google_service_account.invoker.name
  role               = "roles/iam.serviceAccountTokenCreator"
  members = [
    local.github_actions_service_account.member_signature,
    "serviceAccount:${google_service_account.dev_thclark.email}",
    "serviceAccount:${google_service_account.dev_lukasvinclav.email}",
  ]
}
