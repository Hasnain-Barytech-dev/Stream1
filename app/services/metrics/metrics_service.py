"""
Metrics service for the EINO Streaming Service.
"""

from typing import Dict, Any, List, Optional
import time
from datetime import datetime
import json
import os
import asyncio
import aioredis
from collections import defaultdict

from app.config import get_settings
from app.core.logging import logger
from app.integrations.pubsub_client import PubSubClient

settings = get_settings()


class MetricsService:
    """
    Service for collecting and reporting metrics.
    This service tracks usage metrics like video views, upload counts, etc.
    """

    def __init__(self):
        """Initialize the metrics service with dependencies."""
        self.pubsub_client = PubSubClient()
        self.redis = None

    async def connect(self):
        """Connect to Redis if not already connected."""
        if self.redis is None:
            try:
                self.redis = await aioredis.create_redis_pool(
                    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                    password=settings.REDIS_PASSWORD,
                    encoding="utf-8"
                )
            except Exception as e:
                logger.error(f"Error connecting to Redis: {str(e)}")
                self.redis = None

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis is not None:
            self.redis.close()
            await self.redis.wait_closed()
            self.redis = None

    async def record_video_view(
        self, video_id: str, user_id: Optional[str] = None, company_id: Optional[str] = None
    ) -> None:
        """
        Record a video view event.
        
        Args:
            video_id: ID of the viewed video
            user_id: ID of the user who viewed the video (if authenticated)
            company_id: ID of the company the video belongs to
        """
        # Create event data
        event_data = {
            "video_id": video_id,
            "timestamp": int(time.time()),
            "event_type": "video_view"
        }
        
        if user_id:
            event_data["user_id"] = user_id
            
        if company_id:
            event_data["company_id"] = company_id
            
        # Record locally
        await self._record_event(event_data)
        
        # Publish to Pub/Sub
        try:
            await self.pubsub_client.notify_video_viewed(video_id, user_id or "anonymous")
        except Exception as e:
            logger.error(f"Error publishing video view event: {str(e)}")

    async def record_video_upload(
        self, video_id: str, user_id: str, company_id: str, size: int
    ) -> None:
        """
        Record a video upload event.
        
        Args:
            video_id: ID of the uploaded video
            user_id: ID of the user who uploaded the video
            company_id: ID of the company the video belongs to
            size: Size of the video in bytes
        """
        # Create event data
        event_data = {
            "video_id": video_id,
            "user_id": user_id,
            "company_id": company_id,
            "size": size,
            "timestamp": int(time.time()),
            "event_type": "video_upload"
        }
        
        # Record locally
        await self._record_event(event_data)
        
        # Update upload counters
        await self._increment_counter(f"uploads:user:{user_id}", 1)
        await self._increment_counter(f"uploads:company:{company_id}", 1)
        await self._increment_counter("uploads:total", 1)
        
        # Update storage counters
        await self._increment_counter(f"storage:user:{user_id}", size)
        await self._increment_counter(f"storage:company:{company_id}", size)
        await self._increment_counter("storage:total", size)

    async def record_video_processing_time(
        self, video_id: str, duration: float, success: bool
    ) -> None:
        """
        Record video processing time.
        
        Args:
            video_id: ID of the processed video
            duration: Processing time in seconds
            success: Whether processing was successful
        """
        # Create event data
        event_data = {
            "video_id": video_id,
            "duration": duration,
            "success": success,
            "timestamp": int(time.time()),
            "event_type": "video_processing"
        }
        
        # Record locally
        await self._record_event(event_data)
        
        # Update processing time metrics
        await self._record_timing("processing_time", duration)
        
        # Update success/failure counters
        if success:
            await self._increment_counter("processing:success", 1)
        else:
            await self._increment_counter("processing:failure", 1)

    async def get_video_views(self, video_id: str) -> int:
        """
        Get the number of views for a video.
        
        Args:
            video_id: ID of the video
            
        Returns:
            Number of views
        """
        return await self._get_counter(f"views:video:{video_id}")

    async def get_user_upload_count(self, user_id: str) -> int:
        """
        Get the number of uploads for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Number of uploads
        """
        return await self._get_counter(f"uploads:user:{user_id}")

    async def get_company_upload_count(self, company_id: str) -> int:
        """
        Get the number of uploads for a company.
        
        Args:
            company_id: ID of the company
            
        Returns:
            Number of uploads
        """
        return await self._get_counter(f"uploads:company:{company_id}")

    async def get_user_storage_usage(self, user_id: str) -> int:
        """
        Get the storage usage for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Storage usage in bytes
        """
        return await self._get_counter(f"storage:user:{user_id}")

    async def get_company_storage_usage(self, company_id: str) -> int:
        """
        Get the storage usage for a company.
        
        Args:
            company_id: ID of the company
            
        Returns:
            Storage usage in bytes
        """
        return await self._get_counter(f"storage:company:{company_id}")

    async def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get video processing statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        success_count = await self._get_counter("processing:success")
        failure_count = await self._get_counter("processing:failure")
        total_count = success_count + failure_count
        
        avg_time = await self._get_average("processing_time")
        
        return {
            "total_count": total_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": (success_count / total_count) if total_count > 0 else 0,
            "average_time": avg_time
        }

    async def _record_event(self, event_data: Dict[str, Any]) -> None:
        """
        Record an event to the local event store.
        
        Args:
            event_data: Event data to record
        """
        try:
            # Ensure Redis connection
            await self.connect()
            
            if self.redis is None:
                # Fall back to file storage if Redis is not available
                await self._record_event_to_file(event_data)
                return
                
            # Add event to Redis list
            event_type = event_data["event_type"]
            event_json = json.dumps(event_data)
            
            await self.redis.lpush(f"events:{event_type}", event_json)
            
            # If this is a view event, increment view counter
            if event_type == "video_view":
                video_id = event_data["video_id"]
                await self._increment_counter(f"views:video:{video_id}", 1)
                await self._increment_counter("views:total", 1)
                
                # Record daily view
                today = datetime.utcnow().strftime("%Y-%m-%d")
                await self._increment_counter(f"views:daily:{today}", 1)
                
                # Record hourly view
                hour = datetime.utcnow().strftime("%Y-%m-%d-%H")
                await self._increment_counter(f"views:hourly:{hour}", 1)
                
                # If user_id is provided, increment user view counter
                if "user_id" in event_data:
                    user_id = event_data["user_id"]
                    await self._increment_counter(f"views:user:{user_id}", 1)
                    
                # If company_id is provided, increment company view counter
                if "company_id" in event_data:
                    company_id = event_data["company_id"]
                    await self._increment_counter(f"views:company:{company_id}", 1)
        
        except Exception as e:
            logger.error(f"Error recording event: {str(e)}")
            # Fall back to file storage
            await self._record_event_to_file(event_data)

    async def _record_event_to_file(self, event_data: Dict[str, Any]) -> None:
        """
        Record an event to a JSON file.
        
        Args:
            event_data: Event data to record
        """
        try:
            # Create events directory if it doesn't exist
            os.makedirs("events", exist_ok=True)
            
            # Determine file path based on event type
            event_type = event_data["event_type"]
            date = datetime.utcnow().strftime("%Y-%m-%d")
            file_path = f"events/{event_type}_{date}.jsonl"
            
            # Append event to file
            event_json = json.dumps(event_data)
            
            async with aiofiles.open(file_path, "a") as f:
                await f.write(f"{event_json}\n")
                
        except Exception as e:
            logger.error(f"Error recording event to file: {str(e)}")

    async def _increment_counter(self, key: str, value: int) -> None:
        """
        Increment a counter in Redis.
        
        Args:
            key: Counter key
            value: Value to increment by
        """
        try:
            # Ensure Redis connection
            await self.connect()
            
            if self.redis is None:
                return
                
            await self.redis.incrby(key, value)
            
        except Exception as e:
            logger.error(f"Error incrementing counter: {str(e)}")

    async def _get_counter(self, key: str) -> int:
        """
        Get a counter value from Redis.
        
        Args:
            key: Counter key
            
        Returns:
            Counter value
        """
        try:
            # Ensure Redis connection
            await self.connect()
            
            if self.redis is None:
                return 0
                
            value = await self.redis.get(key)
            
            if value is None:
                return 0
                
            return int(value)
            
        except Exception as e:
            logger.error(f"Error getting counter: {str(e)}")
            return 0

    async def _record_timing(self, key: str, value: float) -> None:
        """
        Record a timing value for averaging.
        
        Args:
            key: Timing key
            value: Timing value
        """
        try:
            # Ensure Redis connection
            await self.connect()
            
            if self.redis is None:
                return
                
            # Add value to sorted set
            await self.redis.zadd(f"timings:{key}", value, str(time.time()))
            
            # Limit set size to 1000 entries
            await self.redis.zremrangebyrank(f"timings:{key}", 0, -1001)
            
        except Exception as e:
            logger.error(f"Error recording timing: {str(e)}")

    async def _get_average(self, key: str) -> float:
        """
        Get the average of recorded timing values.
        
        Args:
            key: Timing key
            
        Returns:
            Average value
        """
        try:
            # Ensure Redis connection
            await self.connect()
            
            if self.redis is None:
                return 0.0
                
            # Get all values from sorted set
            values = await self.redis.zrange(f"timings:{key}", 0, -1, withscores=True)
            
            if not values:
                return 0.0
                
            # Calculate average
            total = sum(score for _, score in values)
            count = len(values)
            
            return total / count
            
        except Exception as e:
            logger.error(f"Error getting average: {str(e)}")
            return 0.0

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of key metrics.
        
        Returns:
            Dictionary with metrics summary
        """
        total_views = await self._get_counter("views:total")
        total_uploads = await self._get_counter("uploads:total")
        total_storage = await self._get_counter("storage:total")
        
        # Get daily views
        today = datetime.utcnow().strftime("%Y-%m-%d")
        yesterday = (datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - 
                     datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        
        today_views = await self._get_counter(f"views:daily:{today}")
        yesterday_views = await self._get_counter(f"views:daily:{yesterday}")
        
        # Get processing stats
        processing_stats = await self.get_processing_statistics()
        
        return {
            "total_views": total_views,
            "total_uploads": total_uploads,
            "total_storage_bytes": total_storage,
            "total_storage_gb": round(total_storage / (1024 ** 3), 2),
            "today_views": today_views,
            "yesterday_views": yesterday_views,
            "processing_stats": processing_stats,
            "timestamp": datetime.utcnow().isoformat()
        }