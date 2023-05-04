

# Add a static bucket (public contents)
resource "google_storage_bucket" "static_assets" {
  name                        = "${var.environment}-static-assets"
  location                    = "EU"
  force_destroy               = true
  uniform_bucket_level_access = true
  cors {
    # WARNING: Do not set this to * for production buckets; it should be limited to the origin of your site
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
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
#   Note: CORS are set to allow direct uploads, enabling upload of files
#         larger than 32 mb (Cloud Run has a hard limit on file upload size)
resource "google_storage_bucket" "media_assets" {
  name                        = "${var.environment}-media-assets"
  location                    = "EU"
  force_destroy               = true
  uniform_bucket_level_access = false
  cors {
    # WARNING: Do not set this to * for production buckets; it should be limited to the origin of your site
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
}


# Allows generation of signed urls to upload objects
resource "google_storage_bucket_iam_binding" "media_assets_object_admin" {
  bucket = google_storage_bucket.media_assets.name
  role   = "roles/storage.objectAdmin"
  members = [
    "serviceAccount:${google_service_account.dev_thclark.email}"
  ]
}


# Add an `extra` bucket (eg private datalake with object versioning enabled)
#   Note: CORS are set to allow direct uploads, enabling upload of files
#         larger than 32 mb (Cloud Run has a hard limit on file upload size)
resource "google_storage_bucket" "extra_versioned_assets" {
  name                        = "${var.environment}-extra-versioned-assets"
  location                    = "EU"
  force_destroy               = true
  uniform_bucket_level_access = false
  cors {
    # WARNING: Do not set this to * for production buckets; it should be limited to the origin of your site
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
  versioning {
    enabled = true
  }
}


# Allows generation of signed urls to upload objects
resource "google_storage_bucket_iam_binding" "extra_versioned_assets_object_admin" {
  bucket = google_storage_bucket.extra_versioned_assets.name
  role   = "roles/storage.objectAdmin"
  members = [
    "serviceAccount:${google_service_account.dev_thclark.email}"
  ]
}
