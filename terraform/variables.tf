
variable "github_organisation" {
  type    = string
  default = "octue"
}

variable "github_repository" {
  type    = string
  default = "octue/django-gcp"
}

# Here's how to find this:
# https://sdipesh.medium.com/find-github-repository-id-for-use-in-github-rest-api-d97edb39c2
variable "github_repository_id" {
  type = string
  default = "453015314"
}

variable "project" {
  type    = string
  default = "octue-django-gcp"
}

variable "project_number" {
  type    = string
  default = "134056372703"
}

variable "credentials_file" {
  type    = string
  default = "gcp-credentials.json"
}

variable "region" {
  type    = string
  default = "europe-west1"
}

variable "zone" {
  type    = string
  default = "europe-west1-d"
}

variable "environment" {
  type    = string
  default = "example"
}
