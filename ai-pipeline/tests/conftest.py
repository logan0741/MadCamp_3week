"""
Pytest configuration and shared fixtures
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from PIL import Image
import io
import base64


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    from api.main import app
    return TestClient(app)


@pytest.fixture
def sample_person_image():
    """Create a sample person image for testing."""
    # Create a simple test image (512x512 RGB)
    img = Image.new('RGB', (512, 512), color='red')
    return img


@pytest.fixture
def sample_garment_image():
    """Create a sample garment image for testing."""
    # Create a simple test image (512x512 RGB)
    img = Image.new('RGB', (512, 512), color='blue')
    return img


@pytest.fixture
def sample_person_image_base64(sample_person_image):
    """Convert sample person image to base64."""
    buffered = io.BytesIO()
    sample_person_image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


@pytest.fixture
def sample_garment_image_base64(sample_garment_image):
    """Convert sample garment image to base64."""
    buffered = io.BytesIO()
    sample_garment_image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


@pytest.fixture
def mock_vton_model(monkeypatch):
    """Mock VTON model to avoid loading actual model in tests."""
    def mock_get_model():
        class MockVTONModel:
            def __call__(self, person_image, garment_image, **kwargs):
                # Return a simple test image
                return Image.new('RGB', (512, 512), color='green')
        return MockVTONModel()

    from models.vton import idm_vton
    monkeypatch.setattr(idm_vton, "get_vton_model", mock_get_model)
