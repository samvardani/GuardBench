"""API endpoints for Virtual Staging Platform."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from service.api import AuthContext, require_auth, require_any_role
from service.staging_db import (
    create_appointment,
    create_job,
    create_job_activity,
    create_property,
    create_service_package,
    get_appointment,
    get_job,
    get_property,
    get_service_packages,
    list_appointments,
    list_job_activities,
    list_jobs,
    list_properties,
    update_appointment,
    update_job,
    update_property,
)
from service.staging_notifications import notify_job_status_change
from service.staging_models import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentUpdate,
    AvailabilityRequest,
    AvailabilityResponse,
    JobCreate,
    JobResponse,
    JobUpdate,
    PropertyCreate,
    PropertyResponse,
    PropertyUpdate,
    ServicePackageCreate,
    ServicePackageResponse,
    TimeSlot,
)

router = APIRouter(prefix="/api/staging", tags=["staging"])


# Service Packages
@router.post("/packages", response_model=ServicePackageResponse, status_code=status.HTTP_201_CREATED)
def create_package(
    payload: ServicePackageCreate,
    ctx: AuthContext = Depends(require_any_role("admin", "manager", "owner")),
) -> Dict[str, Any]:
    """Create a new service package (admin/manager only)."""
    package = create_service_package(
        tenant_id=ctx.tenant_id,
        name=payload.name,
        description=payload.description,
        price_cents=payload.price_cents,
        photo_count=payload.photo_count,
        includes_site_visit=payload.includes_site_visit,
        includes_handyman=payload.includes_handyman,
    )
    return package


@router.get("/packages", response_model=List[ServicePackageResponse])
def list_packages(
    ctx: AuthContext = Depends(require_auth),
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all service packages (all authenticated users)."""
    packages = get_service_packages(ctx.tenant_id, status=status_filter)
    return packages


# Properties
@router.post("/properties", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
def create_property_endpoint(
    payload: PropertyCreate,
    ctx: AuthContext = Depends(require_any_role("client", "admin", "manager", "owner")),
) -> Dict[str, Any]:
    """Create a new property listing."""
    if ctx.role == "client" and ctx.user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID required")
    property_data = create_property(
        tenant_id=ctx.tenant_id,
        client_id=ctx.user_id or "",
        address=payload.address,
        city=payload.city,
        state=payload.state,
        zip_code=payload.zip_code,
        country=payload.country,
        property_type=payload.property_type,
        description=payload.description,
    )
    return property_data


@router.get("/properties", response_model=List[PropertyResponse])
def list_properties_endpoint(
    ctx: AuthContext = Depends(require_auth),
    client_id: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List properties. Clients see only their own; staff/admin see all."""
    # Clients can only see their own properties
    if ctx.role == "client":
        client_id = ctx.user_id
    properties = list_properties(ctx.tenant_id, client_id=client_id, status=status_filter)
    return properties


@router.get("/properties/{property_id}", response_model=PropertyResponse)
def get_property_endpoint(
    property_id: str,
    ctx: AuthContext = Depends(require_auth),
) -> Dict[str, Any]:
    """Get property details."""
    property_data = get_property(property_id, ctx.tenant_id)
    if not property_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    # Clients can only access their own properties
    if ctx.role == "client" and property_data.get("client_id") != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return property_data


@router.put("/properties/{property_id}", response_model=PropertyResponse)
def update_property_endpoint(
    property_id: str,
    payload: PropertyUpdate,
    ctx: AuthContext = Depends(require_auth),
) -> Dict[str, Any]:
    """Update property details."""
    property_data = get_property(property_id, ctx.tenant_id)
    if not property_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    # Clients can only update their own properties
    if ctx.role == "client" and property_data.get("client_id") != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    updates = payload.model_dump(exclude_unset=True)
    updated = update_property(property_id, ctx.tenant_id, updates)
    return updated or property_data


# Jobs
@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job_endpoint(
    payload: JobCreate,
    ctx: AuthContext = Depends(require_any_role("client", "admin", "manager", "owner")),
) -> Dict[str, Any]:
    """Create a new staging job."""
    if ctx.role == "client" and ctx.user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID required")
    # Verify property belongs to client (if client role)
    if ctx.role == "client":
        property_data = get_property(payload.property_id, ctx.tenant_id)
        if not property_data or property_data.get("client_id") != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Property not found or access denied")
    job = create_job(
        tenant_id=ctx.tenant_id,
        property_id=payload.property_id,
        client_id=ctx.user_id or "",
        package_id=payload.package_id,
        scheduled_date=payload.scheduled_date,
        scheduled_time=payload.scheduled_time,
        priority=payload.priority,
        notes=payload.notes,
    )
    # Log activity
    create_job_activity(
        tenant_id=ctx.tenant_id,
        job_id=job["job_id"],
        activity_type="job_created",
        user_id=ctx.user_id,
        description=f"Job created by {ctx.role}",
    )
    return job


@router.get("/jobs", response_model=List[JobResponse])
def list_jobs_endpoint(
    ctx: AuthContext = Depends(require_auth),
    client_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    property_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List jobs. Filtered by role: clients see their own, staff see assigned, admin/manager see all."""
    # Role-based filtering
    if ctx.role == "client":
        client_id = ctx.user_id
    elif ctx.role == "staff":
        staff_id = ctx.user_id
    # Admin/manager can see all, but can filter
    jobs = list_jobs(
        ctx.tenant_id,
        client_id=client_id,
        staff_id=staff_id,
        status=status_filter,
        property_id=property_id,
    )
    return jobs


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job_endpoint(
    job_id: str,
    ctx: AuthContext = Depends(require_auth),
) -> Dict[str, Any]:
    """Get job details."""
    job = get_job(job_id, ctx.tenant_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    # Role-based access control
    if ctx.role == "client" and job.get("client_id") != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if ctx.role == "staff" and job.get("assigned_staff_id") != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return job


@router.put("/jobs/{job_id}", response_model=JobResponse)
def update_job_endpoint(
    job_id: str,
    payload: JobUpdate,
    ctx: AuthContext = Depends(require_auth),
) -> Dict[str, Any]:
    """Update job details."""
    job = get_job(job_id, ctx.tenant_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    # Role-based access control
    if ctx.role == "client":
        if job.get("client_id") != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        # Clients can only update notes
        updates = {"notes": payload.notes} if payload.notes is not None else {}
    elif ctx.role == "staff":
        if job.get("assigned_staff_id") != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        # Staff can update status and notes
        updates = payload.model_dump(exclude_unset=True, exclude={"assigned_staff_id", "scheduled_date", "scheduled_time", "priority"})
    else:
        # Admin/manager can update everything
        updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return job
    updated = update_job(job_id, ctx.tenant_id, updates)
    # Log activity
    if "status" in updates:
        create_job_activity(
            tenant_id=ctx.tenant_id,
            job_id=job_id,
            activity_type="status_change",
            user_id=ctx.user_id,
            description=f"Status changed to {updates['status']}",
            metadata={"old_status": job.get("status"), "new_status": updates["status"]},
        )
    return updated or job


@router.put("/jobs/{job_id}/status", response_model=JobResponse)
def update_job_status(
    job_id: str,
    new_status: str,
    ctx: AuthContext = Depends(require_any_role("staff", "manager", "admin", "owner")),
) -> Dict[str, Any]:
    """Update job status (staff/admin only)."""
    job = get_job(job_id, ctx.tenant_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if ctx.role == "staff" and job.get("assigned_staff_id") != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    valid_statuses = ["scheduled", "in_progress", "photos_staged", "completed", "cancelled"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    old_status = job.get("status")
    updated = update_job(job_id, ctx.tenant_id, {"status": new_status})
    # Log activity
    create_job_activity(
        tenant_id=ctx.tenant_id,
        job_id=job_id,
        activity_type="status_change",
        user_id=ctx.user_id,
        description=f"Status changed from {old_status} to {new_status}",
        metadata={"old_status": old_status, "new_status": new_status},
    )
    # Send notification if status changed
    if updated and old_status != new_status:
        try:
            # Get client email (would need to fetch from users table in production)
            notify_job_status_change(
                job=updated,
                old_status=old_status,
                new_status=new_status,
            )
        except Exception as e:
            # Don't fail the request if notification fails
            import logging
            logging.getLogger(__name__).warning(f"Failed to send notification: {e}")
    return updated or job


# Appointments
@router.post("/appointments", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment_endpoint(
    payload: AppointmentCreate,
    ctx: AuthContext = Depends(require_any_role("client", "admin", "manager", "owner")),
) -> Dict[str, Any]:
    """Create a new appointment."""
    # Verify job exists and belongs to client (if client role)
    if ctx.role == "client":
        job = get_job(payload.job_id, ctx.tenant_id)
        if not job or job.get("client_id") != ctx.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Job not found or access denied")
    # Check for conflicts
    from service.staging_db import check_appointment_conflict
    if check_appointment_conflict(
        ctx.tenant_id,
        payload.appointment_date,
        payload.appointment_time,
        payload.duration_minutes,
        staff_id=payload.staff_id,
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Appointment time slot already booked")
    appointment = create_appointment(
        tenant_id=ctx.tenant_id,
        job_id=payload.job_id,
        staff_id=payload.staff_id,
        appointment_date=payload.appointment_date,
        appointment_time=payload.appointment_time,
        duration_minutes=payload.duration_minutes,
        notes=payload.notes,
    )
    return appointment


@router.get("/appointments", response_model=List[AppointmentResponse])
def list_appointments_endpoint(
    ctx: AuthContext = Depends(require_auth),
    job_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List appointments."""
    # Role-based filtering
    if ctx.role == "staff":
        staff_id = ctx.user_id
    appointments = list_appointments(
        ctx.tenant_id,
        job_id=job_id,
        staff_id=staff_id,
        start_date=start_date,
        end_date=end_date,
        status=status_filter,
    )
    return appointments


@router.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
def get_appointment_endpoint(
    appointment_id: str,
    ctx: AuthContext = Depends(require_auth),
) -> Dict[str, Any]:
    """Get appointment details."""
    appointment = get_appointment(appointment_id, ctx.tenant_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    # Role-based access: staff can only see their own
    if ctx.role == "staff" and appointment.get("staff_id") != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return appointment


@router.put("/appointments/{appointment_id}", response_model=AppointmentResponse)
def update_appointment_endpoint(
    appointment_id: str,
    payload: AppointmentUpdate,
    ctx: AuthContext = Depends(require_auth),
) -> Dict[str, Any]:
    """Update appointment."""
    appointment = get_appointment(appointment_id, ctx.tenant_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    # Role-based access
    if ctx.role == "staff" and appointment.get("staff_id") != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    updates = payload.model_dump(exclude_unset=True)
    # Check for conflicts if date/time changed
    if "appointment_date" in updates or "appointment_time" in updates:
        from service.staging_db import check_appointment_conflict
        date = updates.get("appointment_date", appointment.get("appointment_date"))
        time = updates.get("appointment_time", appointment.get("appointment_time"))
        duration = updates.get("duration_minutes", appointment.get("duration_minutes", 60))
        if check_appointment_conflict(
            ctx.tenant_id,
            date,
            time,
            duration,
            exclude_appointment_id=appointment_id,
            staff_id=updates.get("staff_id", appointment.get("staff_id")),
        ):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Appointment time slot already booked")
    updated = update_appointment(appointment_id, ctx.tenant_id, updates)
    return updated or appointment


@router.delete("/appointments/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment_endpoint(
    appointment_id: str,
    ctx: AuthContext = Depends(require_auth),
) -> None:
    """Cancel/delete appointment."""
    appointment = get_appointment(appointment_id, ctx.tenant_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    # Role-based access
    if ctx.role == "staff" and appointment.get("staff_id") != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    update_appointment(appointment_id, ctx.tenant_id, {"status": "cancelled", "cancelled_reason": "Cancelled by user"})


# Availability & Scheduling
@router.post("/availability", response_model=AvailabilityResponse)
def get_availability(
    payload: AvailabilityRequest,
    ctx: AuthContext = Depends(require_auth),
) -> Dict[str, Any]:
    """
    Get available time slots for booking appointments.
    
    Returns available slots between start_date and end_date.
    Business hours: 9 AM - 5 PM, Monday-Friday
    """
    from datetime import datetime, timedelta
    
    # Get existing appointments in the date range
    existing_appointments = list_appointments(
        ctx.tenant_id,
        staff_id=payload.staff_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status="scheduled",
    )
    
    # Create a set of booked slots
    booked_slots = set()
    for apt in existing_appointments:
        booked_slots.add((apt["appointment_date"], apt["appointment_time"]))
    
    # Generate time slots (9 AM - 5 PM, hourly)
    slots = []
    start = datetime.strptime(payload.start_date, "%Y-%m-%d")
    end = datetime.strptime(payload.end_date, "%Y-%m-%d")
    
    current_date = start
    while current_date <= end:
        # Skip weekends
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            date_str = current_date.strftime("%Y-%m-%d")
            # Generate hourly slots from 9 AM to 4 PM (last slot starts at 4 PM, ends at 5 PM)
            for hour in range(9, 17):
                time_str = f"{hour:02d}:00"
                slot_key = (date_str, time_str)
                available = slot_key not in booked_slots
                slots.append(TimeSlot(
                    date=date_str,
                    time=time_str,
                    available=available,
                    staff_id=payload.staff_id,
                ))
        current_date += timedelta(days=1)
    
    return AvailabilityResponse(slots=slots)


# Job Activities
@router.get("/jobs/{job_id}/activities")
def list_job_activities_endpoint(
    job_id: str,
    ctx: AuthContext = Depends(require_auth),
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """List job activity log."""
    job = get_job(job_id, ctx.tenant_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    # Role-based access
    if ctx.role == "client" and job.get("client_id") != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if ctx.role == "staff" and job.get("assigned_staff_id") != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    activities = list_job_activities(job_id, ctx.tenant_id, limit=limit)
    return {"activities": activities}

