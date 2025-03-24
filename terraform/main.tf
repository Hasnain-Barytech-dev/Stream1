provider "google" {
  project     = var.project_id
  region      = var.region
  credentials = var.gcp_service_account_json
}

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
  
  # You may want to configure a remote backend after initial setup
  # backend "gcs" {
  #   bucket = "eino-terraform-state"
  #   prefix = "streaming-service"
  # }
}