"""
Test Celery VTON tasks
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image


class TestVTONTasks:
    """Test VTON Celery tasks."""

    @patch('workers.tasks.vton_tasks.get_vton_model')
    @patch('workers.tasks.vton_tasks.load_image_from_base64')
    def test_process_vton_async_base64(
        self,
        mock_load_base64,
        mock_get_model
    ):
        """Test async VTON task with base64 images."""
        from workers.tasks.vton_tasks import process_vton_async

        # Mock image loading
        mock_img = Image.new('RGB', (512, 512), color='red')
        mock_load_base64.return_value = mock_img

        # Mock VTON model
        mock_model = Mock()
        mock_model.return_value = Image.new('RGB', (512, 512), color='green')
        mock_get_model.return_value = mock_model

        # Run task (in eager mode, synchronous)
        result = process_vton_async(
            person_image_base64="fake_base64_person",
            garment_image_base64="fake_base64_garment",
            num_inference_steps=10,
            guidance_scale=7.5,
        )

        # Verify result structure
        assert result["success"] is True
        assert "result_url" in result
        assert "processing_time_seconds" in result

    @patch('workers.tasks.vton_tasks.get_vton_model')
    @patch('workers.tasks.vton_tasks.load_image_from_url')
    def test_process_vton_async_urls(
        self,
        mock_load_url,
        mock_get_model
    ):
        """Test async VTON task with image URLs."""
        from workers.tasks.vton_tasks import process_vton_async

        # Mock image loading
        mock_img = Image.new('RGB', (512, 512), color='blue')
        mock_load_url.return_value = mock_img

        # Mock VTON model
        mock_model = Mock()
        mock_model.return_value = Image.new('RGB', (512, 512), color='yellow')
        mock_get_model.return_value = mock_model

        # Run task
        result = process_vton_async(
            person_image_url="https://example.com/person.jpg",
            garment_image_url="https://example.com/garment.jpg",
            num_inference_steps=20,
        )

        assert result["success"] is True

    def test_process_vton_async_missing_images(self):
        """Test task fails when no images provided."""
        from workers.tasks.vton_tasks import process_vton_async

        # Should fail with ValueError
        result = process_vton_async(
            num_inference_steps=10,
        )

        assert result["success"] is False
        assert "error" in result

    @patch('workers.tasks.vton_tasks.httpx.post')
    @patch('workers.tasks.vton_tasks.get_vton_model')
    @patch('workers.tasks.vton_tasks.load_image_from_base64')
    def test_webhook_callback(
        self,
        mock_load_base64,
        mock_get_model,
        mock_httpx_post
    ):
        """Test webhook callback on completion."""
        from workers.tasks.vton_tasks import process_vton_async

        # Mock everything
        mock_img = Image.new('RGB', (512, 512))
        mock_load_base64.return_value = mock_img

        mock_model = Mock()
        mock_model.return_value = mock_img
        mock_get_model.return_value = mock_model

        # Run with callback
        callback_url = "https://example.com/webhook"
        result = process_vton_async(
            person_image_base64="fake",
            garment_image_base64="fake",
            callback_url=callback_url,
        )

        # Verify webhook was called
        mock_httpx_post.assert_called_once()
        call_args = mock_httpx_post.call_args
        assert call_args[0][0] == callback_url

    @patch('workers.tasks.vton_tasks.process_vton_async')
    def test_batch_processing(self, mock_process_single):
        """Test batch VTON processing."""
        from workers.tasks.vton_tasks import process_vton_batch_async

        # Mock single task results
        mock_process_single.return_value = {
            "success": True,
            "result_url": "https://cdn.example.com/result.png"
        }

        # Run batch
        requests = [
            {"person_image_base64": "p1", "garment_image_base64": "g1"},
            {"person_image_base64": "p2", "garment_image_base64": "g2"},
        ]

        result = process_vton_batch_async(requests=requests)

        assert result["success"] is True
        assert result["total_items"] == 2
        assert result["successful_items"] == 2
        assert len(result["results"]) == 2


class TestCleanupTask:
    """Test cleanup utility task."""

    @patch('workers.tasks.vton_tasks.settings')
    def test_cleanup_old_results(self, mock_settings):
        """Test cleanup of old result files."""
        from workers.tasks.vton_tasks import cleanup_old_results
        import tempfile
        import time
        from pathlib import Path

        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "vton" / "async"
            output_dir.mkdir(parents=True)

            # Create old file
            old_file = output_dir / "old_result.png"
            old_file.write_text("old")

            # Modify timestamp to be old
            old_time = time.time() - (25 * 3600)  # 25 hours ago
            old_file.touch()
            import os
            os.utime(old_file, (old_time, old_time))

            # Create new file
            new_file = output_dir / "new_result.png"
            new_file.write_text("new")

            # Mock settings
            mock_settings.output_dir = Path(tmpdir)

            # Run cleanup
            result = cleanup_old_results(max_age_hours=24)

            # Old file should be deleted
            assert not old_file.exists()
            assert new_file.exists()
            assert result["deleted"] == 1
