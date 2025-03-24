"""
Logging configuration for the EINO Streaming Service.
"""

import logging
import sys
import os
from datetime import datetime

from app.config import get_settings

settings = get_settings()

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.DEBUG if settings.DEV_MODE else logging.INFO

# Get current date for log file name
current_date = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = f"logs/streaming_service_{current_date}.log"


def setup_logging():
    """
    Set up logging configuration.
    
    Returns:
        Logger instance
    """
    # Configure root logger
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILE)
        ]
    )
    
    # Set log levels for libraries to avoid excessive logs
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    
    # Create app logger
    app_logger = logging.getLogger("app")
    app_logger.setLevel(LOG_LEVEL)
    
    return app_logger


# Create logger instance
logger = setup_logging()