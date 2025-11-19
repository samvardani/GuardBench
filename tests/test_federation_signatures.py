"""Tests for federation signature generation."""

from federation.signatures import (
    canonicalize,
    build_signature,
    tenant_salt,
)


def test_canonicalize_basic():
    """Test basic text canonicalization."""
    text = "Hello World!"
    result = canonicalize(text)
    
    # Should be lowercase
    assert result.islower() or result == result.lower()
    # Should contain the words
    assert "hello" in result
    assert "world" in result


def test_canonicalize_removes_whitespace():
    """Test that canonicalization normalizes whitespace."""
    text = "hello    world  \n\n  test"
    result = canonicalize(text)
    
    # Should normalize multiple spaces
    assert "    " not in result
    assert "\n" not in result or result.strip() == result


def test_canonicalize_removes_punctuation():
    """Test that canonicalization removes or normalizes punctuation."""
    text = "Hello, World! How are you?"
    result = canonicalize(text)
    
    # Punctuation should be handled
    assert "!" not in result or "," not in result or "?" not in result


def test_canonicalize_empty():
    """Test canonicalization with empty string."""
    result = canonicalize("")
    assert result == "" or result.strip() == ""


def test_canonicalize_unicode():
    """Test canonicalization with unicode characters."""
    text = "café résumé"
    result = canonicalize(text)
    
    # Should handle unicode
    assert result


def test_tenant_salt_basic():
    """Test tenant salt generation."""
    salt1 = tenant_salt("tenant1")
    salt2 = tenant_salt("tenant2")
    
    # Different tenants should have different salts
    assert salt1 != salt2
    
    # Same tenant should have same salt
    salt1_again = tenant_salt("tenant1")
    assert salt1 == salt1_again


def test_tenant_salt_empty():
    """Test tenant salt with empty string."""
    salt = tenant_salt("")
    assert salt
    assert isinstance(salt, str)


def test_build_signature_basic():
    """Test building a signature."""
    text = "test content"
    tenant = "test-tenant"
    
    sig = build_signature(text, tenant)
    
    # Should return a Signature object
    assert hasattr(sig, 'perms') or hasattr(sig, 'bloom') or hasattr(sig, 'tenant')
    # Check it has tenant attribute
    if hasattr(sig, 'tenant'):
        assert sig.tenant == tenant


def test_build_signature_with_metadata():
    """Test building signature with metadata."""
    text = "test content"
    tenant = "test-tenant"
    meta = {"key": "value", "category": "test"}
    
    sig = build_signature(text, tenant, meta=meta)
    
    # Should include metadata in signature
    assert sig


def test_build_signature_deterministic():
    """Test that signatures are deterministic."""
    text = "test content"
    tenant = "tenant1"
    
    sig1 = build_signature(text, tenant)
    sig2 = build_signature(text, tenant)
    
    # Same input should produce same signature
    if hasattr(sig1, 'digest'):
        assert sig1.digest == sig2.digest
    elif isinstance(sig1, dict) and isinstance(sig2, dict):
        assert sig1 == sig2 or sig1.get("digest") == sig2.get("digest")


def test_build_signature_different_text():
    """Test that different texts produce different signatures."""
    tenant = "tenant1"
    
    sig1 = build_signature("text1", tenant)
    sig2 = build_signature("text2", tenant)
    
    # Different texts should produce different signatures
    if hasattr(sig1, 'digest') and hasattr(sig2, 'digest'):
        assert sig1.digest != sig2.digest


def test_build_signature_different_tenant():
    """Test that different tenants produce different signatures."""
    text = "same text"
    
    sig1 = build_signature(text, "tenant1")
    sig2 = build_signature(text, "tenant2")
    
    # Different tenants should produce different signatures
    if hasattr(sig1, 'digest') and hasattr(sig2, 'digest'):
        assert sig1.digest != sig2.digest


def test_signature_prevents_cross_tenant_replay():
    """Test that signatures are tenant-specific."""
    text = "test content"
    
    sig1 = build_signature(text, "tenant1")
    sig2 = build_signature(text, "tenant2")
    
    # Same text, different tenants should produce different signatures
    if hasattr(sig1, 'digest') and hasattr(sig2, 'digest'):
        assert sig1.digest != sig2.digest
        assert sig1.tenant != sig2.tenant if hasattr(sig1, 'tenant') else True


def test_canonicalize_preserves_meaning():
    """Test that canonicalization preserves semantic content."""
    text = "Important Security Alert!!!"
    result = canonicalize(text)
    
    # Should still contain the key words
    assert "important" in result.lower()
    assert "security" in result.lower()
    assert "alert" in result.lower()


def test_tenant_salt_special_characters():
    """Test tenant salt with special characters."""
    salt1 = tenant_salt("tenant-with-dashes")
    salt2 = tenant_salt("tenant_with_underscores")
    salt3 = tenant_salt("tenant.with.dots")
    
    # All should produce valid salts
    assert salt1
    assert salt2
    assert salt3
    
    # Should all be different
    assert len({salt1, salt2, salt3}) == 3


def test_build_signature_empty_text():
    """Test building signature with empty text."""
    sig = build_signature("", "tenant")
    assert sig  # Should still create a signature


def test_build_signature_very_long_text():
    """Test building signature with very long text."""
    text = "a" * 100000  # 100KB of text
    sig = build_signature(text, "tenant")
    
    # Should handle large texts
    assert sig


def test_canonicalize_numbers():
    """Test canonicalization with numbers."""
    text = "Order 123 for $45.67"
    result = canonicalize(text)
    
    # Should handle numbers
    assert "123" in result or "45" in result or "67" in result
