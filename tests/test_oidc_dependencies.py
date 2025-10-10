"""Tests for OIDC FastAPI dependencies."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from seval.auth.dependencies import get_current_user, require_auth, require_role
from seval.auth.oidc import UserInfo


@pytest.mark.asyncio
async def test_get_current_user_no_header():
    """Test get_current_user without authorization header."""
    user = await get_current_user(authorization=None)
    
    # Should return None when no header
    assert user is None


@pytest.mark.asyncio
async def test_get_current_user_not_configured():
    """Test get_current_user when OIDC not configured."""
    with patch.dict("os.environ", {}, clear=True):
        from seval.auth.oidc import OIDCAuth
        
        # Reset global instance
        import seval.auth.oidc as oidc_module
        oidc_module._global_oidc_auth = None
        
        user = await get_current_user(authorization="Bearer token")
        
        # Should return None when not configured
        assert user is None


@pytest.mark.asyncio
async def test_get_current_user_invalid_format():
    """Test get_current_user with invalid header format."""
    with patch("seval.auth.dependencies.get_oidc_auth") as mock_oidc:
        mock_oidc.return_value.is_configured.return_value = True
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="InvalidFormat token")
        
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    """Test get_current_user with valid token."""
    mock_user = UserInfo(
        sub="user123",
        email="user@example.com",
        roles=["viewer"]
    )
    
    with patch("seval.auth.dependencies.get_oidc_auth") as mock_oidc:
        mock_oidc.return_value.is_configured.return_value = True
        mock_oidc.return_value.verify_token = AsyncMock(return_value=mock_user)
        
        user = await get_current_user(authorization="Bearer valid-token")
        
        assert user is not None
        assert user.sub == "user123"


@pytest.mark.asyncio
async def test_require_auth_no_token():
    """Test require_auth without token."""
    with patch("seval.auth.dependencies.get_oidc_auth") as mock_oidc:
        mock_oidc.return_value.is_configured.return_value = True
        
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(authorization=None)
        
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_auth_not_configured():
    """Test require_auth when OIDC not configured (public mode)."""
    with patch("seval.auth.dependencies.get_oidc_auth") as mock_oidc:
        mock_oidc.return_value.is_configured.return_value = False
        
        user = await require_auth(authorization=None)
        
        # Should return public user
        assert user.sub == "public"
        assert "viewer" in user.roles


@pytest.mark.asyncio
async def test_require_role_admin():
    """Test require_role for admin role."""
    admin_user = UserInfo(
        sub="admin123",
        roles=["admin"]
    )
    
    checker = require_role("admin")
    result = await checker(admin_user)
    
    assert result.sub == "admin123"


@pytest.mark.asyncio
async def test_require_role_insufficient():
    """Test require_role with insufficient permissions."""
    viewer_user = UserInfo(
        sub="viewer123",
        roles=["viewer"]
    )
    
    checker = require_role("admin")
    
    with pytest.raises(HTTPException) as exc_info:
        await checker(viewer_user)
    
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_role_hierarchy():
    """Test role hierarchy (admin can access developer routes)."""
    admin_user = UserInfo(
        sub="admin123",
        roles=["admin"]
    )
    
    # Admin should pass developer check
    checker = require_role("developer")
    result = await checker(admin_user)
    
    assert result.sub == "admin123"


@pytest.mark.asyncio
async def test_require_role_multiple_roles():
    """Test user with multiple roles."""
    user = UserInfo(
        sub="user123",
        roles=["developer", "analyst", "viewer"]
    )
    
    # Should pass analyst check (user has analyst role)
    checker = require_role("analyst")
    result = await checker(user)
    
    assert result.sub == "user123"

