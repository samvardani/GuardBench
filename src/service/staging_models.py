"""Pydantic models for Virtual Staging Platform API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


# Service Package Models
class ServicePackageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    price_cents: int = Field(..., gt=0)
    photo_count: int = Field(default=3, ge=1)
    includes_site_visit: bool = False
    includes_handyman: bool = False


class ServicePackageResponse(BaseModel):
    package_id: str
    tenant_id: str
    name: str
    description: Optional[str]
    price_cents: int
    photo_count: int
    includes_site_visit: bool
    includes_handyman: bool
    created_at: str
    updated_at: Optional[str]
    status: str

    class Config:
        from_attributes = True


# Property Models
class PropertyCreate(BaseModel):
    address: str = Field(..., min_length=1, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(default="US", max_length=2)
    property_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None


class PropertyUpdate(BaseModel):
    address: Optional[str] = Field(None, min_length=1, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=2)
    property_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    status: Optional[str] = None


class PropertyResponse(BaseModel):
    property_id: str
    tenant_id: str
    client_id: str
    address: str
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    country: str
    property_type: Optional[str]
    description: Optional[str]
    created_at: str
    updated_at: Optional[str]
    status: str

    class Config:
        from_attributes = True


# Job Models
class JobCreate(BaseModel):
    property_id: str
    package_id: Optional[str] = None
    scheduled_date: Optional[str] = None  # ISO date string
    scheduled_time: Optional[str] = None  # HH:MM format
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    notes: Optional[str] = None


class JobUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(scheduled|in_progress|photos_staged|completed|cancelled)$")
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    assigned_staff_id: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(low|normal|high|urgent)$")
    notes: Optional[str] = None


class JobResponse(BaseModel):
    job_id: str
    tenant_id: str
    property_id: str
    client_id: str
    package_id: Optional[str]
    assigned_staff_id: Optional[str]
    status: str
    scheduled_date: Optional[str]
    scheduled_time: Optional[str]
    priority: str
    notes: Optional[str]
    created_at: str
    updated_at: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True


# Appointment Models
class AppointmentCreate(BaseModel):
    job_id: str
    staff_id: Optional[str] = None
    appointment_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    appointment_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    duration_minutes: int = Field(default=60, ge=15, le=480)
    notes: Optional[str] = None


class AppointmentUpdate(BaseModel):
    appointment_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    appointment_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    staff_id: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(scheduled|confirmed|completed|cancelled)$")
    notes: Optional[str] = None
    cancelled_reason: Optional[str] = None


class AppointmentResponse(BaseModel):
    appointment_id: str
    tenant_id: str
    job_id: str
    staff_id: Optional[str]
    appointment_date: str
    appointment_time: str
    duration_minutes: int
    status: str
    notes: Optional[str]
    created_at: str
    updated_at: Optional[str]
    cancelled_at: Optional[str]
    cancelled_reason: Optional[str]

    class Config:
        from_attributes = True


# Availability Models
class AvailabilityRequest(BaseModel):
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    staff_id: Optional[str] = None


class TimeSlot(BaseModel):
    date: str
    time: str
    available: bool
    staff_id: Optional[str] = None


class AvailabilityResponse(BaseModel):
    slots: List[TimeSlot]


# Image Upload Models
class ImageUploadResponse(BaseModel):
    image_id: str
    job_id: str
    image_url: str
    thumbnail_url: Optional[str]
    image_type: str
    filename: str
    file_size_bytes: int
    uploaded_at: str

    class Config:
        from_attributes = True


# Payment Models
class CheckoutRequest(BaseModel):
    job_id: str
    success_url: str = Field(..., min_length=1)
    cancel_url: str = Field(..., min_length=1)


class PaymentResponse(BaseModel):
    payment_id: str
    job_id: str
    client_id: str
    stripe_payment_intent_id: Optional[str]
    stripe_checkout_session_id: Optional[str]
    amount_cents: int
    currency: str
    status: str
    payment_method: Optional[str]
    created_at: str
    updated_at: Optional[str]
    paid_at: Optional[str]
    refunded_at: Optional[str]
    refund_amount_cents: int

    class Config:
        from_attributes = True


# Activity Log Models
class JobActivityResponse(BaseModel):
    activity_id: str
    job_id: str
    user_id: Optional[str]
    activity_type: str
    description: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: str

    class Config:
        from_attributes = True


# Admin Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12)
    role: str = Field(..., pattern="^(client|staff|manager|admin)$")
    status: str = Field(default="active", pattern="^(active|inactive)$")


class UserUpdate(BaseModel):
    role: Optional[str] = Field(None, pattern="^(client|staff|manager|admin)$")
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")


class UserResponse(BaseModel):
    user_id: str
    tenant_id: str
    email: str
    role: str
    status: str
    created_at: str
    last_login_at: Optional[str]

    class Config:
        from_attributes = True


# Analytics Models
class AnalyticsResponse(BaseModel):
    total_jobs: int
    jobs_by_status: Dict[str, int]
    total_revenue_cents: int
    jobs_this_month: int
    revenue_this_month_cents: int
    active_staff_count: int
    active_clients_count: int

