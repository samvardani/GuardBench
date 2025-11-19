"""Notification system for staging platform job status updates."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Email service configuration (can be extended to use SendGrid, etc.)
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
EMAIL_SERVICE_API_KEY = os.getenv("EMAIL_SERVICE_API_KEY", "")

# SMS service configuration (can be extended to use Twilio, etc.)
SMS_ENABLED = os.getenv("SMS_ENABLED", "false").lower() == "true"
SMS_SERVICE_API_KEY = os.getenv("SMS_SERVICE_API_KEY", "")


def send_email_notification(to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
    """
    Send an email notification.
    
    In production, this would integrate with SendGrid, AWS SES, etc.
    For now, just logs the email.
    """
    if not EMAIL_ENABLED:
        logger.info(f"[EMAIL DISABLED] To: {to_email}, Subject: {subject}")
        return True
    
    # TODO: Integrate with actual email service
    logger.info(f"[EMAIL] To: {to_email}, Subject: {subject}, Body: {body[:100]}...")
    return True


def send_sms_notification(to_phone: str, message: str) -> bool:
    """
    Send an SMS notification.
    
    In production, this would integrate with Twilio, etc.
    For now, just logs the SMS.
    """
    if not SMS_ENABLED:
        logger.info(f"[SMS DISABLED] To: {to_phone}, Message: {message[:50]}...")
        return True
    
    # TODO: Integrate with actual SMS service
    logger.info(f"[SMS] To: {to_phone}, Message: {message[:100]}...")
    return True


def notify_job_status_change(
    job: Dict[str, Any],
    old_status: str,
    new_status: str,
    client_email: Optional[str] = None,
    client_phone: Optional[str] = None,
) -> None:
    """Send notification when job status changes."""
    status_messages = {
        "scheduled": "Your staging job has been scheduled.",
        "in_progress": "Your staging job is now in progress.",
        "photos_staged": "Your staged photos are ready for review!",
        "completed": "Your staging job has been completed.",
        "cancelled": "Your staging job has been cancelled.",
    }
    
    message = status_messages.get(new_status, f"Your staging job status has changed to {new_status}.")
    subject = f"Staging Job Update - {new_status.replace('_', ' ').title()}"
    
    if client_email:
        html_body = f"""
        <html>
        <body>
            <h2>Staging Job Update</h2>
            <p>Job ID: {job.get('job_id', 'N/A')}</p>
            <p>Status: {old_status} → {new_status}</p>
            <p>{message}</p>
            <p>You can view your job details in the dashboard.</p>
        </body>
        </html>
        """
        send_email_notification(
            to_email=client_email,
            subject=subject,
            body=message,
            html_body=html_body,
        )
    
    if client_phone:
        send_sms_notification(
            to_phone=client_phone,
            message=f"Staging Job Update: {message} Job ID: {job.get('job_id', 'N/A')[:8]}",
        )


def notify_appointment_reminder(
    appointment: Dict[str, Any],
    client_email: Optional[str] = None,
    client_phone: Optional[str] = None,
) -> None:
    """Send reminder notification for upcoming appointment."""
    date = appointment.get("appointment_date", "")
    time = appointment.get("appointment_time", "")
    
    message = f"Reminder: You have a staging appointment on {date} at {time}."
    subject = "Staging Appointment Reminder"
    
    if client_email:
        html_body = f"""
        <html>
        <body>
            <h2>Appointment Reminder</h2>
            <p>You have a staging appointment scheduled for:</p>
            <p><strong>Date:</strong> {date}</p>
            <p><strong>Time:</strong> {time}</p>
            <p>Please arrive on time. If you need to reschedule, please contact us.</p>
        </body>
        </html>
        """
        send_email_notification(
            to_email=client_email,
            subject=subject,
            body=message,
            html_body=html_body,
        )
    
    if client_phone:
        send_sms_notification(
            to_phone=client_phone,
            message=f"Reminder: Staging appointment on {date} at {time}",
        )


def notify_payment_received(
    payment: Dict[str, Any],
    client_email: Optional[str] = None,
) -> None:
    """Send notification when payment is received."""
    amount = payment.get("amount_cents", 0) / 100
    message = f"Payment of ${amount:.2f} has been received for your staging job."
    subject = "Payment Received"
    
    if client_email:
        html_body = f"""
        <html>
        <body>
            <h2>Payment Received</h2>
            <p>Thank you for your payment!</p>
            <p><strong>Amount:</strong> ${amount:.2f}</p>
            <p>Your staging job will begin processing shortly.</p>
        </body>
        </html>
        """
        send_email_notification(
            to_email=client_email,
            subject=subject,
            body=message,
            html_body=html_body,
        )

