resource "google_cloud_tasks_queue" "primary" {
  name     = "${var.environment}-primary"
  location = var.region
}

resource "google_cloud_tasks_queue" "backup" {
  name     = "${var.environment}-backup"
  location = var.region
}
