resource "google_storage_bucket" "function_source" {
  name     = "eino-function-source"
  location = var.region
}

# Zip the source code for the Cloud Function
data "archive_file" "process_video_source" {
  type        = "zip"
  source_dir  = "../cloud_functions/process_video"
  output_path = "function-source/process_video.zip"
}

# Upload the source code to GCS
resource "google_storage_bucket_object" "process_video_archive" {
  name   = "function-source/process_video_${data.archive_file.process_video_source.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.process_video_source.output_path
}

# Create the Cloud Function for video processing
resource "google_cloudfunctions_function" "process_video" {
  name        = var.video_processing_function
  description = "Process uploaded videos into HLS/DASH format"
  runtime     = "python38"
  
  available_memory_mb   = 2048
  source_archive_bucket = google_storage_bucket.function_source.name
  source_archive_object = google_storage_bucket_object.process_video_archive.name
  timeout               = 540  # 9 minutes
  entry_point           = "process_video"
  
  event_trigger {
    event_type = "google.storage.object.finalize"
    resource   = google_storage_bucket.raw_videos.name
  }

  environment_variables = {
    OUTPUT_BUCKET = google_storage_bucket.processed_videos.name
    GCP_PROJECT_ID = var.project_id
    FFMPEG_THREADS = "4"
  }

  service_account_email = var.service_account_email
}

# Zip the source code for the thumbnail generation Cloud Function
data "archive_file" "generate_thumbnails_source" {
  type        = "zip"
  source_dir  = "../cloud_functions/generate_thumbnails"
  output_path = "function-source/generate_thumbnails.zip"
}

# Upload the source code to GCS
resource "google_storage_bucket_object" "generate_thumbnails_archive" {
  name   = "function-source/generate_thumbnails_${data.archive_file.generate_thumbnails_source.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.generate_thumbnails_source.output_path
}

# Create the Cloud Function for thumbnail generation
resource "google_cloudfunctions_function" "generate_thumbnails" {
  name        = var.thumbnail_generation_function
  description = "Generate thumbnails for uploaded videos"
  runtime     = "python38"
  
  available_memory_mb   = 1024
  source_archive_bucket = google_storage_bucket.function_source.name
  source_archive_object = google_storage_bucket_object.generate_thumbnails_archive.name
  timeout               = 300  # 5 minutes
  entry_point           = "generate_thumbnails"
  
  event_trigger {
    event_type = "google.storage.object.finalize"
    resource   = google_storage_bucket.raw_videos.name
  }

  environment_variables = {
    OUTPUT_BUCKET = google_storage_bucket.processed_videos.name
    GCP_PROJECT_ID = var.project_id
  }

  service_account_email = var.service_account_email
}