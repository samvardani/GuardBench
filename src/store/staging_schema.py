"""Database schema for Virtual Staging Platform."""

import sqlite3
from typing import Iterable


def create_staging_tables(cursor: sqlite3.Cursor) -> None:
    """Create all staging platform tables."""
    cursor.executescript(
        """
    -- Service packages catalog
    CREATE TABLE IF NOT EXISTS service_packages (
      package_id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      name TEXT NOT NULL,
      description TEXT,
      price_cents INTEGER NOT NULL,
      photo_count INTEGER NOT NULL DEFAULT 3,
      includes_site_visit INTEGER DEFAULT 0,
      includes_handyman INTEGER DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT,
      status TEXT NOT NULL DEFAULT 'active'
    );

    -- Property listings
    CREATE TABLE IF NOT EXISTS properties (
      property_id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      client_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
      address TEXT NOT NULL,
      city TEXT,
      state TEXT,
      zip_code TEXT,
      country TEXT DEFAULT 'US',
      property_type TEXT,
      description TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT,
      status TEXT NOT NULL DEFAULT 'active'
    );

    -- Staging jobs
    CREATE TABLE IF NOT EXISTS jobs (
      job_id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      property_id TEXT NOT NULL REFERENCES properties(property_id) ON DELETE CASCADE,
      client_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
      package_id TEXT REFERENCES service_packages(package_id),
      assigned_staff_id TEXT REFERENCES users(user_id) ON DELETE SET NULL,
      status TEXT NOT NULL DEFAULT 'scheduled',
      scheduled_date TEXT,
      scheduled_time TEXT,
      priority TEXT DEFAULT 'normal',
      notes TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT,
      completed_at TEXT
    );

    -- Appointments for on-site visits
    CREATE TABLE IF NOT EXISTS appointments (
      appointment_id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
      staff_id TEXT REFERENCES users(user_id) ON DELETE SET NULL,
      appointment_date TEXT NOT NULL,
      appointment_time TEXT NOT NULL,
      duration_minutes INTEGER DEFAULT 60,
      status TEXT NOT NULL DEFAULT 'scheduled',
      notes TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT,
      cancelled_at TEXT,
      cancelled_reason TEXT
    );

    -- Job images (uploaded and staged)
    CREATE TABLE IF NOT EXISTS job_images (
      image_id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
      image_url TEXT NOT NULL,
      thumbnail_url TEXT,
      image_type TEXT NOT NULL,  -- 'original' or 'staged'
      filename TEXT NOT NULL,
      file_size_bytes INTEGER,
      mime_type TEXT,
      uploaded_by TEXT REFERENCES users(user_id) ON DELETE SET NULL,
      uploaded_at TEXT NOT NULL,
      metadata TEXT
    );

    -- Payment records
    CREATE TABLE IF NOT EXISTS payments (
      payment_id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
      client_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
      stripe_payment_intent_id TEXT,
      stripe_checkout_session_id TEXT,
      amount_cents INTEGER NOT NULL,
      currency TEXT DEFAULT 'usd',
      status TEXT NOT NULL DEFAULT 'pending',  -- pending, succeeded, failed, refunded
      payment_method TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT,
      paid_at TEXT,
      refunded_at TEXT,
      refund_amount_cents INTEGER DEFAULT 0,
      metadata TEXT
    );

    -- Job activity log
    CREATE TABLE IF NOT EXISTS job_activities (
      activity_id TEXT PRIMARY KEY,
      tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
      job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
      user_id TEXT REFERENCES users(user_id) ON DELETE SET NULL,
      activity_type TEXT NOT NULL,  -- status_change, note_added, image_uploaded, etc.
      description TEXT,
      metadata TEXT,
      created_at TEXT NOT NULL
    );
    """
    )


def create_staging_indexes(cursor: sqlite3.Cursor) -> None:
    """Create indexes for staging platform tables."""
    indexes: Iterable[tuple[str, str]] = (
        ("idx_properties_tenant_client", "CREATE INDEX idx_properties_tenant_client ON properties(tenant_id, client_id)"),
        ("idx_properties_status", "CREATE INDEX idx_properties_status ON properties(status)"),
        ("idx_jobs_tenant_client", "CREATE INDEX idx_jobs_tenant_client ON jobs(tenant_id, client_id)"),
        ("idx_jobs_tenant_staff", "CREATE INDEX idx_jobs_tenant_staff ON jobs(tenant_id, assigned_staff_id)"),
        ("idx_jobs_status", "CREATE INDEX idx_jobs_status ON jobs(status)"),
        ("idx_jobs_property", "CREATE INDEX idx_jobs_property ON jobs(property_id)"),
        ("idx_appointments_job", "CREATE INDEX idx_appointments_job ON appointments(job_id)"),
        ("idx_appointments_staff", "CREATE INDEX idx_appointments_staff ON appointments(staff_id)"),
        ("idx_appointments_date", "CREATE INDEX idx_appointments_date ON appointments(appointment_date, appointment_time)"),
        ("idx_appointments_status", "CREATE INDEX idx_appointments_status ON appointments(status)"),
        ("idx_job_images_job", "CREATE INDEX idx_job_images_job ON job_images(job_id)"),
        ("idx_job_images_type", "CREATE INDEX idx_job_images_type ON job_images(image_type)"),
        ("idx_payments_job", "CREATE INDEX idx_payments_job ON payments(job_id)"),
        ("idx_payments_stripe_intent", "CREATE INDEX idx_payments_stripe_intent ON payments(stripe_payment_intent_id)"),
        ("idx_payments_status", "CREATE INDEX idx_payments_status ON payments(status)"),
        ("idx_job_activities_job", "CREATE INDEX idx_job_activities_job ON job_activities(job_id)"),
        ("idx_job_activities_created", "CREATE INDEX idx_job_activities_created ON job_activities(created_at DESC)"),
        ("idx_service_packages_tenant", "CREATE INDEX idx_service_packages_tenant ON service_packages(tenant_id, status)"),
    )
    for name, ddl in indexes:
        existing = cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,)).fetchone()
        if not existing:
            cursor.execute(ddl)

