"""Authentication module with SAML SSO support."""

from __future__ import annotations

from .saml import SAMLHandler, SAMLSecurityError
from .saml_config import SAMLConfig, get_saml_config

__all__ = [
    "SAMLHandler",
    "SAMLSecurityError",
    "SAMLConfig",
    "get_saml_config",
]

