"""
Google Cloud Storage utilities for video processing.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from google.cloud import storage
from google.oauth2 import service_account

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GCSClient:
    """
    Client for Google Cloud Storage operations.
    Uses provided credentials from environment or service account key.
    """
    
    def __init__(self):
        """
        Initialize the GCS client using credentials.
        Reads from environment variables or uses default credentials.
        """
        try:
            # Try to use explicit credentials first
            access_key = os.environ.get('GCS_ACCESS_KEY')
            secret_key = os.environ.get('GCS_SECRET_KEY')
            endpoint_url = os.environ.get('GCS_ENDPOINT_URL', 'https://storage.googleapis.com')
    
    # Check for service account key file in environment
            service_account_json = os.environ.get('GCS_SERVICE_ACCOUNT_JSON')
            
            if service_account_json:
                # Use service account JSON from environment
                credentials_info = json.loads(service_account_json)
                credentials = service_account.Credentials.from_service_account_info(credentials_info)
                self.client = storage.Client(credentials=credentials)
                logger.info("Initialized GCS client with service account JSON from environment")
            elif os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            # Use the application default credentials file path
                self.client = storage.Client()
                logger.info("Initialized GCS client with application default credentials")
                
            else:    
                self.client = storage.Client(credentials=credentials)
                logger.info("Initialized GCS client with built-in service account credentials")
        
        except Exception as e:
            # Fall back to default credentials if available
            logger.warning(f"Error initializing custom credentials: {str(e)}")
            logger.info("Falling back to default credentials")
            self.client = storage.Client()
    
    def upload_file(self, local_path: str, gcs_path: str) -> str:
        """
        Upload a file to Google Cloud Storage.
        
        Args:
            local_path: Path to the local file
            gcs_path: Destination path in GCS (bucket/path/to/file)
            
        Returns:
            GCS URI of the uploaded file
        """
        try:
            # Parse bucket and object path
            parts = gcs_path.split('/', 1)
            if len(parts) < 2:
                raise ValueError(f"Invalid GCS path: {gcs_path}. Expected format: bucket/path/to/file")
            
            bucket_name, object_name = parts
            
            # Get bucket and blob
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            
            # Upload file
            blob.upload_from_filename(local_path)
            
            logger.info(f"Uploaded {local_path} to gs://{gcs_path}")
            
            return f"gs://{gcs_path}"
        
        except Exception as e:
            logger.error(f"Error uploading file to GCS: {str(e)}")
            raise
    
    def download_file(self, gcs_path: str, local_path: str) -> str:
        """
        Download a file from Google Cloud Storage.
        
        Args:
            gcs_path: Source path in GCS (bucket/path/to/file)
            local_path: Path to save the file locally
            
        Returns:
            Local path of the downloaded file
        """
        try:
            # Parse bucket and object path
            parts = gcs_path.split('/', 1)
            if len(parts) < 2:
                raise ValueError(f"Invalid GCS path: {gcs_path}. Expected format: bucket/path/to/file")
            
            bucket_name, object_name = parts
            
            # Get bucket and blob
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download file
            blob.download_to_filename(local_path)
            
            logger.info(f"Downloaded gs://{gcs_path} to {local_path}")
            
            return local_path
        
        except Exception as e:
            logger.error(f"Error downloading file from GCS: {str(e)}")
            raise
    
    def create_signed_url(self, gcs_path: str, expiration: int = 3600) -> str:
        """
        Create a signed URL for a file in GCS.
        
        Args:
            gcs_path: Path in GCS (bucket/path/to/file)
            expiration: URL expiration time in seconds
            
        Returns:
            Signed URL for the file
        """
        try:
            # Parse bucket and object path
            parts = gcs_path.split('/', 1)
            if len(parts) < 2:
                raise ValueError(f"Invalid GCS path: {gcs_path}. Expected format: bucket/path/to/file")
            
            bucket_name, object_name = parts
            
            # Get bucket and blob
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            
            # Create signed URL
            url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="GET"
            )
            
            return url
        
        except Exception as e:
            logger.error(f"Error creating signed URL: {str(e)}")
            raise
    
    def list_files(self, gcs_path: str, prefix: Optional[str] = None) -> List[str]:
        """
        List files in a GCS bucket or directory.
        
        Args:
            gcs_path: Path in GCS (bucket/optional/prefix)
            prefix: Additional prefix to filter by
            
        Returns:
            List of file paths
        """
        try:
            # Parse bucket and optional prefix
            parts = gcs_path.split('/', 1)
            bucket_name = parts[0]
            path_prefix = parts[1] if len(parts) > 1 else ""
            
            if prefix:
                if path_prefix:
                    path_prefix = f"{path_prefix}/{prefix}"
                else:
                    path_prefix = prefix
            
            # Get bucket
            bucket = self.client.bucket(bucket_name)
            
            # List blobs
            blobs = bucket.list_blobs(prefix=path_prefix)
            
            # Extract paths
            file_paths = [f"{bucket_name}/{blob.name}" for blob in blobs]
            
            return file_paths
        
        except Exception as e:
            logger.error(f"Error listing files in GCS: {str(e)}")
            raise
    
    def delete_file(self, gcs_path: str) -> None:
        """
        Delete a file from GCS.
        
        Args:
            gcs_path: Path in GCS (bucket/path/to/file)
        """
        try:
            # Parse bucket and object path
            parts = gcs_path.split('/', 1)
            if len(parts) < 2:
                raise ValueError(f"Invalid GCS path: {gcs_path}. Expected format: bucket/path/to/file")
            
            bucket_name, object_name = parts
            
            # Get bucket and blob
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            
            # Delete blob
            blob.delete()
            
            logger.info(f"Deleted gs://{gcs_path}")
        
        except Exception as e:
            logger.error(f"Error deleting file from GCS: {str(e)}")
            raise