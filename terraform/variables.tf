try:
    # Try to use explicit credentials from environment variables
    access_key = os.environ.get('GCS_ACCESS_KEY')
    secret_key = os.environ.get('GCS_SECRET_KEY')
    endpoint_url = os.environ.get('GCS_ENDPOINT_URL', 'https://storage.googleapis.com')
    
    # Check for service account JSON in environment variables
    service_account_json = os.environ.get('GCS_SERVICE_ACCOUNT_JSON')
    
    # Check for standard credential file path
    credential_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    if service_account_json:
        # Use service account JSON from environment
        try:
            credentials_info = json.loads(service_account_json)
            credentials = service_account.Credentials.from_service_account_info(credentials_info)
            self.client = storage.Client(credentials=credentials)
            logger.info("Initialized GCS client with service account JSON from environment")
        except json.JSONDecodeError as json_err:
            logger.warning(f"Error parsing service account JSON: {str(json_err)}")
            raise
    elif credential_path and os.path.exists(credential_path):
        # Use the credentials file specified by GOOGLE_APPLICATION_CREDENTIALS
        self.client = storage.Client()
        logger.info(f"Initialized GCS client using credentials file at: {credential_path}")
    elif access_key and secret_key:
        # Use access key and secret key if provided
        # Note: This method is less preferred for GCS but included for compatibility
        from google.auth import credentials as google_credentials
        
        class CustomCredentials(google_credentials.Credentials):
            def __init__(self, access_key, secret_key):
                super(CustomCredentials, self).__init__()
                self.access_key = access_key
                self.secret_key = secret_key
                
            def apply(self, headers, token=None):
                headers['authorization'] = f'Bearer {self.access_key}'
                return headers
                
        custom_creds = CustomCredentials(access_key, secret_key)
        self.client = storage.Client(credentials=custom_creds)
        logger.info("Initialized GCS client with access key and secret key")
    else:
        # Try application default credentials
        self.client = storage.Client()
        logger.info("Initialized GCS client with application default credentials")

except Exception as e:
    # Fall back to default credentials if available
    logger.warning(f"Error initializing custom credentials: {str(e)}")
    logger.info("Falling back to default credentials")
    try:
        self.client = storage.Client()
    except Exception as default_cred_error:
        logger.error(f"Failed to initialize with default credentials: {str(default_cred_error)}")
        raise RuntimeError("Unable to initialize Google Cloud Storage client with any credential method")

variable "service_account_email" {
  description = "The email address of the service account to use for Cloud Functions"
  type        = string
  default     = "your-service-account@your-project-id.iam.gserviceaccount.com"
}
