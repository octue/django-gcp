
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
