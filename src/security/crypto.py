"""Encryption utilities for sensitive data like OAuth tokens."""

from __future__ import annotations

import base64
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    Fernet = None
    InvalidToken = None
    logger.warning("cryptography not installed - encryption disabled")


class CryptoBox:
    """Encrypts and decrypts sensitive data using Fernet (AES-256-GCM).
    
    Supports key rotation with version prefixes (e.g., "v2:encrypted_data").
    """
    
    def __init__(self, key: Optional[str] = None):
        """Initialize CryptoBox.
        
        Args:
            key: Base64-encoded Fernet key (32 bytes). If None, uses SLACK_TOKEN_KEY env var.
                 Can include version prefix: "v2:BASE64KEY"
        """
        if Fernet is None:
            raise ImportError("cryptography package required for encryption")
        
        # Get key from parameter or environment
        key_str = key or os.getenv("SLACK_TOKEN_KEY", "")
        
        if not key_str:
            # Generate a new key for development
            key_str = Fernet.generate_key().decode()
            logger.warning("No SLACK_TOKEN_KEY set - using generated key (NOT FOR PRODUCTION)")
        
        # Parse key version if present
        if ":" in key_str:
            self.version, key_material = key_str.split(":", 1)
        else:
            self.version = "v1"
            key_material = key_str
        
        # Initialize Fernet cipher
        try:
            self.cipher = Fernet(key_material.encode() if isinstance(key_material, str) else key_material)
        except Exception as e:
            logger.error(f"Invalid encryption key: {e}")
            raise ValueError(f"Invalid encryption key: {e}")
        
        logger.info(f"CryptoBox initialized with key version: {self.version}")
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Encrypted string with version prefix: "v1:encrypted_data"
        """
        if not plaintext:
            return ""
        
        # Encrypt
        encrypted_bytes = self.cipher.encrypt(plaintext.encode())
        encrypted_str = encrypted_bytes.decode()
        
        # Add version prefix
        return f"{self.version}:{encrypted_str}"
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext string.
        
        Args:
            ciphertext: Encrypted string (may have version prefix)
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            InvalidToken: If decryption fails
        """
        if not ciphertext:
            return ""
        
        # Parse version prefix if present
        if ":" in ciphertext and ciphertext.split(":")[0].startswith("v"):
            version, encrypted_data = ciphertext.split(":", 1)
            
            if version != self.version:
                logger.warning(f"Decrypting with key version {self.version}, data version {version}")
        else:
            # No version prefix - assume v1
            encrypted_data = ciphertext
        
        # Decrypt
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_data.encode())
            return decrypted_bytes.decode()
        except InvalidToken as e:
            logger.error("Failed to decrypt token - invalid key or corrupted data")
            raise
    
    def rotate_key(self, old_ciphertext: str, new_key: str) -> str:
        """Rotate encryption key for existing ciphertext.
        
        Args:
            old_ciphertext: Data encrypted with current key
            new_key: New encryption key
            
        Returns:
            Data re-encrypted with new key
        """
        # Decrypt with old key
        plaintext = self.decrypt(old_ciphertext)
        
        # Create new CryptoBox with new key
        new_box = CryptoBox(key=new_key)
        
        # Encrypt with new key
        return new_box.encrypt(plaintext)


# Global CryptoBox instance
_global_crypto_box: Optional[CryptoBox] = None


def get_crypto_box() -> CryptoBox:
    """Get global CryptoBox instance.
    
    Returns:
        CryptoBox instance
    """
    global _global_crypto_box
    
    if _global_crypto_box is None:
        _global_crypto_box = CryptoBox()
    
    return _global_crypto_box


__all__ = ["CryptoBox", "get_crypto_box"]

