"""Tests for OIDC authentication."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from seval.auth.oidc import OIDCAuth, UserInfo


def test_user_info_creation():
    """Test UserInfo creation."""
    user = UserInfo(
        sub="user123",
        email="user@example.com",
        name="Test User",
        groups=["developers"],
        roles=["developer"]
    )
    
    assert user.sub == "user123"
    assert user.email == "user@example.com"
    assert "developer" in user.roles


def test_user_info_to_dict():
    """Test UserInfo to_dict conversion."""
    user = UserInfo(
        sub="user123",
        email="user@example.com",
    )
    
    d = user.to_dict()
    
    assert d["sub"] == "user123"
    assert d["email"] == "user@example.com"
    assert "groups" in d
    assert "roles" in d


def test_oidc_auth_not_configured():
    """Test OIDCAuth when not configured."""
    with patch.dict("os.environ", {}, clear=True):
        oidc = OIDCAuth()
        
        assert not oidc.is_configured()


def test_oidc_auth_configured():
    """Test OIDCAuth when configured."""
    with patch.dict("os.environ", {
        "OIDC_ISSUER": "https://auth.example.com",
        "OIDC_CLIENT_ID": "client123",
        "OIDC_CLIENT_SECRET": "secret123",
    }):
        oidc = OIDCAuth()
        
        assert oidc.is_configured()
        assert oidc.issuer == "https://auth.example.com"
        assert oidc.client_id == "client123"


def test_oidc_auth_map_groups_to_roles():
    """Test group to role mapping."""
    oidc = OIDCAuth()
    
    # Test admin mapping
    roles = oidc._map_groups_to_roles(["admin", "developers"])
    assert "admin" in roles
    assert "developer" in roles
    
    # Test case insensitive
    roles = oidc._map_groups_to_roles(["ADMIN", "Developers"])
    assert "admin" in roles
    assert "developer" in roles


def test_oidc_auth_default_role():
    """Test default role assignment."""
    oidc = OIDCAuth()
    
    # Unknown group should get viewer role
    roles = oidc._map_groups_to_roles(["unknown-group"])
    assert "viewer" in roles


def test_oidc_auth_custom_role_mapping():
    """Test custom role mapping."""
    custom_mapping = {
        "custom-admin": "admin",
        "custom-dev": "developer",
    }
    
    oidc = OIDCAuth(role_mapping=custom_mapping)
    
    roles = oidc._map_groups_to_roles(["custom-admin"])
    assert "admin" in roles


def test_oidc_auth_get_primary_role():
    """Test getting primary role."""
    oidc = OIDCAuth()
    
    # Admin is highest
    assert oidc.get_primary_role(["admin", "developer", "viewer"]) == "admin"
    
    # Developer over viewer
    assert oidc.get_primary_role(["developer", "viewer"]) == "developer"
    
    # Default to viewer
    assert oidc.get_primary_role([]) == "viewer"


@pytest.mark.asyncio
async def test_oidc_verify_token_not_configured():
    """Test token verification when not configured."""
    oidc = OIDCAuth()
    
    with pytest.raises(ValueError, match="not configured"):
        await oidc.verify_token("fake-token")


@pytest.mark.asyncio
async def test_oidc_verify_token_mock():
    """Test token verification with mock."""
    with patch.dict("os.environ", {
        "OIDC_ISSUER": "https://auth.example.com",
        "OIDC_CLIENT_ID": "client123",
        "OIDC_CLIENT_SECRET": "secret123",
    }):
        oidc = OIDCAuth()
        
        # Mock JWT decode
        mock_claims = {
            "sub": "user123",
            "email": "user@example.com",
            "name": "Test User",
            "groups": ["developers"],
        }
        
        with patch("seval.auth.oidc.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"keys": []}
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            with patch("seval.auth.oidc.jwt.decode", return_value=mock_claims):
                user_info = await oidc.verify_token("valid-token")
                
                assert user_info.sub == "user123"
                assert user_info.email == "user@example.com"
                assert "developer" in user_info.roles


def test_oidc_global_instance():
    """Test global OIDC instance is singleton."""
    from seval.auth.oidc import get_oidc_auth
    
    oidc1 = get_oidc_auth()
    oidc2 = get_oidc_auth()
    
    assert oidc1 is oidc2


def test_role_mapping_multiple_groups():
    """Test role mapping with multiple groups."""
    oidc = OIDCAuth()
    
    groups = ["admin", "developers", "analysts"]
    roles = oidc._map_groups_to_roles(groups)
    
    # Should map all groups
    assert "admin" in roles
    assert "developer" in roles
    assert "analyst" in roles
    
    # No duplicates
    assert len(roles) == len(set(roles))


def test_role_mapping_preserves_order():
    """Test role mapping doesn't duplicate roles."""
    oidc = OIDCAuth()
    
    # Same group appears twice
    groups = ["admin", "admins", "admin"]
    roles = oidc._map_groups_to_roles(groups)
    
    # Should only have one admin role
    assert roles.count("admin") == 1

