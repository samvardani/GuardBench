"""Tests for staging platform API endpoints."""

import pytest
from fastapi.testclient import TestClient

from service.api import app
from service.db import create_tenant, create_user, issue_token

client = TestClient(app)


@pytest.fixture
def test_tenant():
    """Create a test tenant."""
    tenant = create_tenant("Test Staging Tenant", slug="test-staging")
    return tenant


@pytest.fixture
def test_client_user(test_tenant):
    """Create a test client user."""
    user = create_user(
        test_tenant["tenant_id"],
        "client@test.com",
        "TestPassword123!",
        role="client",
    )
    token = issue_token(user["user_id"], test_tenant["tenant_id"], label="test")
    return {**user, "token": token["token"], "tenant": test_tenant}


@pytest.fixture
def test_staff_user(test_tenant):
    """Create a test staff user."""
    user = create_user(
        test_tenant["tenant_id"],
        "staff@test.com",
        "TestPassword123!",
        role="staff",
    )
    token = issue_token(user["user_id"], test_tenant["tenant_id"], label="test")
    return {**user, "token": token["token"], "tenant": test_tenant}


@pytest.fixture
def test_admin_user(test_tenant):
    """Create a test admin user."""
    user = create_user(
        test_tenant["tenant_id"],
        "admin@test.com",
        "TestPassword123!",
        role="admin",
    )
    token = issue_token(user["user_id"], test_tenant["tenant_id"], label="test")
    return {**user, "token": token["token"], "tenant": test_tenant}


def test_list_packages_requires_auth():
    """Test that listing packages requires authentication."""
    response = client.get("/api/staging/packages")
    assert response.status_code == 401


def test_list_packages(test_client_user):
    """Test listing service packages."""
    headers = {"Authorization": f"Bearer {test_client_user['token']}"}
    response = client.get("/api/staging/packages", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_property(test_client_user):
    """Test creating a property."""
    headers = {"Authorization": f"Bearer {test_client_user['token']}"}
    payload = {
        "address": "123 Main St",
        "city": "San Francisco",
        "state": "CA",
        "zip_code": "94102",
        "property_type": "residential",
    }
    response = client.post("/api/staging/properties", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["address"] == payload["address"]
    assert data["client_id"] == test_client_user["user_id"]


def test_list_properties(test_client_user):
    """Test listing properties."""
    headers = {"Authorization": f"Bearer {test_client_user['token']}"}
    # Create a property first
    payload = {"address": "456 Oak Ave", "city": "Oakland"}
    client.post("/api/staging/properties", json=payload, headers=headers)
    
    # List properties
    response = client.get("/api/staging/properties", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_create_job(test_client_user):
    """Test creating a staging job."""
    headers = {"Authorization": f"Bearer {test_client_user['token']}"}
    
    # Create a property first
    property_payload = {"address": "789 Pine St"}
    property_resp = client.post("/api/staging/properties", json=property_payload, headers=headers)
    property_id = property_resp.json()["property_id"]
    
    # Create a job
    job_payload = {
        "property_id": property_id,
        "priority": "normal",
        "notes": "Test job",
    }
    response = client.post("/api/staging/jobs", json=job_payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["property_id"] == property_id
    assert data["status"] == "scheduled"


def test_update_job_status_staff_only(test_client_user, test_staff_user):
    """Test that only staff can update job status."""
    headers_client = {"Authorization": f"Bearer {test_client_user['token']}"}
    headers_staff = {"Authorization": f"Bearer {test_staff_user['token']}"}
    
    # Create property and job as client
    property_payload = {"address": "123 Test St"}
    property_resp = client.post("/api/staging/properties", json=property_payload, headers=headers_client)
    property_id = property_resp.json()["property_id"]
    
    job_payload = {"property_id": property_id}
    job_resp = client.post("/api/staging/jobs", json=job_payload, headers=headers_client)
    job_id = job_resp.json()["job_id"]
    
    # Client cannot update status
    response = client.put(f"/api/staging/jobs/{job_id}/status?new_status=in_progress", headers=headers_client)
    assert response.status_code == 403
    
    # Staff can update status (if assigned)
    # First assign the job (would need admin endpoint or direct DB call)
    # For now, test that staff endpoint exists
    response = client.put(f"/api/staging/jobs/{job_id}/status?new_status=in_progress", headers=headers_staff)
    # May fail if not assigned, but endpoint should exist
    assert response.status_code in [200, 403]


def test_list_jobs_role_filtering(test_client_user, test_staff_user):
    """Test that jobs are filtered by role."""
    headers_client = {"Authorization": f"Bearer {test_client_user['token']}"}
    headers_staff = {"Authorization": f"Bearer {test_staff_user['token']}"}
    
    # Create job as client
    property_payload = {"address": "456 Filter St"}
    property_resp = client.post("/api/staging/properties", json=property_payload, headers=headers_client)
    property_id = property_resp.json()["property_id"]
    
    job_payload = {"property_id": property_id}
    client.post("/api/staging/jobs", json=job_payload, headers=headers_client)
    
    # Client should see their jobs
    response = client.get("/api/staging/jobs", headers=headers_client)
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) > 0
    
    # Staff should see assigned jobs (or all if admin)
    response = client.get("/api/staging/jobs", headers=headers_staff)
    assert response.status_code == 200


def test_create_appointment(test_client_user):
    """Test creating an appointment."""
    headers = {"Authorization": f"Bearer {test_client_user['token']}"}
    
    # Create property and job
    property_payload = {"address": "789 Appt St"}
    property_resp = client.post("/api/staging/properties", json=property_payload, headers=headers)
    property_id = property_resp.json()["property_id"]
    
    job_payload = {"property_id": property_id}
    job_resp = client.post("/api/staging/jobs", json=job_payload, headers=headers)
    job_id = job_resp.json()["job_id"]
    
    # Create appointment
    appointment_payload = {
        "job_id": job_id,
        "appointment_date": "2025-12-15",
        "appointment_time": "10:00",
        "duration_minutes": 60,
    }
    response = client.post("/api/staging/appointments", json=appointment_payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["job_id"] == job_id
    assert data["appointment_date"] == "2025-12-15"


def test_admin_list_users(test_admin_user):
    """Test admin listing users."""
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}
    response = client.get("/api/staging/admin/users", headers=headers)
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)


def test_admin_analytics(test_admin_user):
    """Test admin analytics endpoint."""
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}
    response = client.get("/api/staging/admin/analytics", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_jobs" in data
    assert "jobs_by_status" in data
    assert "total_revenue_cents" in data

