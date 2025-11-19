"""Tests for staging platform image upload."""

import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from service.api import app
from service.db import create_tenant, create_user, issue_token

client = TestClient(app)


@pytest.fixture
def test_tenant():
    """Create a test tenant."""
    tenant = create_tenant("Test Upload Tenant", slug="test-upload")
    return tenant


@pytest.fixture
def test_client_user(test_tenant):
    """Create a test client user."""
    user = create_user(
        test_tenant["tenant_id"],
        "upload@test.com",
        "TestPassword123!",
        role="client",
    )
    token = issue_token(user["user_id"], test_tenant["tenant_id"], label="test")
    return {**user, "token": token["token"], "tenant": test_tenant}


def create_test_image() -> bytes:
    """Create a test JPEG image."""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_upload_image_requires_auth():
    """Test that image upload requires authentication."""
    image_data = create_test_image()
    files = {"file": ("test.jpg", image_data, "image/jpeg")}
    response = client.post("/api/staging/jobs/test-job-id/upload", files=files)
    assert response.status_code == 401


def test_upload_image_invalid_job(test_client_user):
    """Test uploading image to non-existent job."""
    headers = {"Authorization": f"Bearer {test_client_user['token']}"}
    image_data = create_test_image()
    files = {"file": ("test.jpg", image_data, "image/jpeg")}
    response = client.post(
        "/api/staging/jobs/invalid-job-id/upload",
        files=files,
        headers=headers,
        data={"image_type": "original"},
    )
    assert response.status_code == 404


def test_upload_image_valid(test_client_user):
    """Test uploading a valid image."""
    headers = {"Authorization": f"Bearer {test_client_user['token']}"}
    
    # Create property and job first
    from service.staging_db import create_property, create_job
    property_data = create_property(
        test_client_user["tenant"]["tenant_id"],
        test_client_user["user_id"],
        "123 Upload St",
    )
    job_data = create_job(
        test_client_user["tenant"]["tenant_id"],
        property_data["property_id"],
        test_client_user["user_id"],
    )
    
    # Upload image
    image_data = create_test_image()
    files = {"file": ("test.jpg", image_data, "image/jpeg")}
    response = client.post(
        f"/api/staging/jobs/{job_data['job_id']}/upload",
        files=files,
        headers=headers,
        data={"image_type": "original"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["image_type"] == "original"
    assert data["job_id"] == job_data["job_id"]


def test_upload_image_invalid_type(test_client_user):
    """Test uploading invalid file type."""
    headers = {"Authorization": f"Bearer {test_client_user['token']}"}
    
    # Create property and job
    from service.staging_db import create_property, create_job
    property_data = create_property(
        test_client_user["tenant"]["tenant_id"],
        test_client_user["user_id"],
        "456 Invalid St",
    )
    job_data = create_job(
        test_client_user["tenant"]["tenant_id"],
        property_data["property_id"],
        test_client_user["user_id"],
    )
    
    # Try to upload non-image file
    files = {"file": ("test.txt", b"not an image", "text/plain")}
    response = client.post(
        f"/api/staging/jobs/{job_data['job_id']}/upload",
        files=files,
        headers=headers,
        data={"image_type": "original"},
    )
    assert response.status_code == 400


def test_list_job_images(test_client_user):
    """Test listing images for a job."""
    headers = {"Authorization": f"Bearer {test_client_user['token']}"}
    
    # Create property and job
    from service.staging_db import create_property, create_job
    property_data = create_property(
        test_client_user["tenant"]["tenant_id"],
        test_client_user["user_id"],
        "789 List St",
    )
    job_data = create_job(
        test_client_user["tenant"]["tenant_id"],
        property_data["property_id"],
        test_client_user["user_id"],
    )
    
    # List images (should be empty initially)
    response = client.get(
        f"/api/staging/jobs/{job_data['job_id']}/images",
        headers=headers,
    )
    assert response.status_code == 200
    images = response.json()
    assert isinstance(images, list)

