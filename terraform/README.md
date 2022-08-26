# DjangoGCP Terraform Configuration

The purpose of this configuration is to maintain a set of resources that can be used for
development and integration testing of django-gcp with live resources on Google Cloud.

It's already proven invaluable for testing and development of the tasks module.

We're currently learning terraform and expanding our DevOps expertise, so expect our workflows
to change dramatically in this area.

In the meaantime, used with a different project ID, performing a `terraform apply`
on a fresh GCP project with this configuration (supply the project ID as a variable) should
give you the resources required to run the management tasks to demonstrate the example test
server (you'll need to manage service accounts yourself at the time of writing).

It's a work in progress so any contributions in this area are very welcome.
