

# Add a static bucket (public contents)
resource "google_storage_bucket" "static_assets" {
  name                        = "${var.environment}-static-assets"
  location                    = "EU"
  force_destroy               = true
  uniform_bucket_level_access = true
}

# Make static bucket contents public
resource "google_storage_bucket_iam_binding" "static_assets_object_viewer" {
  bucket = google_storage_bucket.static_assets.name
  role   = "roles/storage.objectViewer"
  members = [
    "allUsers"
  ]
}

# Add a media bucket (private contents)
resource "google_storage_bucket" "media_assets" {
  name                        = "${var.environment}-media-assets"
  location                    = "EU"
  force_destroy               = true
  uniform_bucket_level_access = false
}
