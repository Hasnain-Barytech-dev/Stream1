

# Note: We're not creating a new service account since it already exists
# If you need to update IAM permissions, uncomment and modify these resources

# resource "google_project_iam_member" "storage_admin" {
#   project = var.project_id
#   role    = "roles/storage.admin"
#   member  = "serviceAccount:${var.service_account_email}"
# }

# resource "google_project_iam_member" "functions_invoker" {
#   project = var.project_id
#   role    = "roles/cloudfunctions.invoker"
#   member  = "serviceAccount:${var.service_account_email}"
# }

resource "google_storage_bucket_iam_binding" "raw_videos_binding" {
  bucket = google_storage_bucket.raw_videos.name
  role   = "roles/storage.objectAdmin"
  members = [
    "serviceAccount:${var.service_account_email}",
  ]
}

resource "google_storage_bucket_iam_binding" "processed_videos_binding" {
  bucket = google_storage_bucket.processed_videos.name
  role   = "roles/storage.objectAdmin"
  members = [
    "serviceAccount:${var.service_account_email}",
  ]
}