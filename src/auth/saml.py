"""SAML 2.0 authentication module."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from .saml_config import SAMLConfig

logger = logging.getLogger(__name__)


@dataclass
class SAMLUser:
    """User information extracted from SAML assertion."""
    
    name_id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    session_index: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name_id": self.name_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "attributes": self.attributes or {},
            "session_index": self.session_index,
        }


class SAMLAuth:
    """SAML 2.0 authentication handler."""
    
    def __init__(self, config: SAMLConfig):
        """Initialize SAML auth handler.
        
        Args:
            config: SAML configuration
        """
        self.config = config
        self.settings = config.to_saml_settings()
    
    def prepare_request_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare request data for python3-saml.
        
        Args:
            request_data: Raw request data with keys: http_host, script_name, 
                         get_data, post_data, server_port, https
        
        Returns:
            Prepared request data
        """
        return {
            "http_host": request_data.get("http_host", ""),
            "script_name": request_data.get("script_name", ""),
            "get_data": request_data.get("get_data", {}),
            "post_data": request_data.get("post_data", {}),
            "server_port": request_data.get("server_port", 443),
            "https": request_data.get("https", "on"),
        }
    
    def get_sso_url(self, request_data: Dict[str, Any], relay_state: Optional[str] = None) -> str:
        """Get SSO login URL.
        
        Args:
            request_data: Request data
            relay_state: Optional relay state for redirect after login
            
        Returns:
            SSO URL to redirect user to
        """
        req = self.prepare_request_data(request_data)
        auth = OneLogin_Saml2_Auth(req, self.settings)
        
        return auth.login(return_to=relay_state)
    
    def process_saml_response(
        self,
        request_data: Dict[str, Any]
    ) -> tuple[bool, SAMLUser | None, list[str]]:
        """Process SAML response from IdP.
        
        Args:
            request_data: Request data containing SAMLResponse
            
        Returns:
            Tuple of (success, SAMLUser or None, error_list)
        """
        req = self.prepare_request_data(request_data)
        auth = OneLogin_Saml2_Auth(req, self.settings)
        
        try:
            # Process the response
            auth.process_response()
            
            errors = auth.get_errors()
            if errors:
                logger.error(f"SAML response errors: {errors}")
                return False, None, errors
            
            if not auth.is_authenticated():
                logger.warning("SAML authentication failed: user not authenticated")
                return False, None, ["Authentication failed"]
            
            # Extract user information
            name_id = auth.get_nameid()
            attributes = auth.get_attributes()
            session_index = auth.get_session_index()
            
            # Apply attribute mapping
            email = self._extract_attribute(attributes, "email", ["email", "mail", "emailAddress"])
            first_name = self._extract_attribute(attributes, "first_name", ["firstName", "givenName"])
            last_name = self._extract_attribute(attributes, "last_name", ["lastName", "surname", "sn"])
            display_name = self._extract_attribute(attributes, "display_name", ["displayName", "cn"])
            
            # If email not in attributes, try name_id if it looks like an email
            if not email and "@" in name_id:
                email = name_id
            
            saml_user = SAMLUser(
                name_id=name_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                display_name=display_name,
                attributes=attributes,
                session_index=session_index,
            )
            
            logger.info(f"SAML authentication successful for user: {email or name_id}")
            return True, saml_user, []
        
        except Exception as e:
            logger.exception(f"Error processing SAML response: {e}")
            return False, None, [str(e)]
    
    def _extract_attribute(
        self,
        attributes: Dict[str, list],
        key: str,
        possible_keys: list[str]
    ) -> Optional[str]:
        """Extract attribute from SAML attributes using multiple possible keys.
        
        Args:
            attributes: SAML attributes dictionary
            key: Primary key to look for in attribute_mapping
            possible_keys: List of possible attribute names
            
        Returns:
            Attribute value or None
        """
        # Check custom mapping first
        if self.config.attribute_mapping and key in self.config.attribute_mapping:
            mapped_key = self.config.attribute_mapping[key]
            if mapped_key in attributes and attributes[mapped_key]:
                return attributes[mapped_key][0]
        
        # Try standard keys
        for attr_key in possible_keys:
            if attr_key in attributes and attributes[attr_key]:
                return attributes[attr_key][0]
        
        return None
    
    def get_sp_metadata(self) -> str:
        """Get SP metadata XML.
        
        Returns:
            SP metadata as XML string
        """
        settings = OneLogin_Saml2_Settings(self.settings)
        metadata = settings.get_sp_metadata()
        errors = settings.validate_metadata(metadata)
        
        if errors:
            logger.error(f"SP metadata validation errors: {errors}")
            raise ValueError(f"Invalid SP metadata: {errors}")
        
        return metadata
    
    def get_logout_url(
        self,
        request_data: Dict[str, Any],
        name_id: Optional[str] = None,
        session_index: Optional[str] = None,
        relay_state: Optional[str] = None
    ) -> Optional[str]:
        """Get Single Logout URL.
        
        Args:
            request_data: Request data
            name_id: User name ID
            session_index: Session index from login
            relay_state: Optional relay state
            
        Returns:
            Logout URL or None if SLO not configured
        """
        if not self.config.idp_slo_url:
            return None
        
        req = self.prepare_request_data(request_data)
        auth = OneLogin_Saml2_Auth(req, self.settings)
        
        return auth.logout(
            name_id=name_id,
            session_index=session_index,
            return_to=relay_state
        )
    
    def process_slo_response(self, request_data: Dict[str, Any]) -> tuple[bool, list[str]]:
        """Process Single Logout response.
        
        Args:
            request_data: Request data containing SAMLResponse or LogoutRequest
            
        Returns:
            Tuple of (success, error_list)
        """
        req = self.prepare_request_data(request_data)
        auth = OneLogin_Saml2_Auth(req, self.settings)
        
        try:
            # Process SLO
            url = auth.process_slo(delete_session_cb=lambda: None)
            errors = auth.get_errors()
            
            if errors:
                logger.error(f"SLO errors: {errors}")
                return False, errors
            
            return True, []
        
        except Exception as e:
            logger.exception(f"Error processing SLO: {e}")
            return False, [str(e)]


def validate_saml_config(config: SAMLConfig) -> tuple[bool, list[str]]:
    """Validate SAML configuration.
    
    Args:
        config: SAML configuration
        
    Returns:
        Tuple of (is_valid, error_list)
    """
    errors = []
    
    # Validate required fields
    if not config.sp_entity_id:
        errors.append("SP entity ID is required")
    
    if not config.sp_acs_url:
        errors.append("SP ACS URL is required")
    else:
        # Validate URL format
        try:
            parsed = urlparse(config.sp_acs_url)
            if not parsed.scheme or not parsed.netloc:
                errors.append("SP ACS URL must be a valid URL")
        except Exception:
            errors.append("SP ACS URL is invalid")
    
    if not config.idp_entity_id:
        errors.append("IdP entity ID is required")
    
    if not config.idp_sso_url:
        errors.append("IdP SSO URL is required")
    
    if not config.idp_x509_cert:
        errors.append("IdP x509 certificate is required")
    else:
        # Basic certificate format validation
        cert = config.idp_x509_cert.strip()
        if not cert or len(cert) < 100:
            errors.append("IdP x509 certificate appears invalid")
    
    # Try to create settings
    if not errors:
        try:
            settings = config.to_saml_settings()
            OneLogin_Saml2_Settings(settings)
        except Exception as e:
            errors.append(f"Invalid SAML settings: {str(e)}")
    
    return len(errors) == 0, errors

