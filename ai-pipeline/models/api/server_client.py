"""
Server Communication Module for MemeForty Pipeline.

Handles communication between GPU server (this) and CPU server.
Supports image crawling, job queue, and result delivery.
"""

from __future__ import annotations

import base64
import json
import time
from io import BytesIO
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

import requests
from PIL import Image
from loguru import logger


class CPUServerClient:
    """
    Client for communicating with CPU server (VPS).
    
    Handles:
    - Fetching crawled product images
    - Sending generation results
    - Job queue management
    """
    
    def __init__(
        self,
        base_url: str = "http://172.10.5.42:8000",
        timeout: int = 30,
    ):
        """
        Initialize CPU server client.
        
        Args:
            base_url: Base URL of CPU server API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        
        logger.info(f"CPUServerClient initialized: {self.base_url}")
    
    def health_check(self) -> bool:
        """Check if CPU server is reachable."""
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"CPU server health check failed: {e}")
            return False
    
    # ========================================
    # Image Crawling API
    # ========================================
    
    def get_pending_jobs(self) -> List[Dict[str, Any]]:
        """
        Get pending image generation jobs from CPU server.
        
        Returns:
            List of job dictionaries
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/jobs/pending",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get("jobs", [])
        except Exception as e:
            logger.error(f"Failed to get pending jobs: {e}")
            return []
    
    def fetch_crawled_images(
        self,
        product_id: str,
    ) -> Optional[Dict[str, Image.Image]]:
        """
        Fetch crawled product images from CPU server.
        
        Args:
            product_id: Product ID to fetch images for
            
        Returns:
            Dict with 'front', 'back', 'person' images or None
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/products/{product_id}/images",
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            images = {}
            for key in ["front", "back", "person"]:
                if key in data and data[key]:
                    img_data = base64.b64decode(data[key])
                    images[key] = Image.open(BytesIO(img_data))
            
            logger.info(f"Fetched {len(images)} images for product {product_id}")
            return images
            
        except Exception as e:
            logger.error(f"Failed to fetch images: {e}")
            return None
    
    def download_image(self, url: str) -> Optional[Image.Image]:
        """
        Download image from URL.
        
        Args:
            url: Image URL
            
        Returns:
            PIL Image or None
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            return None
    
    # ========================================
    # Result Delivery API
    # ========================================
    
    def upload_result(
        self,
        job_id: str,
        glb_path: Path,
        textures: Optional[Dict[str, Path]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Upload generation result to CPU server.
        
        Args:
            job_id: Job ID
            glb_path: Path to GLB file
            textures: Dict of texture paths
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        try:
            files = {"glb": open(glb_path, "rb")}
            
            if textures:
                for name, path in textures.items():
                    files[f"texture_{name}"] = open(path, "rb")
            
            data = {"job_id": job_id}
            if metadata:
                data["metadata"] = json.dumps(metadata)
            
            response = self.session.post(
                f"{self.base_url}/api/jobs/{job_id}/result",
                files=files,
                data=data,
                timeout=self.timeout * 2
            )
            response.raise_for_status()
            
            logger.info(f"Uploaded result for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload result: {e}")
            return False
        finally:
            for f in files.values():
                f.close()
    
    def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: float = 0.0,
        message: Optional[str] = None,
    ) -> bool:
        """
        Update job status on CPU server.
        
        Args:
            job_id: Job ID
            status: Status string (processing, completed, failed)
            progress: Progress percentage (0-100)
            message: Optional status message
            
        Returns:
            True if successful
        """
        try:
            response = self.session.patch(
                f"{self.base_url}/api/jobs/{job_id}",
                json={
                    "status": status,
                    "progress": progress,
                    "message": message,
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
            return False
    
    # ========================================
    # Crawling Request API
    # ========================================
    
    def request_crawl(
        self,
        product_url: str,
        priority: int = 5,
    ) -> Optional[str]:
        """
        Request CPU server to crawl a product page.
        
        Args:
            product_url: URL of product page
            priority: Crawl priority (1-10)
            
        Returns:
            Job ID if successful, None otherwise
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/crawl",
                json={
                    "url": product_url,
                    "priority": priority,
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get("job_id")
        except Exception as e:
            logger.error(f"Failed to request crawl: {e}")
            return None


class JobQueueProcessor:
    """
    Processes jobs from CPU server queue.
    """
    
    def __init__(
        self,
        client: CPUServerClient,
        poll_interval: int = 10,
    ):
        """
        Initialize job queue processor.
        
        Args:
            client: CPU server client
            poll_interval: Seconds between queue polls
        """
        self.client = client
        self.poll_interval = poll_interval
        self.running = False
    
    def process_single_job(self, job: Dict[str, Any]) -> bool:
        """
        Process a single job.
        
        Args:
            job: Job dictionary
            
        Returns:
            True if successful
        """
        job_id = job.get("id")
        product_id = job.get("product_id")
        
        logger.info(f"Processing job {job_id} for product {product_id}")
        
        # Update status to processing
        self.client.update_job_status(job_id, "processing", 0)
        
        try:
            # Fetch images
            images = self.client.fetch_crawled_images(product_id)
            if not images:
                raise ValueError("No images found")
            
            self.client.update_job_status(job_id, "processing", 20, "Images loaded")
            
            # Run pipeline (placeholder - integrate with actual pipeline)
            result = self._run_pipeline(images, job)
            
            self.client.update_job_status(job_id, "processing", 80, "Uploading result")
            
            # Upload result
            if result and "glb_path" in result:
                self.client.upload_result(
                    job_id,
                    Path(result["glb_path"]),
                    result.get("textures"),
                    result.get("metadata"),
                )
            
            self.client.update_job_status(job_id, "completed", 100)
            return True
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            self.client.update_job_status(job_id, "failed", 0, str(e))
            return False
    
    def _run_pipeline(
        self,
        images: Dict[str, Image.Image],
        job: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Run the generation pipeline."""
        # This would integrate with MemeForty3DPipeline
        # Placeholder for now
        from models.pipeline.memeforty_3d import run_phase2_pipeline
        
        result = run_phase2_pipeline(
            front_image=images.get("front") or images.get("person"),
            back_image=images.get("back") or images.get("front"),
            output_dir=Path("/tmp/memeforty") / job.get("id", "default"),
        )
        
        return {
            "glb_path": result.glb_path,
            "metadata": {
                "quality_score": result.overall_quality,
            }
        }
    
    def run_loop(self):
        """Run continuous job processing loop."""
        self.running = True
        logger.info("Starting job queue processor")
        
        while self.running:
            try:
                jobs = self.client.get_pending_jobs()
                
                for job in jobs:
                    if not self.running:
                        break
                    self.process_single_job(job)
                
                if not jobs:
                    time.sleep(self.poll_interval)
                    
            except Exception as e:
                logger.error(f"Queue processor error: {e}")
                time.sleep(self.poll_interval)
    
    def stop(self):
        """Stop the processing loop."""
        self.running = False


# Convenience functions
def get_cpu_client(base_url: str = "http://172.10.5.42:8000") -> CPUServerClient:
    """Get CPU server client instance."""
    return CPUServerClient(base_url)


def test_cpu_connection() -> Dict[str, Any]:
    """Test connection to CPU server."""
    client = get_cpu_client()
    
    result = {
        "base_url": client.base_url,
        "reachable": client.health_check(),
    }
    
    if result["reachable"]:
        result["pending_jobs"] = len(client.get_pending_jobs())
    
    return result
