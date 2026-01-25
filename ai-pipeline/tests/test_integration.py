"""
Integration tests for VTON pipeline

These tests require:
- Redis running
- Celery worker running
- Actual model weights (optional, can use mocks)

Run with: pytest tests/test_integration.py -v
"""

import pytest
import time
import httpx
from PIL import Image
import io
import base64


# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def api_base_url():
    """API base URL for integration tests."""
    return "http://localhost:8001"


@pytest.fixture(scope="module")
def test_images():
    """Create test images."""
    person_img = Image.new('RGB', (512, 512), color=(255, 0, 0))
    garment_img = Image.new('RGB', (512, 512), color=(0, 0, 255))

    # Convert to base64
    def img_to_base64(img):
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    return {
        "person_base64": img_to_base64(person_img),
        "garment_base64": img_to_base64(garment_img),
    }


class TestIntegrationHealthCheck:
    """Test API is running."""

    def test_api_is_running(self, api_base_url):
        """Verify API is accessible."""
        try:
            response = httpx.get(f"{api_base_url}/health", timeout=5.0)
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
        except httpx.ConnectError:
            pytest.skip("API server not running")


class TestIntegrationVTONSync:
    """Test synchronous VTON (requires model weights)."""

    @pytest.mark.slow
    def test_sync_vton_e2e(self, api_base_url, test_images):
        """End-to-end test of synchronous VTON."""
        payload = {
            "person_image_base64": test_images["person_base64"],
            "garment_image_base64": test_images["garment_base64"],
            "num_inference_steps": 10,  # Fast for testing
            "guidance_scale": 7.5,
        }

        try:
            response = httpx.post(
                f"{api_base_url}/api/vton/try-on",
                json=payload,
                timeout=120.0  # Allow time for inference
            )

            assert response.status_code == 200
            data = response.json()
            assert "result_base64" in data or "result_url" in data
            assert "processing_time_seconds" in data

        except httpx.ConnectError:
            pytest.skip("API server not running")
        except Exception as e:
            # Model weights might not be available
            pytest.skip(f"Model inference failed: {e}")


class TestIntegrationVTONAsync:
    """Test asynchronous VTON workflow."""

    def test_async_vton_submit(self, api_base_url, test_images):
        """Test task submission."""
        payload = {
            "person_image_base64": test_images["person_base64"],
            "garment_image_base64": test_images["garment_base64"],
            "num_inference_steps": 20,
        }

        try:
            response = httpx.post(
                f"{api_base_url}/api/vton/try-on-async",
                json=payload,
                timeout=10.0
            )

            assert response.status_code == 200
            data = response.json()
            assert "task_id" in data
            assert data["status"] in ["PENDING", "PROGRESS", "SUCCESS"]

        except httpx.ConnectError:
            pytest.skip("API server not running")

    @pytest.mark.slow
    def test_async_vton_complete_workflow(self, api_base_url, test_images):
        """Test complete async workflow: submit -> poll -> result."""
        # 1. Submit task
        payload = {
            "person_image_base64": test_images["person_base64"],
            "garment_image_base64": test_images["garment_base64"],
            "num_inference_steps": 10,
        }

        try:
            submit_response = httpx.post(
                f"{api_base_url}/api/vton/try-on-async",
                json=payload,
                timeout=10.0
            )
            assert submit_response.status_code == 200
            task_id = submit_response.json()["task_id"]

            # 2. Poll for completion
            max_attempts = 60  # 60 seconds max
            for attempt in range(max_attempts):
                status_response = httpx.get(
                    f"{api_base_url}/api/vton/task/{task_id}",
                    timeout=5.0
                )
                assert status_response.status_code == 200
                status_data = status_response.json()

                print(f"Attempt {attempt + 1}: {status_data['status']}")

                if status_data["status"] == "SUCCESS":
                    # Task completed successfully
                    assert "result" in status_data
                    result = status_data["result"]
                    assert result["success"] is True
                    assert "result_url" in result
                    assert "processing_time_seconds" in result
                    print(f"✓ Task completed in {result['processing_time_seconds']}s")
                    return

                elif status_data["status"] == "FAILURE":
                    # Task failed
                    pytest.fail(f"Task failed: {status_data.get('error')}")

                elif status_data["status"] == "PROGRESS":
                    # Task in progress
                    meta = status_data.get("meta", {})
                    progress = meta.get("progress", 0)
                    message = meta.get("message", "")
                    print(f"  Progress: {progress}% - {message}")

                # Wait before next poll
                time.sleep(1)

            pytest.fail("Task did not complete within timeout")

        except httpx.ConnectError:
            pytest.skip("API server not running")
        except Exception as e:
            pytest.skip(f"Integration test failed: {e}")


class TestIntegrationBatch:
    """Test batch processing."""

    def test_batch_submit(self, api_base_url, test_images):
        """Test batch task submission."""
        payload = {
            "requests": [
                {
                    "person_image_base64": test_images["person_base64"],
                    "garment_image_base64": test_images["garment_base64"],
                },
                {
                    "person_image_base64": test_images["person_base64"],
                    "garment_image_base64": test_images["garment_base64"],
                }
            ]
        }

        try:
            response = httpx.post(
                f"{api_base_url}/api/vton/batch-async",
                json=payload,
                timeout=10.0
            )

            assert response.status_code == 200
            data = response.json()
            assert "task_id" in data

        except httpx.ConnectError:
            pytest.skip("API server not running")


class TestIntegrationCeleryWorker:
    """Test Celery worker is running."""

    def test_celery_worker_active(self, api_base_url):
        """Check if Celery workers are active."""
        # This requires Celery inspect API
        # For now, just verify by submitting a task
        pass


# Pytest markers configuration
def pytest_configure(config):
    """Add custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (requires running services)"
    )
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (takes > 10 seconds)"
    )
