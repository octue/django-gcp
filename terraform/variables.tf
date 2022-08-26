variable "project" {
  type    = string
  default = "octue-django-gcp"
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
