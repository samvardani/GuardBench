"""OIDC SSO authentication module."""

from __future__ import annotations

from .oidc import OIDCAuth, UserInfo, get_oidc_auth
from .dependencies import get_current_user, require_auth, require_role
from .middleware import OIDCMiddleware

__all__ = [
    "OIDCAuth",
    "UserInfo",
    "get_oidc_auth",
    "get_current_user",
    "require_auth",
    "require_role",
    "OIDCMiddleware",
]

