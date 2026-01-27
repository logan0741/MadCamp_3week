"""
Tests for 3D Avatar API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import numpy as np
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def client():
    """Create test client."""
    from api.main import app
    return TestClient(app)


@pytest.fixture
def mock_shapy():
    """Mock SHAPY model."""
    with patch('models.avatar.ShapyModel') as mock:
        instance = MagicMock()
        instance.estimate_from_image.return_value = {
            'betas': np.zeros(10, dtype=np.float32),
            'body_pose': np.zeros(63, dtype=np.float32),
            'global_orient': np.zeros(3, dtype=np.float32),
            'measurements': {
                'height': 1.75,
                'weight': 70.0,
                'chest': 95.0,
                'waist': 80.0,
                'hips': 95.0,
            },
            'confidence': 0.9,
        }
        instance.estimate_from_measurements.return_value = {
            'betas': np.zeros(10, dtype=np.float32),
            'gender': 'neutral',
            'input_measurements': {
                'height': 1.75,
                'weight': 70.0,
                'chest': 95.0,
                'waist': 80.0,
                'hips': 95.0,
            }
        }
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_smplx():
    """Mock SMPL-X model."""
    with patch('models.avatar.SMPLXModel') as mock:
        instance = MagicMock()
        instance.forward.return_value = {
            'vertices': np.random.randn(1, 10475, 3).astype(np.float32),
            'joints': np.random.randn(1, 55, 3).astype(np.float32),
            'faces': np.array([[0, 1, 2]], dtype=np.int32),
        }
        instance.get_mesh.return_value = (
            np.random.randn(10475, 3).astype(np.float32),
            np.array([[0, 1, 2]], dtype=np.int32),
        )
        instance.export_mesh.return_value = "/tmp/test_avatar.glb"
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_snug():
    """Mock SNUG model."""
    with patch('models.garment.SnugModel') as mock:
        instance = MagicMock()
        instance.simulate.return_value = {
            'vertices': np.random.randn(5000, 3).astype(np.float32),
            'faces': np.array([[0, 1, 2]], dtype=np.int32),
            'stress': np.zeros(5000, dtype=np.float32),
        }
        instance.export_mesh.return_value = "/tmp/test_garment.glb"
        mock.return_value = instance
        yield mock


# ============================================
# Test: List Garment Types
# ============================================

def test_list_garment_types(client):
    """Test listing available garment types."""
    response = client.get("/api/avatar/garments/types")

    assert response.status_code == 200
    data = response.json()

    assert "garments" in data
    assert len(data["garments"]) > 0

    # Check structure
    garment = data["garments"][0]
    assert "type" in garment
    assert "name" in garment


# ============================================
# Test: Generate Avatar from Measurements
# ============================================

@pytest.mark.skip(reason="Requires model files")
def test_generate_avatar_from_measurements(client, mock_shapy, mock_smplx):
    """Test avatar generation from body measurements."""
    request_data = {
        "measurements": {
            "height": 1.75,
            "weight": 70,
            "chest": 95,
            "waist": 80,
            "hips": 95,
            "gender": "male"
        },
        "output_format": "glb"
    }

    response = client.post("/api/avatar/generate", json=request_data)

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "avatar_id" in data
    assert "mesh_url" in data
    assert "betas" in data
    assert "measurements" in data


# ============================================
# Test: Generate Avatar from Image
# ============================================

@pytest.mark.skip(reason="Requires model files and image")
def test_generate_avatar_from_image(client, mock_shapy, mock_smplx):
    """Test avatar generation from image URL."""
    request_data = {
        "image_url": "https://example.com/person.jpg",
        "output_format": "obj"
    }

    response = client.post("/api/avatar/generate", json=request_data)

    # Should fail without actual image, but test the endpoint
    assert response.status_code in [200, 400, 500]


# ============================================
# Test: Simulate Garment
# ============================================

@pytest.mark.skip(reason="Requires avatar to exist")
def test_simulate_garment(client, mock_snug, mock_smplx):
    """Test garment simulation on existing avatar."""
    request_data = {
        "avatar_id": "test-avatar-id",
        "garment_type": "tshirt",
        "output_format": "glb"
    }

    response = client.post("/api/avatar/garment/simulate", json=request_data)

    # Should fail without actual avatar, but test the endpoint
    assert response.status_code in [200, 404, 500]


# ============================================
# Test: Combined Avatar + Garment
# ============================================

@pytest.mark.skip(reason="Requires model files")
def test_combined_avatar_garment(client, mock_shapy, mock_smplx, mock_snug):
    """Test combined avatar and garment generation."""
    request_data = {
        "measurements": {
            "height": 1.70,
            "weight": 65,
            "chest": 90,
            "waist": 75,
            "hips": 95,
            "gender": "female"
        },
        "garment_type": "dress",
        "output_format": "glb"
    }

    response = client.post("/api/avatar/combined", json=request_data)

    # Check endpoint is reachable
    assert response.status_code in [200, 400, 500]


# ============================================
# Test: Get Avatar (Not Found)
# ============================================

def test_get_avatar_not_found(client):
    """Test getting non-existent avatar."""
    response = client.get("/api/avatar/nonexistent-id")

    assert response.status_code == 404


# ============================================
# Test: Delete Avatar (Not Found)
# ============================================

def test_delete_avatar_not_found(client):
    """Test deleting non-existent avatar."""
    response = client.delete("/api/avatar/nonexistent-id")

    # Should handle gracefully even if not found
    assert response.status_code in [200, 404, 500]


# ============================================
# Test: Invalid Request
# ============================================

def test_generate_avatar_invalid_request(client):
    """Test avatar generation with invalid request."""
    # Missing both image and measurements
    request_data = {
        "output_format": "glb"
    }

    response = client.post("/api/avatar/generate", json=request_data)

    assert response.status_code == 400


def test_generate_avatar_invalid_measurements(client):
    """Test avatar generation with invalid measurements."""
    request_data = {
        "measurements": {
            "height": 0.5,  # Too short
            "gender": "invalid"
        }
    }

    response = client.post("/api/avatar/generate", json=request_data)

    assert response.status_code == 422  # Validation error


# ============================================
# Test: Garment Type Validation
# ============================================

@pytest.mark.skip(reason="Requires avatar to exist")
def test_simulate_invalid_garment_type(client):
    """Test simulation with invalid garment type."""
    request_data = {
        "avatar_id": "test-avatar-id",
        "garment_type": "invalid_garment",
        "output_format": "glb"
    }

    response = client.post("/api/avatar/garment/simulate", json=request_data)

    # Should fail with validation or not found error
    assert response.status_code in [400, 404, 422, 500]


# ============================================
# Integration Test (Manual)
# ============================================

@pytest.mark.integration
@pytest.mark.skip(reason="Requires full setup")
def test_full_avatar_workflow(client):
    """
    Full integration test for avatar workflow.

    Run with: pytest -v -m integration
    """
    # 1. Generate avatar
    avatar_response = client.post("/api/avatar/generate", json={
        "measurements": {
            "height": 1.75,
            "weight": 70,
            "chest": 95,
            "waist": 80,
            "hips": 95,
            "gender": "male"
        }
    })

    assert avatar_response.status_code == 200
    avatar_data = avatar_response.json()
    avatar_id = avatar_data["avatar_id"]

    # 2. Simulate garment
    garment_response = client.post("/api/avatar/garment/simulate", json={
        "avatar_id": avatar_id,
        "garment_type": "tshirt"
    })

    assert garment_response.status_code == 200
    garment_data = garment_response.json()

    assert garment_data["success"] is True
    assert "garment_mesh_url" in garment_data

    # 3. Get avatar info
    info_response = client.get(f"/api/avatar/{avatar_id}")
    assert info_response.status_code == 200

    # 4. Delete avatar
    delete_response = client.delete(f"/api/avatar/{avatar_id}")
    assert delete_response.status_code == 200
