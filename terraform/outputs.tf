output "raw_videos_bucket" {
  value       = google_storage_bucket.raw_videos.name
  description = "The name of the bucket where raw videos are stored"
}

output "processed_videos_bucket" {
  value       = google_storage_bucket.processed_videos.name
  description = "The name of the bucket where processed videos are stored"
}

output "process_video_function" {
  value       = google_cloudfunctions_function.process_video.name
  description = "The name of the video processing function"
}

output "generate_thumbnails_function" {
  value       = google_cloudfunctions_function.generate_thumbnails.name
  description = "The name of the thumbnail generation function"
}

output "service_account_email" {
  value       = var.service_account_email
  description = "The email of the service account used by the streaming service"
}