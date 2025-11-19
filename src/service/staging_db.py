"""Database operations for Virtual Staging Platform."""

from __future__ import annotations

import datetime as _dt
import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from service.db import DB_PATH, db_conn, ensure_schema


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


# Service Packages
def create_service_package(
    tenant_id: str,
    name: str,
    price_cents: int,
    *,
    description: Optional[str] = None,
    photo_count: int = 3,
    includes_site_visit: bool = False,
    includes_handyman: bool = False,
) -> Dict[str, Any]:
    ensure_schema()
    package_id = uuid.uuid4().hex
    created = _now()
    with db_conn() as con:
        con.execute(
            """
            INSERT INTO service_packages 
            (package_id, tenant_id, name, description, price_cents, photo_count, includes_site_visit, includes_handyman, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """,
            (package_id, tenant_id, name, description, price_cents, photo_count, 1 if includes_site_visit else 0, 1 if includes_handyman else 0, created),
        )
    return {
        "package_id": package_id,
        "tenant_id": tenant_id,
        "name": name,
        "description": description,
        "price_cents": price_cents,
        "photo_count": photo_count,
        "includes_site_visit": includes_site_visit,
        "includes_handyman": includes_handyman,
        "created_at": created,
        "status": "active",
    }


def get_service_packages(tenant_id: str, *, status: Optional[str] = None) -> List[Dict[str, Any]]:
    ensure_schema()
    query = "SELECT * FROM service_packages WHERE tenant_id = ?"
    params: list[Any] = [tenant_id]
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    with db_conn(commit=False) as con:
        rows = con.execute(query, params).fetchall()
    return [dict(row) for row in rows]


# Properties
def create_property(
    tenant_id: str,
    client_id: str,
    address: str,
    *,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    country: str = "US",
    property_type: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_schema()
    property_id = uuid.uuid4().hex
    created = _now()
    with db_conn() as con:
        con.execute(
            """
            INSERT INTO properties 
            (property_id, tenant_id, client_id, address, city, state, zip_code, country, property_type, description, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """,
            (property_id, tenant_id, client_id, address, city, state, zip_code, country, property_type, description, created),
        )
    return {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "client_id": client_id,
        "address": address,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "country": country,
        "property_type": property_type,
        "description": description,
        "created_at": created,
        "status": "active",
    }


def get_property(property_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    ensure_schema()
    with db_conn(commit=False) as con:
        row = con.execute("SELECT * FROM properties WHERE property_id = ? AND tenant_id = ?", (property_id, tenant_id)).fetchone()
    return dict(row) if row else None


def list_properties(tenant_id: str, *, client_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    ensure_schema()
    query = "SELECT * FROM properties WHERE tenant_id = ?"
    params: list[Any] = [tenant_id]
    if client_id:
        query += " AND client_id = ?"
        params.append(client_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    with db_conn(commit=False) as con:
        rows = con.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def update_property(property_id: str, tenant_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ensure_schema()
    if not updates:
        return get_property(property_id, tenant_id)
    set_clauses = []
    params: list[Any] = []
    for key, value in updates.items():
        if value is not None:
            set_clauses.append(f"{key} = ?")
            params.append(value)
    if not set_clauses:
        return get_property(property_id, tenant_id)
    set_clauses.append("updated_at = ?")
    params.append(_now())
    params.extend([property_id, tenant_id])
    with db_conn() as con:
        con.execute(f"UPDATE properties SET {', '.join(set_clauses)} WHERE property_id = ? AND tenant_id = ?", params)
    return get_property(property_id, tenant_id)


# Jobs
def create_job(
    tenant_id: str,
    property_id: str,
    client_id: str,
    *,
    package_id: Optional[str] = None,
    scheduled_date: Optional[str] = None,
    scheduled_time: Optional[str] = None,
    priority: str = "normal",
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_schema()
    job_id = uuid.uuid4().hex
    created = _now()
    with db_conn() as con:
        con.execute(
            """
            INSERT INTO jobs 
            (job_id, tenant_id, property_id, client_id, package_id, scheduled_date, scheduled_time, priority, notes, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'scheduled')
            """,
            (job_id, tenant_id, property_id, client_id, package_id, scheduled_date, scheduled_time, priority, notes, created),
        )
    return {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "property_id": property_id,
        "client_id": client_id,
        "package_id": package_id,
        "scheduled_date": scheduled_date,
        "scheduled_time": scheduled_time,
        "priority": priority,
        "notes": notes,
        "created_at": created,
        "status": "scheduled",
    }


def get_job(job_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    ensure_schema()
    with db_conn(commit=False) as con:
        row = con.execute("SELECT * FROM jobs WHERE job_id = ? AND tenant_id = ?", (job_id, tenant_id)).fetchone()
    return dict(row) if row else None


def list_jobs(
    tenant_id: str,
    *,
    client_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    status: Optional[str] = None,
    property_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    ensure_schema()
    query = "SELECT * FROM jobs WHERE tenant_id = ?"
    params: list[Any] = [tenant_id]
    if client_id:
        query += " AND client_id = ?"
        params.append(client_id)
    if staff_id:
        query += " AND assigned_staff_id = ?"
        params.append(staff_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    if property_id:
        query += " AND property_id = ?"
        params.append(property_id)
    query += " ORDER BY created_at DESC"
    with db_conn(commit=False) as con:
        rows = con.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def update_job(job_id: str, tenant_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ensure_schema()
    if not updates:
        return get_job(job_id, tenant_id)
    set_clauses = []
    params: list[Any] = []
    for key, value in updates.items():
        if value is not None:
            set_clauses.append(f"{key} = ?")
            params.append(value)
    if not set_clauses:
        return get_job(job_id, tenant_id)
    set_clauses.append("updated_at = ?")
    params.append(_now())
    if updates.get("status") == "completed":
        set_clauses.append("completed_at = ?")
        params.append(_now())
    params.extend([job_id, tenant_id])
    with db_conn() as con:
        con.execute(f"UPDATE jobs SET {', '.join(set_clauses)} WHERE job_id = ? AND tenant_id = ?", params)
    return get_job(job_id, tenant_id)


# Appointments
def create_appointment(
    tenant_id: str,
    job_id: str,
    appointment_date: str,
    appointment_time: str,
    *,
    staff_id: Optional[str] = None,
    duration_minutes: int = 60,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_schema()
    appointment_id = uuid.uuid4().hex
    created = _now()
    with db_conn() as con:
        con.execute(
            """
            INSERT INTO appointments 
            (appointment_id, tenant_id, job_id, staff_id, appointment_date, appointment_time, duration_minutes, notes, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'scheduled')
            """,
            (appointment_id, tenant_id, job_id, staff_id, appointment_date, appointment_time, duration_minutes, notes, created),
        )
    return {
        "appointment_id": appointment_id,
        "tenant_id": tenant_id,
        "job_id": job_id,
        "staff_id": staff_id,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "duration_minutes": duration_minutes,
        "notes": notes,
        "created_at": created,
        "status": "scheduled",
    }


def check_appointment_conflict(tenant_id: str, appointment_date: str, appointment_time: str, duration_minutes: int, *, exclude_appointment_id: Optional[str] = None, staff_id: Optional[str] = None) -> bool:
    """Check if an appointment conflicts with existing appointments."""
    ensure_schema()
    # Simple conflict check: same date/time with overlapping duration
    # In production, would need more sophisticated time overlap calculation
    query = """
        SELECT COUNT(*) FROM appointments 
        WHERE tenant_id = ? AND appointment_date = ? AND appointment_time = ? AND status != 'cancelled'
    """
    params: list[Any] = [tenant_id, appointment_date, appointment_time]
    if exclude_appointment_id:
        query += " AND appointment_id != ?"
        params.append(exclude_appointment_id)
    if staff_id:
        query += " AND staff_id = ?"
        params.append(staff_id)
    with db_conn(commit=False) as con:
        count = con.execute(query, params).fetchone()[0]
    return count > 0


def list_appointments(
    tenant_id: str,
    *,
    job_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    ensure_schema()
    query = "SELECT * FROM appointments WHERE tenant_id = ?"
    params: list[Any] = [tenant_id]
    if job_id:
        query += " AND job_id = ?"
        params.append(job_id)
    if staff_id:
        query += " AND staff_id = ?"
        params.append(staff_id)
    if start_date:
        query += " AND appointment_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND appointment_date <= ?"
        params.append(end_date)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY appointment_date, appointment_time"
    with db_conn(commit=False) as con:
        rows = con.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_appointment(appointment_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    ensure_schema()
    with db_conn(commit=False) as con:
        row = con.execute("SELECT * FROM appointments WHERE appointment_id = ? AND tenant_id = ?", (appointment_id, tenant_id)).fetchone()
    return dict(row) if row else None


def update_appointment(appointment_id: str, tenant_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ensure_schema()
    if not updates:
        return get_appointment(appointment_id, tenant_id)
    set_clauses = []
    params: list[Any] = []
    for key, value in updates.items():
        if value is not None:
            set_clauses.append(f"{key} = ?")
            params.append(value)
    if not set_clauses:
        return get_appointment(appointment_id, tenant_id)
    set_clauses.append("updated_at = ?")
    params.append(_now())
    if updates.get("status") == "cancelled":
        set_clauses.append("cancelled_at = ?")
        params.append(_now())
    params.extend([appointment_id, tenant_id])
    with db_conn() as con:
        con.execute(f"UPDATE appointments SET {', '.join(set_clauses)} WHERE appointment_id = ? AND tenant_id = ?", params)
    return get_appointment(appointment_id, tenant_id)


# Job Images
def create_job_image(
    tenant_id: str,
    job_id: str,
    image_url: str,
    filename: str,
    image_type: str,
    *,
    thumbnail_url: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    mime_type: Optional[str] = None,
    uploaded_by: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ensure_schema()
    image_id = uuid.uuid4().hex
    uploaded_at = _now()
    metadata_json = json.dumps(metadata) if metadata else None
    with db_conn() as con:
        con.execute(
            """
            INSERT INTO job_images 
            (image_id, tenant_id, job_id, image_url, thumbnail_url, image_type, filename, file_size_bytes, mime_type, uploaded_by, uploaded_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (image_id, tenant_id, job_id, image_url, thumbnail_url, image_type, filename, file_size_bytes, mime_type, uploaded_by, uploaded_at, metadata_json),
        )
    return {
        "image_id": image_id,
        "tenant_id": tenant_id,
        "job_id": job_id,
        "image_url": image_url,
        "thumbnail_url": thumbnail_url,
        "image_type": image_type,
        "filename": filename,
        "file_size_bytes": file_size_bytes,
        "mime_type": mime_type,
        "uploaded_by": uploaded_by,
        "uploaded_at": uploaded_at,
        "metadata": metadata,
    }


def list_job_images(job_id: str, tenant_id: str, *, image_type: Optional[str] = None) -> List[Dict[str, Any]]:
    ensure_schema()
    query = "SELECT * FROM job_images WHERE job_id = ? AND tenant_id = ?"
    params: list[Any] = [job_id, tenant_id]
    if image_type:
        query += " AND image_type = ?"
        params.append(image_type)
    query += " ORDER BY uploaded_at DESC"
    with db_conn(commit=False) as con:
        rows = con.execute(query, params).fetchall()
    result = []
    for row in rows:
        data = dict(row)
        if data.get("metadata"):
            try:
                data["metadata"] = json.loads(data["metadata"])
            except (json.JSONDecodeError, TypeError):
                data["metadata"] = None
        result.append(data)
    return result


# Payments
def create_payment(
    tenant_id: str,
    job_id: str,
    client_id: str,
    amount_cents: int,
    *,
    stripe_payment_intent_id: Optional[str] = None,
    stripe_checkout_session_id: Optional[str] = None,
    currency: str = "usd",
    status: str = "pending",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ensure_schema()
    payment_id = uuid.uuid4().hex
    created = _now()
    metadata_json = json.dumps(metadata) if metadata else None
    with db_conn() as con:
        con.execute(
            """
            INSERT INTO payments 
            (payment_id, tenant_id, job_id, client_id, stripe_payment_intent_id, stripe_checkout_session_id, 
             amount_cents, currency, status, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (payment_id, tenant_id, job_id, client_id, stripe_payment_intent_id, stripe_checkout_session_id, amount_cents, currency, status, created, metadata_json),
        )
    return {
        "payment_id": payment_id,
        "tenant_id": tenant_id,
        "job_id": job_id,
        "client_id": client_id,
        "stripe_payment_intent_id": stripe_payment_intent_id,
        "stripe_checkout_session_id": stripe_checkout_session_id,
        "amount_cents": amount_cents,
        "currency": currency,
        "status": status,
        "created_at": created,
        "metadata": metadata,
    }


def get_payment(payment_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    ensure_schema()
    with db_conn(commit=False) as con:
        row = con.execute("SELECT * FROM payments WHERE payment_id = ? AND tenant_id = ?", (payment_id, tenant_id)).fetchone()
    if not row:
        return None
    data = dict(row)
    if data.get("metadata"):
        try:
            data["metadata"] = json.loads(data["metadata"])
        except (json.JSONDecodeError, TypeError):
            data["metadata"] = None
    return data


def update_payment(payment_id: str, tenant_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ensure_schema()
    if not updates:
        return get_payment(payment_id, tenant_id)
    set_clauses = []
    params: list[Any] = []
    for key, value in updates.items():
        if value is not None:
            set_clauses.append(f"{key} = ?")
            params.append(value)
    if not set_clauses:
        return get_payment(payment_id, tenant_id)
    set_clauses.append("updated_at = ?")
    params.append(_now())
    if updates.get("status") == "succeeded":
        set_clauses.append("paid_at = ?")
        params.append(_now())
    if updates.get("status") == "refunded":
        set_clauses.append("refunded_at = ?")
        params.append(_now())
    params.extend([payment_id, tenant_id])
    with db_conn() as con:
        con.execute(f"UPDATE payments SET {', '.join(set_clauses)} WHERE payment_id = ? AND tenant_id = ?", params)
    return get_payment(payment_id, tenant_id)


def get_payment_by_stripe_session(session_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    ensure_schema()
    with db_conn(commit=False) as con:
        row = con.execute("SELECT * FROM payments WHERE stripe_checkout_session_id = ? AND tenant_id = ?", (session_id, tenant_id)).fetchone()
    if not row:
        return None
    data = dict(row)
    if data.get("metadata"):
        try:
            data["metadata"] = json.loads(data["metadata"])
        except (json.JSONDecodeError, TypeError):
            data["metadata"] = None
    return data


# Job Activities
def create_job_activity(
    tenant_id: str,
    job_id: str,
    activity_type: str,
    *,
    user_id: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ensure_schema()
    activity_id = uuid.uuid4().hex
    created = _now()
    metadata_json = json.dumps(metadata) if metadata else None
    with db_conn() as con:
        con.execute(
            """
            INSERT INTO job_activities 
            (activity_id, tenant_id, job_id, user_id, activity_type, description, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (activity_id, tenant_id, job_id, user_id, activity_type, description, metadata_json, created),
        )
    return {
        "activity_id": activity_id,
        "tenant_id": tenant_id,
        "job_id": job_id,
        "user_id": user_id,
        "activity_type": activity_type,
        "description": description,
        "metadata": metadata,
        "created_at": created,
    }


def list_job_activities(job_id: str, tenant_id: str, *, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    ensure_schema()
    query = "SELECT * FROM job_activities WHERE job_id = ? AND tenant_id = ? ORDER BY created_at DESC"
    params: list[Any] = [job_id, tenant_id]
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    with db_conn(commit=False) as con:
        rows = con.execute(query, params).fetchall()
    result = []
    for row in rows:
        data = dict(row)
        if data.get("metadata"):
            try:
                data["metadata"] = json.loads(data["metadata"])
            except (json.JSONDecodeError, TypeError):
                data["metadata"] = None
        result.append(data)
    return result

