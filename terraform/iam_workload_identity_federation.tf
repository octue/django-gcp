
resource "google_iam_workload_identity_pool" "github_actions_pool" {
    display_name              = "github-actions-pool"
    project                   = var.project
    workload_identity_pool_id = "github-actions-pool"
}


resource "google_iam_workload_identity_pool_provider" "github_actions_provider" {
    display_name                       = "Github Actions Provider"
    project                            = var.project_number
    workload_identity_pool_id          = "github-actions-pool"
    workload_identity_pool_provider_id = "github-actions-provider"
    attribute_condition = <<EOT
        attribute.repository == "${var.github_repository}"
    EOT
    attribute_mapping = {
        "google.subject"       = "assertion.sub"
        "attribute.actor"      = "assertion.actor"
        "attribute.aud"        = "assertion.aud"
        "attribute.repository" = "assertion.repository"
    }
    oidc {
        issuer_uri        = "https://token.actions.githubusercontent.com"
    }
}


data "google_iam_policy" "github_actions_workload_identity_pool_policy" {
  binding {
    role = "roles/iam.workloadIdentityUser"
    members = [
      "principalSet://iam.googleapis.com/projects/${var.project_number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github_actions_pool.workload_identity_pool_id}/attribute.repository/${var.github_repository}"
    ]
  }
}


// Allow a machine under Workload Identity Federation to act as the given service account
resource "google_service_account_iam_policy" "github_actions_workload_identity_service_account_policy" {
  service_account_id = google_service_account.github_actions_service_account.name
  policy_data        = data.google_iam_policy.github_actions_workload_identity_pool_policy.policy_data
}
