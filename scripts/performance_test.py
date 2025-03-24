"""
Performance test script for the EINO Streaming Service.

This script evaluates the performance of the video streaming service under various load conditions,
measuring metrics such as upload throughput, transcoding speed, and streaming performance.

Usage:
    python scripts/performance_test.py --mode=[all|upload|transcode|stream] --concurrency=10 --duration=300
"""

import asyncio
import argparse
import time
import os
import random
import statistics
import uuid
import logging
import aiohttp
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("performance_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("performance_test")

# Default settings
DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1"
DEFAULT_CONCURRENCY = 5
DEFAULT_DURATION = 60  # seconds
DEFAULT_UPLOAD_CHUNK_SIZE = 5 * 1024 * 1024  # 5MB chunks
DEFAULT_TEST_FILES_DIR = "test_files"
TEST_VIDEO_SIZES = ["small", "medium", "large"]  # Corresponds to test file naming

# Performance metrics storage
metrics = {
    "upload": {
        "durations": [],
        "speeds": [],
        "success_count": 0,
        "failure_count": 0,
        "videos": []
    },
    "transcode": {
        "durations": [],
        "speeds": [],
        "success_count": 0,
        "failure_count": 0
    },
    "stream": {
        "durations": [],
        "startup_times": [],
        "success_count": 0,
        "failure_count": 0
    }
}


class PerformanceTester:
    """Main performance testing class for the streaming service."""

    def __init__(
        self,
        api_base_url: str = DEFAULT_API_BASE_URL,
        concurrency: int = DEFAULT_CONCURRENCY,
        duration: int = DEFAULT_DURATION,
        test_files_dir: str = DEFAULT_TEST_FILES_DIR,
        chunk_size: int = DEFAULT_UPLOAD_CHUNK_SIZE
    ):
        """Initialize the performance tester.
        
        Args:
            api_base_url: Base URL of the API
            concurrency: Number of concurrent operations
            duration: Test duration in seconds
            test_files_dir: Directory containing test video files
            chunk_size: Size of upload chunks in bytes
        """
        self.api_base_url = api_base_url
        self.concurrency = concurrency
        self.duration = duration
        self.test_files_dir = Path(test_files_dir)
        self.chunk_size = chunk_size
        
        # Auth token storage
        self.auth_token = None
        
        # Test account credentials
        self.test_email = os.environ.get("TEST_EMAIL", "test@example.com")
        self.test_password = os.environ.get("TEST_PASSWORD", "testpassword")
        
        # Company ID for tests
        self.company_id = os.environ.get("TEST_COMPANY_ID", "test-company-id")
        
        # Create test files directory if it doesn't exist
        os.makedirs(self.test_files_dir, exist_ok=True)
        
        logger.info(f"Initialized performance tester with concurrency={concurrency}, duration={duration}s")

    async def authenticate(self) -> None:
        """Authenticate with the API and get an auth token."""
        async with aiohttp.ClientSession() as session:
            try:
                login_url = f"{self.api_base_url}/auth/token"
                data = {
                    "username": self.test_email,
                    "password": self.test_password
                }
                
                async with session.post(login_url, data=data) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        self.auth_token = response_data.get("access_token")
                        logger.info("Authentication successful")
                    else:
                        error_text = await response.text()
                        logger.error(f"Authentication failed: {error_text}")
                        raise Exception(f"Authentication failed: {error_text}")
            except Exception as e:
                logger.error(f"Error during authentication: {str(e)}")
                raise

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers including authentication."""
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Company-Id": self.company_id,
            "Accept": "application/json"
        }
        return headers

    async def _get_test_file(self, size: str = "medium") -> Tuple[str, int]:
        """Get a test video file for upload testing.
        
        Args:
            size: Size category of the test file (small, medium, large)
            
        Returns:
            Tuple of (file_path, file_size)
        """
        # Look for existing test files
        test_files = list(self.test_files_dir.glob(f"test_video_{size}*.mp4"))
        
        if test_files:
            # Use an existing test file
            file_path = str(test_files[0])
            file_size = os.path.getsize(file_path)
            return file_path, file_size
        else:
            # Download a test file if none exists
            logger.info(f"No {size} test file found, downloading...")
            
            # Sizes in MB approximately
            size_mb = {
                "small": 5,
                "medium": 25,
                "large": 100
            }.get(size, 25)
            
            # This would typically download from a reliable source
            # For this example, we'll create a dummy file
            file_path = str(self.test_files_dir / f"test_video_{size}_{uuid.uuid4()}.mp4")
            
            # Create a dummy file of approximately the right size
            file_size = size_mb * 1024 * 1024  # Convert MB to bytes
            with open(file_path, "wb") as f:
                # Write random data in chunks to avoid memory issues
                chunk_size = 1024 * 1024  # 1MB chunks
                for _ in range(0, size_mb):
                    f.write(os.urandom(chunk_size))
            
            logger.info(f"Created test file: {file_path} ({size_mb}MB)")
            return file_path, file_size

    async def run_upload_test(self) -> None:
        """Run performance test for video uploads."""
        logger.info(f"Starting upload performance test with concurrency={self.concurrency}")
        
        # Reset metrics
        metrics["upload"] = {
            "durations": [],
            "speeds": [],
            "success_count": 0,
            "failure_count": 0,
            "videos": []
        }
        
        # Make sure we're authenticated
        if not self.auth_token:
            await self.authenticate()
        
        # Create tasks for concurrent uploads
        tasks = []
        for i in range(self.concurrency):
            # Randomly select test file size
            size = random.choice(TEST_VIDEO_SIZES)
            tasks.append(self._upload_video_task(i, size))
        
        # Run tasks concurrently
        await asyncio.gather(*tasks)
        
        # Log results
        self._log_upload_results()

    async def _upload_video_task(self, task_id: int, file_size: str) -> None:
        """Task for uploading a single video.
        
        Args:
            task_id: Task identifier
            file_size: Size category of the test file
        """
        try:
            # Get test file
            file_path, file_size_bytes = await self._get_test_file(file_size)
            file_name = os.path.basename(file_path)
            
            logger.info(f"Task {task_id}: Starting upload of {file_name} ({file_size_bytes/1024/1024:.2f}MB)")
            
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                # Step 1: Initialize upload
                init_data = {
                    "filename": file_name,
                    "file_size": file_size_bytes,
                    "content_type": "video/mp4",
                    "title": f"Performance Test Video {task_id}",
                    "description": f"Upload performance test video {task_id}"
                }
                
                async with session.post(
                    f"{self.api_base_url}/upload/initialize",
                    json=init_data,
                    headers=self._get_headers()
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Task {task_id}: Upload initialization failed: {error_text}")
                        metrics["upload"]["failure_count"] += 1
                        return
                    
                    init_response = await response.json()
                    video_id = init_response.get("video_id")
                
                # Step 2: Upload chunks
                with open(file_path, "rb") as f:
                    chunk_index = 0
                    while True:
                        chunk_data = f.read(self.chunk_size)
                        if not chunk_data:
                            break
                        
                        form_data = aiohttp.FormData()
                        form_data.add_field("file", chunk_data, filename=f"chunk_{chunk_index}")
                        form_data.add_field("video_id", video_id)
                        form_data.add_field("chunk_index", str(chunk_index))
                        form_data.add_field("total_chunks", str((file_size_bytes + self.chunk_size - 1) // self.chunk_size))
                        
                        async with session.post(
                            f"{self.api_base_url}/upload/chunk",
                            data=form_data,
                            headers=self._get_headers()
                        ) as response:
                            if response.status != 200:
                                error_text = await response.text()
                                logger.error(f"Task {task_id}: Chunk {chunk_index} upload failed: {error_text}")
                                metrics["upload"]["failure_count"] += 1
                                return
                        
                        chunk_index += 1
                
                # Step 3: Wait for processing to start
                async with session.get(
                    f"{self.api_base_url}/upload/status/{video_id}",
                    headers=self._get_headers()
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Task {task_id}: Failed to get upload status: {error_text}")
                        metrics["upload"]["failure_count"] += 1
                        return
                    
                    status_response = await response.json()
                
                # Calculate metrics
                end_time = time.time()
                duration = end_time - start_time
                speed_mbps = (file_size_bytes / 1024 / 1024) / duration
                
                metrics["upload"]["durations"].append(duration)
                metrics["upload"]["speeds"].append(speed_mbps)
                metrics["upload"]["success_count"] += 1
                metrics["upload"]["videos"].append(video_id)
                
                logger.info(
                    f"Task {task_id}: Upload completed in {duration:.2f}s " +
                    f"({speed_mbps:.2f}MB/s) - Video ID: {video_id}"
                )
                
        except Exception as e:
            logger.error(f"Task {task_id}: Error during upload: {str(e)}")
            metrics["upload"]["failure_count"] += 1

    async def run_transcode_test(self) -> None:
        """Run performance test for video transcoding."""
        logger.info(f"Starting transcode performance test")
        
        # Reset metrics
        metrics["transcode"] = {
            "durations": [],
            "speeds": [],
            "success_count": 0,
            "failure_count": 0
        }
        
        # Make sure we're authenticated
        if not self.auth_token:
            await self.authenticate()
        
        # Get videos for testing
        if not metrics["upload"]["videos"]:
            # Run upload test first if no videos available
            await self.run_upload_test()
        
        video_ids = metrics["upload"]["videos"]
        if not video_ids:
            logger.error("No videos available for transcode testing")
            return
        
        # Create tasks for monitoring transcoding performance
        tasks = []
        for i, video_id in enumerate(video_ids):
            tasks.append(self._monitor_transcoding_task(i, video_id))
        
        # Run tasks concurrently
        await asyncio.gather(*tasks)
        
        # Log results
        self._log_transcode_results()

    async def _monitor_transcoding_task(self, task_id: int, video_id: str) -> None:
        """Task for monitoring transcoding performance.
        
        Args:
            task_id: Task identifier
            video_id: ID of the video to monitor
        """
        try:
            logger.info(f"Task {task_id}: Monitoring transcoding of video {video_id}")
            
            start_time = time.time()
            status = "processing"
            
            async with aiohttp.ClientSession() as session:
                # Poll for status until complete or timeout
                timeout = time.time() + 30 * 60  # 30 minute timeout
                
                while status in ["pending", "processing"] and time.time() < timeout:
                    async with session.get(
                        f"{self.api_base_url}/streams/{video_id}",
                        headers=self._get_headers()
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Task {task_id}: Failed to get video status: {error_text}")
                            # Maybe it's still processing, continue polling
                            await asyncio.sleep(5)
                            continue
                        
                        video_data = await response.json()
                        status = video_data.get("status", "unknown")
                        
                        if status == "ready":
                            # Transcoding complete
                            end_time = time.time()
                            duration = end_time - start_time
                            
                            # Calculate speed in terms of video duration vs processing time
                            video_duration = video_data.get("duration", 0)
                            speed_ratio = video_duration / duration if duration > 0 else 0
                            
                            metrics["transcode"]["durations"].append(duration)
                            metrics["transcode"]["speeds"].append(speed_ratio)
                            metrics["transcode"]["success_count"] += 1
                            
                            logger.info(
                                f"Task {task_id}: Transcoding completed in {duration:.2f}s " +
                                f"(Speed ratio: {speed_ratio:.2f}x real-time)"
                            )
                            return
                        elif status == "failed":
                            logger.error(f"Task {task_id}: Transcoding failed for video {video_id}")
                            metrics["transcode"]["failure_count"] += 1
                            return
                    
                    # Wait before polling again
                    await asyncio.sleep(5)
                
                # If we got here, we timed out
                if time.time() >= timeout:
                    logger.error(f"Task {task_id}: Transcoding timed out for video {video_id}")
                    metrics["transcode"]["failure_count"] += 1
                
        except Exception as e:
            logger.error(f"Task {task_id}: Error monitoring transcoding: {str(e)}")
            metrics["transcode"]["failure_count"] += 1

    async def run_stream_test(self) -> None:
        """Run performance test for video streaming."""
        logger.info(f"Starting streaming performance test with concurrency={self.concurrency}")
        
        # Reset metrics
        metrics["stream"] = {
            "durations": [],
            "startup_times": [],
            "success_count": 0,
            "failure_count": 0
        }
        
        # Make sure we're authenticated
        if not self.auth_token:
            await self.authenticate()
        
        # Get list of videos to stream
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_base_url}/streams/my-videos",
                headers=self._get_headers()
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to get video list: {error_text}")
                    return
                
                videos_data = await response.json()
                
                # Filter for ready videos
                available_videos = [v for v in videos_data if v.get("status") == "ready"]
                
                if not available_videos:
                    logger.error("No ready videos available for streaming test")
                    return
        
        # Create tasks for concurrent streaming tests
        start_time = time.time()
        end_time = start_time + self.duration
        
        # Create a queue of streaming test tasks
        task_queue = asyncio.Queue()
        
        # Producer: add streaming tasks to the queue
        async def producer():
            task_id = 0
            while time.time() < end_time:
                # Randomly select a video
                video = random.choice(available_videos)
                await task_queue.put((task_id, video["id"]))
                task_id += 1
                # Small delay between adding tasks
                await asyncio.sleep(random.uniform(0.1, 1.0))
        
        # Consumer: execute streaming tests from the queue
        async def consumer(worker_id):
            while time.time() < end_time:
                try:
                    # Get a task with timeout
                    try:
                        task_id, video_id = await asyncio.wait_for(task_queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue
                    
                    # Execute the streaming test
                    await self._stream_video_task(worker_id, task_id, video_id)
                    
                    # Mark task as done
                    task_queue.task_done()
                except Exception as e:
                    logger.error(f"Worker {worker_id}: Error in consumer: {str(e)}")
        
        # Start producer task
        producer_task = asyncio.create_task(producer())
        
        # Start consumer tasks
        consumer_tasks = [
            asyncio.create_task(consumer(i))
            for i in range(self.concurrency)
        ]
        
        # Wait for the test duration to complete
        await asyncio.sleep(self.duration)
        
        # Wait for all tasks to complete
        await producer_task
        await asyncio.gather(*consumer_tasks)
        
        # Log results
        self._log_stream_results()

    async def _stream_video_task(self, worker_id: int, task_id: int, video_id: str) -> None:
        """Task for streaming a single video.
        
        Args:
            worker_id: Worker identifier
            task_id: Task identifier
            video_id: ID of the video to stream
        """
        try:
            logger.info(f"Worker {worker_id}, Task {task_id}: Starting streaming test for video {video_id}")
            
            async with aiohttp.ClientSession() as session:
                # Step 1: Get streaming manifest
                start_time = time.time()
                
                async with session.get(
                    f"{self.api_base_url}/streams/{video_id}/manifest?format=hls",
                    headers=self._get_headers()
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Worker {worker_id}, Task {task_id}: Failed to get streaming manifest: {error_text}")
                        metrics["stream"]["failure_count"] += 1
                        return
                    
                    manifest_data = await response.json()
                    manifest_url = manifest_data.get("manifest_url")
                
                # Step 2: Get the manifest file
                async with session.get(
                    manifest_url,
                    headers=self._get_headers()
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Worker {worker_id}, Task {task_id}: Failed to get HLS master playlist: {error_text}")
                        metrics["stream"]["failure_count"] += 1
                        return
                    
                    master_playlist = await response.text()
                
                # Calculate startup time (time to get manifest + master playlist)
                startup_time = time.time() - start_time
                metrics["stream"]["startup_times"].append(startup_time)
                
                # Step 3: Parse master playlist to get variant playlists
                variant_urls = []
                for line in master_playlist.splitlines():
                    if not line.startswith('#') and line.strip():
                        # This is a variant playlist URL
                        variant_url = line
                        # Handle relative URLs
                        if not variant_url.startswith('http'):
                            base_url = os.path.dirname(manifest_url)
                            variant_url = f"{base_url}/{variant_url}"
                        variant_urls.append(variant_url)
                
                if not variant_urls:
                    logger.error(f"Worker {worker_id}, Task {task_id}: No variant playlists found in master playlist")
                    metrics["stream"]["failure_count"] += 1
                    return
                
                # Step 4: Get a variant playlist
                variant_url = random.choice(variant_urls)
                
                async with session.get(
                    variant_url,
                    headers=self._get_headers()
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Worker {worker_id}, Task {task_id}: Failed to get variant playlist: {error_text}")
                        metrics["stream"]["failure_count"] += 1
                        return
                    
                    variant_playlist = await response.text()
                
                # Step 5: Parse variant playlist to get segment URLs
                segment_urls = []
                for line in variant_playlist.splitlines():
                    if not line.startswith('#') and line.strip():
                        # This is a segment URL
                        segment_url = line
                        # Handle relative URLs
                        if not segment_url.startswith('http'):
                            base_url = os.path.dirname(variant_url)
                            segment_url = f"{base_url}/{segment_url}"
                        segment_urls.append(segment_url)
                
                if not segment_urls:
                    logger.error(f"Worker {worker_id}, Task {task_id}: No segments found in variant playlist")
                    metrics["stream"]["failure_count"] += 1
                    return
                
                # Step 6: Download a sample of segments to simulate streaming
                # For performance testing, we'll only download a few segments
                segments_to_download = min(3, len(segment_urls))
                sample_segments = random.sample(segment_urls, segments_to_download)
                
                for i, segment_url in enumerate(sample_segments):
                    async with session.get(
                        segment_url,
                        headers=self._get_headers()
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Worker {worker_id}, Task {task_id}: Failed to get segment {i}: {error_text}")
                            metrics["stream"]["failure_count"] += 1
                            return
                        
                        # Read segment data
                        await response.read()
                
                # Calculate total streaming duration
                end_time = time.time()
                duration = end_time - start_time
                
                metrics["stream"]["durations"].append(duration)
                metrics["stream"]["success_count"] += 1
                
                logger.info(
                    f"Worker {worker_id}, Task {task_id}: Streaming test completed in {duration:.2f}s " +
                    f"(Startup time: {startup_time:.2f}s)"
                )
                
        except Exception as e:
            logger.error(f"Worker {worker_id}, Task {task_id}: Error during streaming test: {str(e)}")
            metrics["stream"]["failure_count"] += 1

    def _log_upload_results(self) -> None:
        """Log the results of the upload performance test."""
        if not metrics["upload"]["durations"]:
            logger.info("No upload data to report")
            return
        
        avg_duration = statistics.mean(metrics["upload"]["durations"])
        avg_speed = statistics.mean(metrics["upload"]["speeds"])
        success_rate = metrics["upload"]["success_count"] / (
            metrics["upload"]["success_count"] + metrics["upload"]["failure_count"]
        ) * 100 if metrics["upload"]["success_count"] + metrics["upload"]["failure_count"] > 0 else 0
        
        logger.info("=== Upload Performance Results ===")
        logger.info(f"Successful Uploads: {metrics['upload']['success_count']}")
        logger.info(f"Failed Uploads: {metrics['upload']['failure_count']}")
        logger.info(f"Success Rate: {success_rate:.2f}%")
        logger.info(f"Average Upload Duration: {avg_duration:.2f}s")
        logger.info(f"Average Upload Speed: {avg_speed:.2f}MB/s")
        logger.info("=================================")

    def _log_transcode_results(self) -> None:
        """Log the results of the transcode performance test."""
        if not metrics["transcode"]["durations"]:
            logger.info("No transcode data to report")
            return
        
        avg_duration = statistics.mean(metrics["transcode"]["durations"])
        avg_speed = statistics.mean(metrics["transcode"]["speeds"])
        success_rate = metrics["transcode"]["success_count"] / (
            metrics["transcode"]["success_count"] + metrics["transcode"]["failure_count"]
        ) * 100 if metrics["transcode"]["success_count"] + metrics["transcode"]["failure_count"] > 0 else 0
        
        logger.info("=== Transcode Performance Results ===")
        logger.info(f"Successful Transcodes: {metrics['transcode']['success_count']}")
        logger.info(f"Failed Transcodes: {metrics['transcode']['failure_count']}")
        logger.info(f"Success Rate: {success_rate:.2f}%")
        logger.info(f"Average Transcode Duration: {avg_duration:.2f}s")
        logger.info(f"Average Transcode Speed Ratio: {avg_speed:.2f}x real-time")
        logger.info("=====================================")

    def _log_stream_results(self) -> None:
        """Log the results of the streaming performance test."""
        if not metrics["stream"]["durations"]:
            logger.info("No streaming data to report")
            return
        
        avg_duration = statistics.mean(metrics["stream"]["durations"])
        avg_startup = statistics.mean(metrics["stream"]["startup_times"])
        success_rate = metrics["stream"]["success_count"] / (
            metrics["stream"]["success_count"] + metrics["stream"]["failure_count"]
        ) * 100 if metrics["stream"]["success_count"] + metrics["stream"]["failure_count"] > 0 else 0
        
        logger.info("=== Streaming Performance Results ===")
        logger.info(f"Successful Streams: {metrics['stream']['success_count']}")
        logger.info(f"Failed Streams: {metrics['stream']['failure_count']}")
        logger.info(f"Success Rate: {success_rate:.2f}%")
        logger.info(f"Average Stream Duration: {avg_duration:.2f}s")
        logger.info(f"Average Startup Time: {avg_startup:.2f}s")
        logger.info("=====================================")

    async def run_all_tests(self) -> None:
        """Run all performance tests in sequence."""
        logger.info("Starting comprehensive performance test suite")
        
        # Make sure we're authenticated
        if not self.auth_token:
            await self.authenticate()
        
        # Run upload tests
        await self.run_upload_test()
        
        # Run transcode tests
        await self.run_transcode_test()
        
        # Run streaming tests
        await self.run_stream_test()
        
        # Log overall results
        self._log_overall_results()

    def _log_overall_results(self) -> None:
        """Log overall performance test results and generate a summary report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info("=== Overall Performance Test Results ===")
        logger.info(f"Test Timestamp: {timestamp}")
        logger.info(f"Concurrency Level: {self.concurrency}")
        logger.info(f"Test Duration: {self.duration}s")
        
        # Upload metrics
        upload_success_rate = metrics["upload"]["success_count"] / (
            metrics["upload"]["success_count"] + metrics["upload"]["failure_count"]
        ) * 100 if metrics["upload"]["success_count"] + metrics["upload"]["failure_count"] > 0 else 0
        
        logger.info("Upload Performance:")
        logger.info(f"  - Success Rate: {upload_success_rate:.2f}%")
        if metrics["upload"]["speeds"]:
            logger.info(f"  - Average Upload Speed: {statistics.mean(metrics['upload']['speeds']):.2f}MB/s")
        
        # Transcode metrics
        transcode_success_rate = metrics["transcode"]["success_count"] / (
            metrics["transcode"]["success_count"] + metrics["transcode"]["failure_count"]
        ) * 100 if metrics["transcode"]["success_count"] + metrics["transcode"]["failure_count"] > 0 else 0
        
        logger.info("Transcode Performance:")
        logger.info(f"  - Success Rate: {transcode_success_rate:.2f}%")
        if metrics["transcode"]["speeds"]:
            logger.info(f"  - Average Processing Speed: {statistics.mean(metrics['transcode']['speeds']):.2f}x real-time")
        
        # Streaming metrics
        stream_success_rate = metrics["stream"]["success_count"] / (
            metrics["stream"]["success_count"] + metrics["stream"]["failure_count"]
        ) * 100 if metrics["stream"]["success_count"] + metrics["stream"]["failure_count"] > 0 else 0
        
        logger.info("Streaming Performance:")
        logger.info(f"  - Success Rate: {stream_success_rate:.2f}%")
        if metrics["stream"]["startup_times"]:
            logger.info(f"  - Average Startup Time: {statistics.mean(metrics['stream']['startup_times']):.2f}s")
        
        logger.info("=========================================")
        
        # Write JSON report
        report = {
            "timestamp": timestamp,
            "configuration": {
                "concurrency": self.concurrency,
                "duration": self.duration,
                "api_base_url": self.api_base_url,
                "chunk_size": self.chunk_size
            },
            "metrics": metrics
        }
        
        report_path = f"performance_report_{int(time.time())}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Detailed performance report saved to {report_path}")


async def main():
    """Main entry point for the performance test script."""
    parser = argparse.ArgumentParser(description="Performance testing tool for EINO Streaming Service")
    
    # Main arguments
    parser.add_argument("--mode", choices=["all", "upload", "transcode", "stream"], default="all",
                       help="Test mode to run (default: all)")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY,
                       help=f"Number of concurrent operations (default: {DEFAULT_CONCURRENCY})")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION,
                       help=f"Test duration in seconds (default: {DEFAULT_DURATION})")
    
    # Additional configuration
    parser.add_argument("--api-url", default=DEFAULT_API_BASE_URL,
                       help=f"Base URL of the API (default: {DEFAULT_API_BASE_URL})")
    parser.add_argument("--test-files-dir", default=DEFAULT_TEST_FILES_DIR,
                       help=f"Directory for test files (default: {DEFAULT_TEST_FILES_DIR})")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_UPLOAD_CHUNK_SIZE,
                       help=f"Upload chunk size in bytes (default: {DEFAULT_UPLOAD_CHUNK_SIZE})")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create tester instance
    tester = PerformanceTester(
        api_base_url=args.api_url,
        concurrency=args.concurrency,
        duration=args.duration,
        test_files_dir=args.test_files_dir,
        chunk_size=args.chunk_size
    )
    
    # Run tests based on mode
    try:
        await tester.authenticate()
        
        if args.mode == "upload" or args.mode == "all":
            await tester.run_upload_test()
            
        if args.mode == "transcode" or args.mode == "all":
            await tester.run_transcode_test()
            
        if args.mode == "stream" or args.mode == "all":
            await tester.run_stream_test()
            
        if args.mode == "all":
            tester._log_overall_results()
            
    except Exception as e:
        logger.error(f"Error running performance tests: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    # Set up asyncio policy for Windows if needed
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Run the main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)