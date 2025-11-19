"""Stripe payment integration for staging platform."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from service.api import AuthContext, require_auth, require_any_role
from service.staging_db import (
    create_payment,
    get_job,
    get_payment,
    get_payment_by_stripe_session,
    get_service_packages,
    update_job,
    update_payment,
)
from service.staging_models import CheckoutRequest, PaymentResponse

router = APIRouter(prefix="/api/staging", tags=["staging"])

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Base URL for redirects
BASE_URL = os.getenv("BASE_URL", "http://localhost:8001")


@router.post("/jobs/{job_id}/checkout")
def create_checkout_session(
    job_id: str,
    payload: CheckoutRequest,
    ctx: AuthContext = Depends(require_any_role("client", "admin", "manager", "owner")),
) -> Dict[str, Any]:
    """
    Create a Stripe Checkout Session for a job.
    
    Returns a checkout session URL that the client can redirect to.
    """
    if not stripe.api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment processing not configured")
    
    # Verify job exists and belongs to client
    job = get_job(job_id, ctx.tenant_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    if ctx.role == "client" and job.get("client_id") != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Check if payment already exists (simple check - in production would query by job_id)
    # For now, we'll allow multiple payments but mark job as paid after first success
    
    # Get package price if package_id is set
    amount_cents = 0
    line_items = []
    
    if job.get("package_id"):
        packages = get_service_packages(ctx.tenant_id, status="active")
        package = next((p for p in packages if p["package_id"] == job["package_id"]), None)
        if not package:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Package not found")
        amount_cents = package["price_cents"]
        line_items.append({
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": package["name"],
                    "description": package.get("description", ""),
                },
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        })
    else:
        # Default pricing if no package
        amount_cents = 5000  # $50.00 default
        line_items.append({
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": "Virtual Staging Service",
                    "description": "Virtual staging of property photos",
                },
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        })
    
    if amount_cents == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid pricing")
    
    try:
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url=payload.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=payload.cancel_url,
            client_reference_id=job_id,
            metadata={
                "job_id": job_id,
                "tenant_id": ctx.tenant_id,
                "client_id": job.get("client_id", ""),
            },
        )
        
        # Create payment record
        payment = create_payment(
            tenant_id=ctx.tenant_id,
            job_id=job_id,
            client_id=job.get("client_id", ""),
            amount_cents=amount_cents,
            stripe_checkout_session_id=checkout_session.id,
            status="pending",
        )
        
        return {
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id,
            "payment_id": payment["payment_id"],
        }
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Stripe error: {str(e)}")


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment_endpoint(
    payment_id: str,
    ctx: AuthContext = Depends(require_auth),
) -> Dict[str, Any]:
    """Get payment details."""
    payment = get_payment(payment_id, ctx.tenant_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    
    # Role-based access
    if ctx.role == "client" and payment.get("client_id") != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    return payment


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
) -> Dict[str, Any]:
    """
    Handle Stripe webhook events.
    
    This endpoint should be configured in Stripe dashboard to receive webhook events.
    Note: This endpoint should NOT require authentication (Stripe signs the requests).
    """
    # Get the raw request body
    body = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Webhook secret not configured")
    
    try:
        event = stripe.Webhook.construct_event(body, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid payload: {str(e)}")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid signature: {str(e)}")
    
    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session["id"]
        
        # Find payment by session ID
        payment = get_payment_by_stripe_session(session_id, session["metadata"].get("tenant_id", ""))
        if payment:
            # Update payment status
            update_payment(
                payment["payment_id"],
                payment["tenant_id"],
                {
                    "status": "succeeded",
                    "stripe_payment_intent_id": session.get("payment_intent"),
                    "payment_method": "card",
                },
            )
            
            # Update job status to confirmed
            job_id = payment["job_id"]
            job = get_job(job_id, payment["tenant_id"])
            if job and job.get("status") == "scheduled":
                update_job(job_id, payment["tenant_id"], {"status": "in_progress"})
            
            # Send payment notification
            try:
                notify_payment_received(payment)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to send payment notification: {e}")
    
    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        # Find payment by payment intent ID (would need to store this)
        # For now, we'll handle this in the checkout session completion
    
    return {"status": "success"}


@router.post("/payments/{payment_id}/refund")
def refund_payment(
    payment_id: str,
    amount_cents: Optional[int] = None,
    ctx: AuthContext = Depends(require_any_role("admin", "manager", "owner")),
) -> Dict[str, Any]:
    """Refund a payment (admin only)."""
    payment = get_payment(payment_id, ctx.tenant_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    
    if payment.get("status") != "succeeded":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment must be succeeded to refund")
    
    if not payment.get("stripe_payment_intent_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment intent not found")
    
    try:
        # Create refund in Stripe
        refund_amount = amount_cents or payment["amount_cents"]
        refund = stripe.Refund.create(
            payment_intent=payment["stripe_payment_intent_id"],
            amount=refund_amount,
        )
        
        # Update payment record
        update_payment(
            payment_id,
            ctx.tenant_id,
            {
                "status": "refunded",
                "refund_amount_cents": refund_amount,
            },
        )
        
        return {
            "refund_id": refund.id,
            "amount_cents": refund_amount,
            "status": "refunded",
        }
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Stripe error: {str(e)}")

