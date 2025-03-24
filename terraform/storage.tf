resource "google_storage_bucket" "raw_videos" {
  name          = var.raw_bucket_name
  location      = var.region
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  lifecycle_rule {
    condition {
      age = 30  # days
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket" "processed_videos" {
  name          = var.processed_bucket_name
  location      = var.region
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  # No lifecycle rule for processed videos to keep them available
}