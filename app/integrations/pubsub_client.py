"""
Client for integrating with Google Cloud Pub/Sub.
"""

import json
import base64
from typing import Dict, Any, List
from google.cloud import pubsub_v1
from google.api_core.exceptions import GoogleAPIError

from app.config import get_settings
from app.core.logging import logger

settings = get_settings()


class PubSubClient:
    """
    Client for publishing and subscribing to Google Cloud Pub/Sub.
    This client handles message publication and subscription for event-driven architecture.
    """

    def __init__(self):
        """Initialize the Pub/Sub client with project ID from settings."""
        self.project_id = settings.GCP_PROJECT_ID
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()

    async def publish_message(self, topic_name: str, message: Dict[str, Any]) -> str:
        """
        Publish a message to a Pub/Sub topic.
        
        Args:
            topic_name: Name of the topic
            message: Message to publish
            
        Returns:
            Message ID
            
        Raises:
            Exception: If the message publication fails
        """
        # Format the topic path
        topic_path = self.publisher.topic_path(self.project_id, topic_name)
        
        try:
            # Convert message to JSON string
            message_json = json.dumps(message)
            
            # Encode message as bytes
            message_bytes = message_json.encode("utf-8")
            
            # Publish message
            future = self.publisher.publish(topic_path, data=message_bytes)
            
            # Get the message ID
            message_id = future.result()
            
            return message_id
        
        except GoogleAPIError as e:
            logger.error(f"Google API error when publishing message: {str(e)}")
            raise Exception(f"Failed to publish message: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error publishing message: {str(e)}")
            raise Exception(f"Failed to publish message: {str(e)}")

    async def notify_video_uploaded(self, video_id: str, user_id: str, company_id: str) -> str:
        """
        Notify that a video has been uploaded and needs processing.
        
        Args:
            video_id: ID of the uploaded video
            user_id: ID of the user who uploaded the video
            company_id: ID of the company the video belongs to
            
        Returns:
            Message ID
            
        Raises:
            Exception: If the notification fails
        """
        message = {
            "event_type": "video_uploaded",
            "video_id": video_id,
            "user_id": user_id,
            "company_id": company_id,
            "timestamp": int(import_module("time").time())
        }
        
        return await self.publish_message("video-events", message)

    async def notify_video_processed(self, video_id: str, status: str) -> str:
        """
        Notify that a video has been processed.
        
        Args:
            video_id: ID of the processed video
            status: Processing status ("success" or "error")
            
        Returns:
            Message ID
            
        Raises:
            Exception: If the notification fails
        """
        message = {
            "event_type": "video_processed",
            "video_id": video_id,
            "status": status,
            "timestamp": int(import_module("time").time())
        }
        
        return await self.publish_message("video-events", message)

    async def notify_video_viewed(self, video_id: str, user_id: str) -> str:
        """
        Notify that a video has been viewed.
        
        Args:
            video_id: ID of the viewed video
            user_id: ID of the user who viewed the video
            
        Returns:
            Message ID
            
        Raises:
            Exception: If the notification fails
        """
        message = {
            "event_type": "video_viewed",
            "video_id": video_id,
            "user_id": user_id,
            "timestamp": int(import_module("time").time())
        }
        
        return await self.publish_message("video-analytics", message)

    def create_subscription(self, topic_name: str, subscription_name: str, callback) -> None:
        """
        Create a subscription to a Pub/Sub topic with a callback function.
        
        Args:
            topic_name: Name of the topic
            subscription_name: Name of the subscription
            callback: Callback function to process messages
            
        Raises:
            Exception: If the subscription creation fails
        """
        # Format the subscription path
        subscription_path = self.subscriber.subscription_path(
            self.project_id, subscription_name
        )
        
        # Define the callback wrapper
        def callback_wrapper(message):
            try:
                # Decode message data
                data = json.loads(message.data.decode("utf-8"))
                
                # Call the callback function
                callback(data)
                
                # Acknowledge the message
                message.ack()
            
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                # Don't acknowledge to allow retry
        
        try:
            # Create the subscription if it doesn't exist
            topic_path = self.publisher.topic_path(self.project_id, topic_name)
            
            try:
                self.subscriber.create_subscription(
                    request={"name": subscription_path, "topic": topic_path}
                )
            except GoogleAPIError:
                # Subscription might already exist
                pass
            
            # Subscribe to the topic
            future = self.subscriber.subscribe(subscription_path, callback_wrapper)
            
            # Log subscription
            logger.info(f"Subscribed to {subscription_path}")
            
            return future
        
        except Exception as e:
            logger.error(f"Error creating subscription: {str(e)}")
            raise Exception(f"Failed to create subscription: {str(e)}")

    async def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the Pub/Sub service.
        
        Returns:
            Health status
        """
        try:
            # Try to list topics to check health
            project_path = f"projects/{self.project_id}"
            self.publisher.list_topics(request={"project": project_path})
            
            return {
                "status": "ok",
                "details": "Pub/Sub service is healthy"
            }
        
        except Exception as e:
            logger.error(f"Pub/Sub health check failed: {str(e)}")
            return {
                "status": "error",
                "details": str(e)
            }


# Import time module - used in methods but imported here to avoid circular imports
from importlib import import_module