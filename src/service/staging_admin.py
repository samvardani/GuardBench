"""Admin API endpoints for staging platform."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from service.api import AuthContext, require_auth, require_any_role
from service.db import create_user as db_create_user, list_users as db_list_users
from service.staging_db import (
    get_job,
    get_service_packages,
    list_jobs,
    list_properties,
    update_job,
)
from service.staging_models import AnalyticsResponse, UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/api/staging/admin", tags=["staging-admin"])


@router.get("/users", response_model=List[UserResponse])
def list_users_admin(
    ctx: AuthContext = Depends(require_any_role("admin", "manager", "owner")),
    role_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all users (admin/manager only)."""
    users = db_list_users(ctx.tenant_id)
    # Apply filters
    if role_filter:
        users = [u for u in users if u.get("role") == role_filter]
    if status_filter:
        users = [u for u in users if u.get("status") == status_filter]
    return users


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user_admin(
    payload: UserCreate,
    ctx: AuthContext = Depends(require_any_role("admin", "manager", "owner")),
) -> Dict[str, Any]:
    """Create a new user (admin/manager only)."""
    # Validate role
    valid_roles = ["client", "staff", "manager", "admin"]
    if payload.role not in valid_roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    # Only owner can create admin users
    if payload.role == "admin" and ctx.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can create admin users")
    
    try:
        user = db_create_user(
            tenant_id=ctx.tenant_id,
            email=payload.email,
            password=payload.password,
            role=payload.role,
            status=payload.status,
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user_admin(
    user_id: str,
    payload: UserUpdate,
    ctx: AuthContext = Depends(require_any_role("admin", "manager", "owner")),
) -> Dict[str, Any]:
    """Update user (admin/manager only)."""
    from service.db import get_user, update_user
    
    user = get_user(user_id, ctx.tenant_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Only owner can change roles to admin
    if payload.role == "admin" and ctx.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can assign admin role")
    
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return user
    
    # Update user
    from service.db import update_user
    updated = update_user(user_id, ctx.tenant_id, updates)
    return updated or user


@router.get("/jobs", response_model=List[Dict[str, Any]])
def list_all_jobs_admin(
    ctx: AuthContext = Depends(require_any_role("admin", "manager", "owner")),
    client_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    property_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all jobs (admin view - no filtering by role)."""
    jobs = list_jobs(
        ctx.tenant_id,
        client_id=client_id,
        staff_id=staff_id,
        status=status_filter,
        property_id=property_id,
    )
    return jobs


@router.post("/jobs/{job_id}/assign")
def assign_job_staff(
    job_id: str,
    staff_id: str,
    ctx: AuthContext = Depends(require_any_role("admin", "manager", "owner")),
) -> Dict[str, Any]:
    """Assign staff member to a job (admin/manager only)."""
    job = get_job(job_id, ctx.tenant_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    # Verify staff user exists and has staff role
    from service.db import get_user
    staff_user = get_user(staff_id, ctx.tenant_id)
    if not staff_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found")
    if staff_user.get("role") not in ["staff", "manager", "admin"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must have staff, manager, or admin role")
    
    updated = update_job(job_id, ctx.tenant_id, {"assigned_staff_id": staff_id})
    return updated or job


@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(
    ctx: AuthContext = Depends(require_any_role("admin", "manager", "owner")),
) -> Dict[str, Any]:
    """Get platform analytics (admin/manager only)."""
    # Get all jobs
    all_jobs = list_jobs(ctx.tenant_id)
    
    # Calculate metrics
    total_jobs = len(all_jobs)
    jobs_by_status = {}
    total_revenue_cents = 0
    jobs_this_month = 0
    revenue_this_month_cents = 0
    
    from datetime import datetime
    current_month = datetime.now().strftime("%Y-%m")
    
    for job in all_jobs:
        status = job.get("status", "unknown")
        jobs_by_status[status] = jobs_by_status.get(status, 0) + 1
        
        # Check if job is from this month
        created_at = job.get("created_at", "")
        if created_at.startswith(current_month):
            jobs_this_month += 1
        
        # Get payment for job (would need to query payments table)
        # For now, estimate revenue from package prices
        if job.get("package_id"):
            packages = get_service_packages(ctx.tenant_id)
            package = next((p for p in packages if p["package_id"] == job["package_id"]), None)
            if package:
                amount = package.get("price_cents", 0)
                total_revenue_cents += amount
                if created_at.startswith(current_month):
                    revenue_this_month_cents += amount
    
    # Count active staff and clients
    users = db_list_users(ctx.tenant_id)
    active_staff_count = len([u for u in users if u.get("role") in ["staff", "manager", "admin"] and u.get("status") == "active"])
    active_clients_count = len([u for u in users if u.get("role") == "client" and u.get("status") == "active"])
    
    return {
        "total_jobs": total_jobs,
        "jobs_by_status": jobs_by_status,
        "total_revenue_cents": total_revenue_cents,
        "jobs_this_month": jobs_this_month,
        "revenue_this_month_cents": revenue_this_month_cents,
        "active_staff_count": active_staff_count,
        "active_clients_count": active_clients_count,
    }


@router.get("/properties", response_model=List[Dict[str, Any]])
def list_all_properties_admin(
    ctx: AuthContext = Depends(require_any_role("admin", "manager", "owner")),
    client_id: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all properties (admin view)."""
    from service.staging_db import list_properties
    properties = list_properties(ctx.tenant_id, client_id=client_id, status=status_filter)
    return properties

