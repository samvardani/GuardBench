"""SAML configuration management."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class SAMLConfig:
    """SAML configuration for a tenant."""
    
    tenant_id: str
    sp_entity_id: str
    sp_acs_url: str
    sp_sls_url: Optional[str]
    idp_entity_id: str
    idp_sso_url: str
    idp_slo_url: Optional[str]
    idp_x509_cert: str
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    authn_requests_signed: bool = False
    want_assertions_signed: bool = True
    attribute_mapping: Optional[Dict[str, str]] = None
    default_role: str = "viewer"
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tenant_id": self.tenant_id,
            "sp_entity_id": self.sp_entity_id,
            "sp_acs_url": self.sp_acs_url,
            "sp_sls_url": self.sp_sls_url,
            "idp_entity_id": self.idp_entity_id,
            "idp_sso_url": self.idp_sso_url,
            "idp_slo_url": self.idp_slo_url,
            "idp_x509_cert": self.idp_x509_cert,
            "name_id_format": self.name_id_format,
            "authn_requests_signed": self.authn_requests_signed,
            "want_assertions_signed": self.want_assertions_signed,
            "attribute_mapping": self.attribute_mapping or {},
            "default_role": self.default_role,
            "enabled": self.enabled,
        }
    
    def to_saml_settings(self) -> Dict[str, Any]:
        """Convert to python3-saml settings format."""
        settings = {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": self.sp_entity_id,
                "assertionConsumerService": {
                    "url": self.sp_acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                },
                "NameIDFormat": self.name_id_format,
            },
            "idp": {
                "entityId": self.idp_entity_id,
                "singleSignOnService": {
                    "url": self.idp_sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "x509cert": self.idp_x509_cert,
            },
            "security": {
                "nameIdEncrypted": False,
                "authnRequestsSigned": self.authn_requests_signed,
                "logoutRequestSigned": False,
                "logoutResponseSigned": False,
                "signMetadata": False,
                "wantMessagesSigned": False,
                "wantAssertionsSigned": self.want_assertions_signed,
                "wantAssertionsEncrypted": False,
                "wantNameIdEncrypted": False,
                "requestedAuthnContext": True,
                "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
            }
        }
        
        # Add SLO endpoints if configured
        if self.sp_sls_url:
            settings["sp"]["singleLogoutService"] = {
                "url": self.sp_sls_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            }
        
        if self.idp_slo_url:
            settings["idp"]["singleLogoutService"] = {
                "url": self.idp_slo_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            }
        
        return settings


def init_saml_config_table(conn: sqlite3.Connection) -> None:
    """Initialize SAML configuration table.
    
    Args:
        conn: Database connection
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS saml_config (
            tenant_id TEXT PRIMARY KEY,
            sp_entity_id TEXT NOT NULL,
            sp_acs_url TEXT NOT NULL,
            sp_sls_url TEXT,
            idp_entity_id TEXT NOT NULL,
            idp_sso_url TEXT NOT NULL,
            idp_slo_url TEXT,
            idp_x509_cert TEXT NOT NULL,
            name_id_format TEXT DEFAULT 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
            authn_requests_signed INTEGER DEFAULT 0,
            want_assertions_signed INTEGER DEFAULT 1,
            attribute_mapping TEXT,
            default_role TEXT DEFAULT 'viewer',
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
        )
    """)
    
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_saml_config_enabled 
        ON saml_config(tenant_id, enabled)
    """)
    
    conn.commit()
    logger.info("SAML configuration table initialized")


def get_saml_config(tenant_id: str, db_path: Path = Path("history.db")) -> Optional[SAMLConfig]:
    """Get SAML configuration for tenant.
    
    Args:
        tenant_id: Tenant ID
        db_path: Database path
        
    Returns:
        SAMLConfig or None
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM saml_config WHERE tenant_id = ? AND enabled = 1",
            (tenant_id,)
        )
        row = cur.fetchone()
        
        if not row:
            return None
        
        import json
        attribute_mapping = json.loads(row["attribute_mapping"]) if row["attribute_mapping"] else None
        
        return SAMLConfig(
            tenant_id=row["tenant_id"],
            sp_entity_id=row["sp_entity_id"],
            sp_acs_url=row["sp_acs_url"],
            sp_sls_url=row["sp_sls_url"],
            idp_entity_id=row["idp_entity_id"],
            idp_sso_url=row["idp_sso_url"],
            idp_slo_url=row["idp_slo_url"],
            idp_x509_cert=row["idp_x509_cert"],
            name_id_format=row["name_id_format"],
            authn_requests_signed=bool(row["authn_requests_signed"]),
            want_assertions_signed=bool(row["want_assertions_signed"]),
            attribute_mapping=attribute_mapping,
            default_role=row["default_role"],
            enabled=bool(row["enabled"]),
        )
    
    finally:
        conn.close()


def set_saml_config(config: SAMLConfig, db_path: Path = Path("history.db")) -> None:
    """Set SAML configuration for tenant.
    
    Args:
        config: SAML configuration
        db_path: Database path
    """
    conn = sqlite3.connect(db_path)
    
    try:
        import json
        attribute_mapping_json = json.dumps(config.attribute_mapping) if config.attribute_mapping else None
        
        conn.execute("""
            INSERT INTO saml_config (
                tenant_id, sp_entity_id, sp_acs_url, sp_sls_url,
                idp_entity_id, idp_sso_url, idp_slo_url, idp_x509_cert,
                name_id_format, authn_requests_signed, want_assertions_signed,
                attribute_mapping, default_role, enabled, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(tenant_id) DO UPDATE SET
                sp_entity_id = excluded.sp_entity_id,
                sp_acs_url = excluded.sp_acs_url,
                sp_sls_url = excluded.sp_sls_url,
                idp_entity_id = excluded.idp_entity_id,
                idp_sso_url = excluded.idp_sso_url,
                idp_slo_url = excluded.idp_slo_url,
                idp_x509_cert = excluded.idp_x509_cert,
                name_id_format = excluded.name_id_format,
                authn_requests_signed = excluded.authn_requests_signed,
                want_assertions_signed = excluded.want_assertions_signed,
                attribute_mapping = excluded.attribute_mapping,
                default_role = excluded.default_role,
                enabled = excluded.enabled,
                updated_at = CURRENT_TIMESTAMP
        """, (
            config.tenant_id,
            config.sp_entity_id,
            config.sp_acs_url,
            config.sp_sls_url,
            config.idp_entity_id,
            config.idp_sso_url,
            config.idp_slo_url,
            config.idp_x509_cert,
            config.name_id_format,
            int(config.authn_requests_signed),
            int(config.want_assertions_signed),
            attribute_mapping_json,
            config.default_role,
            int(config.enabled),
        ))
        
        conn.commit()
        logger.info(f"SAML configuration saved for tenant {config.tenant_id}")
    
    finally:
        conn.close()


def delete_saml_config(tenant_id: str, db_path: Path = Path("history.db")) -> None:
    """Delete SAML configuration for tenant.
    
    Args:
        tenant_id: Tenant ID
        db_path: Database path
    """
    conn = sqlite3.connect(db_path)
    
    try:
        conn.execute("DELETE FROM saml_config WHERE tenant_id = ?", (tenant_id,))
        conn.commit()
        logger.info(f"SAML configuration deleted for tenant {tenant_id}")
    
    finally:
        conn.close()

