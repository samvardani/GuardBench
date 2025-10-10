"""SAML authentication routes."""

from __future__ import annotations

import logging
import os
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse, Response
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

from .saml import SAMLAuth, SAMLUser, validate_saml_config
from .saml_config import get_saml_config, SAMLConfig
from service import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/saml", tags=["SAML Authentication"])


def _get_request_data(request: Request) -> dict:
    """Extract request data for SAML library.
    
    Args:
        request: FastAPI request
        
    Returns:
        Request data dictionary
    """
    # Parse URL
    url = str(request.url)
    parsed = urlparse(url)
    
    return {
        "http_host": request.client.host if request.client else parsed.netloc,
        "script_name": parsed.path,
        "get_data": dict(request.query_params),
        "post_data": {},  # Will be populated for POST requests
        "server_port": parsed.port or (443 if parsed.scheme == "https" else 80),
        "https": "on" if parsed.scheme == "https" else "off",
    }


def _get_tenant_from_relay_state(relay_state: Optional[str]) -> Optional[str]:
    """Extract tenant ID from relay state.
    
    Args:
        relay_state: Relay state string
        
    Returns:
        Tenant ID or None
    """
    if not relay_state:
        return None
    
    # Relay state format: "tenant:<tenant_id>:redirect:<url>"
    if relay_state.startswith("tenant:"):
        parts = relay_state.split(":", 3)
        if len(parts) >= 2:
            return parts[1]
    
    return None


def _build_relay_state(tenant_id: str, redirect_url: Optional[str] = None) -> str:
    """Build relay state string.
    
    Args:
        tenant_id: Tenant ID
        redirect_url: Optional redirect URL after login
        
    Returns:
        Relay state string
    """
    state = f"tenant:{tenant_id}"
    if redirect_url:
        state += f":redirect:{redirect_url}"
    return state


@router.get("/login/{tenant_id}")
async def saml_login(
    tenant_id: str,
    request: Request,
    redirect_url: Optional[str] = None
):
    """Initiate SAML login for tenant.
    
    Args:
        tenant_id: Tenant ID
        request: FastAPI request
        redirect_url: Optional URL to redirect to after login
        
    Returns:
        Redirect to IdP SSO
    """
    # Get SAML config for tenant
    config = get_saml_config(tenant_id)
    if not config:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"SAML not configured for tenant {tenant_id}"
        )
    
    # Create SAML auth handler
    saml_auth = SAMLAuth(config)
    
    # Build relay state
    relay_state = _build_relay_state(tenant_id, redirect_url)
    
    # Get SSO URL
    request_data = _get_request_data(request)
    try:
        sso_url = saml_auth.get_sso_url(request_data, relay_state=relay_state)
        logger.info(f"Redirecting to IdP SSO for tenant {tenant_id}")
        return RedirectResponse(sso_url)
    except Exception as e:
        logger.exception(f"Error initiating SAML login: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate SAML login: {str(e)}"
        )


@router.post("/acs")
async def saml_acs(
    request: Request,
    SAMLResponse: str = Form(...),
    RelayState: Optional[str] = Form(None)
):
    """Assertion Consumer Service - Process SAML response from IdP.
    
    Args:
        request: FastAPI request
        SAMLResponse: SAML response from IdP
        RelayState: Optional relay state
        
    Returns:
        Redirect to application or error page
    """
    # Extract tenant ID from relay state
    tenant_id = _get_tenant_from_relay_state(RelayState)
    if not tenant_id:
        logger.error("No tenant ID in relay state")
        return HTMLResponse(
            "<h1>SAML Login Failed</h1><p>Invalid relay state</p>",
            status_code=HTTP_400_BAD_REQUEST
        )
    
    # Get SAML config
    config = get_saml_config(tenant_id)
    if not config:
        logger.error(f"No SAML config for tenant {tenant_id}")
        return HTMLResponse(
            f"<h1>SAML Login Failed</h1><p>SAML not configured for tenant {tenant_id}</p>",
            status_code=HTTP_404_NOT_FOUND
        )
    
    # Process SAML response
    request_data = _get_request_data(request)
    request_data["post_data"] = {"SAMLResponse": SAMLResponse}
    if RelayState:
        request_data["post_data"]["RelayState"] = RelayState
    
    saml_auth = SAMLAuth(config)
    success, saml_user, errors = saml_auth.process_saml_response(request_data)
    
    if not success or not saml_user:
        logger.error(f"SAML authentication failed: {errors}")
        error_msg = "<br>".join(errors) if errors else "Unknown error"
        return HTMLResponse(
            f"<h1>SAML Login Failed</h1><p>{error_msg}</p>",
            status_code=HTTP_400_BAD_REQUEST
        )
    
    # Provision or authenticate user
    try:
        user, token = _provision_user(tenant_id, saml_user, config)
        logger.info(f"SAML login successful for {saml_user.email} in tenant {tenant_id}")
        
        # Extract redirect URL from relay state
        redirect_url = "/"
        if RelayState and ":redirect:" in RelayState:
            parts = RelayState.split(":redirect:", 1)
            if len(parts) == 2:
                redirect_url = parts[1]
        
        # Create response with token
        response = RedirectResponse(redirect_url, status_code=302)
        response.set_cookie(
            key="auth_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=86400  # 24 hours
        )
        
        return response
    
    except Exception as e:
        logger.exception(f"Error provisioning user: {e}")
        return HTMLResponse(
            f"<h1>SAML Login Failed</h1><p>Error provisioning user: {str(e)}</p>",
            status_code=HTTP_500_INTERNAL_SERVER_ERROR
        )


def _provision_user(tenant_id: str, saml_user: SAMLUser, config: SAMLConfig) -> tuple[dict, str]:
    """Provision or authenticate user from SAML assertion.
    
    Args:
        tenant_id: Tenant ID
        saml_user: SAML user information
        config: SAML configuration
        
    Returns:
        Tuple of (user_dict, token)
    """
    email = saml_user.email or saml_user.name_id
    
    # Normalize email
    email = email.lower().strip()
    
    # Check if user exists
    existing_user = db.get_user_by_email(tenant_id, email)
    
    if existing_user:
        # User exists, generate token
        user_id = existing_user["user_id"]
        logger.info(f"Existing user {email} logged in via SAML")
    else:
        # Create new user
        display_name = saml_user.display_name or f"{saml_user.first_name or ''} {saml_user.last_name or ''}".strip() or email
        
        # Generate password (won't be used since user logs in via SAML)
        import secrets
        random_password = secrets.token_urlsafe(32)
        
        user = db.create_user(
            tenant_id=tenant_id,
            email=email,
            password=random_password,  # Won't be used
            role=config.default_role,
            status="active"
        )
        
        user_id = user["user_id"]
        logger.info(f"New user {email} provisioned via SAML with role {config.default_role}")
    
    # Generate API token
    token_record = db.create_token(tenant_id, user_id, role=config.default_role)
    token = token_record["token"]
    
    # Get full user record
    user_record = db.get_user_by_email(tenant_id, email)
    
    return user_record, token


@router.get("/metadata/{tenant_id}")
async def saml_metadata(tenant_id: str):
    """Get SP metadata for tenant.
    
    Args:
        tenant_id: Tenant ID
        
    Returns:
        SP metadata XML
    """
    config = get_saml_config(tenant_id)
    if not config:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"SAML not configured for tenant {tenant_id}"
        )
    
    try:
        saml_auth = SAMLAuth(config)
        metadata = saml_auth.get_sp_metadata()
        
        return Response(
            content=metadata,
            media_type="application/xml",
            headers={"Content-Disposition": f'attachment; filename="sp_metadata_{tenant_id}.xml"'}
        )
    except Exception as e:
        logger.exception(f"Error generating SP metadata: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate SP metadata: {str(e)}"
        )


@router.get("/logout/{tenant_id}")
async def saml_logout(
    tenant_id: str,
    request: Request,
    name_id: Optional[str] = None,
    session_index: Optional[str] = None,
    redirect_url: Optional[str] = None
):
    """Initiate SAML Single Logout.
    
    Args:
        tenant_id: Tenant ID
        request: FastAPI request
        name_id: User name ID
        session_index: Session index
        redirect_url: Optional redirect URL
        
    Returns:
        Redirect to IdP SLO or local logout
    """
    config = get_saml_config(tenant_id)
    if not config or not config.idp_slo_url:
        # No SLO configured, just clear local session
        response = RedirectResponse(redirect_url or "/", status_code=302)
        response.delete_cookie("auth_token")
        return response
    
    # Initiate SLO with IdP
    try:
        saml_auth = SAMLAuth(config)
        request_data = _get_request_data(request)
        
        relay_state = _build_relay_state(tenant_id, redirect_url)
        logout_url = saml_auth.get_logout_url(
            request_data,
            name_id=name_id,
            session_index=session_index,
            relay_state=relay_state
        )
        
        if logout_url:
            response = RedirectResponse(logout_url)
            response.delete_cookie("auth_token")
            return response
        else:
            # Fallback to local logout
            response = RedirectResponse(redirect_url or "/", status_code=302)
            response.delete_cookie("auth_token")
            return response
    
    except Exception as e:
        logger.exception(f"Error initiating SLO: {e}")
        # Fallback to local logout
        response = RedirectResponse(redirect_url or "/", status_code=302)
        response.delete_cookie("auth_token")
        return response


@router.get("/sls/{tenant_id}")
@router.post("/sls/{tenant_id}")
async def saml_sls(
    tenant_id: str,
    request: Request,
    SAMLResponse: Optional[str] = Form(None),
    RelayState: Optional[str] = Form(None)
):
    """Single Logout Service - Process SLO response from IdP.
    
    Args:
        tenant_id: Tenant ID
        request: FastAPI request
        SAMLResponse: Optional SAML response
        RelayState: Optional relay state
        
    Returns:
        Redirect to application
    """
    config = get_saml_config(tenant_id)
    if not config:
        return RedirectResponse("/", status_code=302)
    
    # Process SLO response
    request_data = _get_request_data(request)
    if SAMLResponse:
        request_data["post_data"] = {"SAMLResponse": SAMLResponse}
        if RelayState:
            request_data["post_data"]["RelayState"] = RelayState
    
    try:
        saml_auth = SAMLAuth(config)
        success, errors = saml_auth.process_slo_response(request_data)
        
        if not success:
            logger.error(f"SLO processing failed: {errors}")
    
    except Exception as e:
        logger.exception(f"Error processing SLO: {e}")
    
    # Extract redirect URL
    redirect_url = "/"
    if RelayState and ":redirect:" in RelayState:
        parts = RelayState.split(":redirect:", 1)
        if len(parts) == 2:
            redirect_url = parts[1]
    
    # Clear auth cookie
    response = RedirectResponse(redirect_url, status_code=302)
    response.delete_cookie("auth_token")
    
    return response

