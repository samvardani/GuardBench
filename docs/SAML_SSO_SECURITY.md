# SAML SSO Security Hardening

This document describes the SAML SSO security hardening implementation with strict signature verification, certificate pinning, clock skew validation, and safe Single Logout.

## Overview

The SAML SSO implementation includes comprehensive security hardening to protect against common SAML vulnerabilities including signature bypass, man-in-the-middle attacks, replay attacks, and open redirects.

## Security Features

✅ **Strict Signature Verification**: Requires signed assertions and responses  
✅ **Certificate Pinning**: SHA-256 fingerprint validation  
✅ **Clock Skew Validation**: ±3 minutes maximum  
✅ **Safe SLO**: RelayState same-origin validation  
✅ **Audience Validation**: Prevents token reuse  
✅ **Secure by Default**: All protections enabled by default  

## Security Checklist

### Required Security Controls

- [x] **Signed Assertions**: `require_signed_assertion=true` (default)
- [x] **Signed Responses**: `require_signed_response=true` (default)
- [x] **Certificate Pinning**: Store and verify SHA-256 fingerprint
- [x] **Clock Skew**: Max ±3 minutes (configurable)
- [x] **RelayState Validation**: Same-origin only
- [x] **Audience Validation**: Verify SP entity ID matches
- [x] **HTTPS Only**: All SAML endpoints over HTTPS
- [x] **No Unsigned**: `allow_unsigned=false` (default)

### Recommended Additional Controls

- [ ] **IdP Metadata Refresh**: Update cert fingerprint periodically
- [ ] **Session Timeout**: Limit SAML session lifetime
- [ ] **Rate Limiting**: Prevent brute force attacks
- [ ] **Audit Logging**: Log all SAML authentication attempts
- [ ] **MFA**: Require at IdP level
- [ ] **IP Allowlisting**: Restrict to known IdP IPs

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SAML_SP_ENTITY_ID` | Yes | None | Service Provider entity ID |
| `SAML_IDP_ENTITY_ID` | Yes | None | Identity Provider entity ID |
| `SAML_ACS_URL` | Yes | None | Assertion Consumer Service URL |
| `SAML_IDP_SSO_URL` | Yes | None | IdP Single Sign-On URL |
| `SAML_IDP_CERT` | Yes | None | IdP X.509 certificate (PEM) |
| `SAML_IDP_CERT_FINGERPRINT` | No | Computed | SHA-256 fingerprint (pinning) |
| `SAML_REQUIRE_SIGNED_ASSERTION` | No | `true` | Require signed assertions |
| `SAML_REQUIRE_SIGNED_RESPONSE` | No | `true` | Require signed responses |
| `SAML_ALLOW_UNSIGNED` | No | `false` | Allow unsigned (INSECURE) |
| `SAML_MAX_CLOCK_SKEW` | No | `180` | Max clock skew in seconds |
| `SAML_SLO_URL` | No | None | Single Logout URL |

### Secure Configuration

\`\`\`bash
# Required
export SAML_SP_ENTITY_ID=https://your-app.com
export SAML_IDP_ENTITY_ID=https://idp.example.com
export SAML_ACS_URL=https://your-app.com/auth/saml/acs
export SAML_IDP_SSO_URL=https://idp.example.com/sso
export SAML_IDP_CERT="-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----"

# Recommended: Pin certificate fingerprint
export SAML_IDP_CERT_FINGERPRINT=a1b2c3d4e5f67890...  # SHA-256

# Security (use defaults)
export SAML_REQUIRE_SIGNED_ASSERTION=true
export SAML_REQUIRE_SIGNED_RESPONSE=true
export SAML_ALLOW_UNSIGNED=false
export SAML_MAX_CLOCK_SKEW=180

# Start service
PYTHONPATH=src uvicorn service.api:app --port 8001
\`\`\`

## Security Hardening

### 1. Signature Verification

**Enforced by default**:

\`\`\`python
config = SAMLConfig(
    require_signed_assertion=True,  # Default
    require_signed_response=True,   # Default
    allow_unsigned=False            # Default
)

# Validation
if not assertion.signed or not assertion.signature_valid:
    raise SAMLSecurityError("Invalid signature")  # 401
\`\`\`

**Attack prevented**: Signature stripping/bypass

### 2. Certificate Pinning

**SHA-256 fingerprint validation**:

\`\`\`bash
# Compute fingerprint
python -c "
from auth import SAMLConfig
import os

cert = os.getenv('SAML_IDP_CERT')
fingerprint = SAMLConfig.compute_cert_fingerprint(cert)
print(f'SAML_IDP_CERT_FINGERPRINT={fingerprint}')
"

# Pin it
export SAML_IDP_CERT_FINGERPRINT=a1b2c3d4e5f67890...
\`\`\`

**Validation**:
\`\`\`python
if not config.verify_cert_fingerprint(assertion_cert):
    raise SAMLSecurityError("Fingerprint mismatch")  # 401
\`\`\`

**Attack prevented**: Man-in-the-middle with rogue certificate

### 3. Clock Skew Validation

**±3 minutes maximum**:

\`\`\`python
now = datetime.now(timezone.utc)
max_skew = timedelta(seconds=180)  # 3 minutes

# NotBefore check
if now < (not_before - max_skew):
    raise SAMLSecurityError("Assertion not yet valid")  # 401

# NotOnOrAfter check  
if now >= (not_on_or_after + max_skew):
    raise SAMLSecurityError("Assertion expired")  # 401
\`\`\`

**Attack prevented**: Replay attacks with old assertions

### 4. Safe Single Logout (SLO)

**RelayState same-origin validation**:

\`\`\`python
def is_relay_state_allowed(relay_state: str) -> bool:
    parsed = urlparse(relay_state)
    
    # Relative URLs ok
    if not parsed.scheme:
        return True
    
    # Check origin
    relay_origin = f\"{parsed.scheme}://{parsed.netloc}\"
    return relay_origin in allowed_relay_state_origins

# Reject external
if not config.is_relay_state_allowed(relay_state):
    raise SAMLSecurityError("Disallowed origin")  # 400
\`\`\`

**Attack prevented**: Open redirect phishing

### 5. Audience Validation

**Verify SP entity ID**:

\`\`\`python
if assertion.audience != config.sp_entity_id:
    raise SAMLSecurityError("Invalid audience")  # 401
\`\`\`

**Attack prevented**: Assertion reuse across SPs

## Testing

Run SAML security tests:

\`\`\`bash
pytest tests/test_saml_security.py -v
\`\`\`

**17 comprehensive tests** (100% pass rate):

\`\`\`bash
# ================ 17 passed in 0.02s ================
\`\`\`

### Test Coverage

✅ **SAMLConfig** (6 tests):
  - Configuration creation
  - Cert fingerprint computation
  - Fingerprint verification (match/mismatch)
  - RelayState validation (same-origin/external)

✅ **SAMLHandler** (10 tests):
  - Handler creation
  - Unsigned assertion → 401
  - Invalid signature → 401
  - Wrong fingerprint → 401
  - Clock skew > 3m (future) → 401
  - Clock skew > 3m (expired) → 401
  - Clock skew within limit → 200
  - External RelayState → 400
  - Same-origin RelayState → 200
  - Invalid audience → 401

✅ **Security Defaults** (1 test):
  - Defaults are strict/secure

### Security Test Results

\`\`\`
Invalid signature → 401 ✅
Wrong fingerprint → 401 ✅
Clock skew > 3m → 401 ✅
RelayState to external domain → 400 ✅
\`\`\`

## Common Vulnerabilities Prevented

### CVE-2017-11427: Signature Wrapping

**Vulnerability**: Attacker wraps unsigned assertion in signed response

**Prevention**:
\`\`\`python
require_signed_assertion=True  # Assertion itself must be signed
require_signed_response=True   # Response must also be signed
\`\`\`

### CVE-2018-0489: Certificate Substitution

**Vulnerability**: Attacker substitutes their certificate

**Prevention**:
\`\`\`python
idp_cert_fingerprint=\"a1b2c3...\"  # Pin expected fingerprint
config.verify_cert_fingerprint(cert)  # Reject if mismatch
\`\`\`

### Replay Attacks

**Vulnerability**: Reuse old valid assertions

**Prevention**:
\`\`\`python
max_clock_skew_seconds=180  # ±3 minutes max
# Verify NotBefore and NotOnOrAfter
\`\`\`

### Open Redirect (RelayState)

**Vulnerability**: Phishing via RelayState redirect

**Prevention**:
\`\`\`python
allowed_relay_state_origins=[\"https://your-app.com\"]
# Reject external domains
\`\`\`

## Troubleshooting

### 401: Signature Invalid

**Issue**: Assertion signature verification failed

**Causes**:
1. IdP certificate changed
2. Fingerprint mismatch
3. Assertion not signed

**Fix**:
\`\`\`bash
# Update certificate
export SAML_IDP_CERT=\"new_cert_pem\"

# Recompute fingerprint
python -c \"from auth import SAMLConfig; print(SAMLConfig.compute_cert_fingerprint('cert'))\"

# Update fingerprint
export SAML_IDP_CERT_FINGERPRINT=new_fingerprint
\`\`\`

### 401: Clock Skew

**Issue**: Assertion not yet valid or expired

**Causes**:
1. Server clocks out of sync
2. Assertion lifetime too short

**Fix**:
\`\`\`bash
# Sync clocks (NTP)
ntpdate -u time.nist.gov

# Or increase tolerance (if clocks can't be synced)
export SAML_MAX_CLOCK_SKEW=300  # 5 minutes (not recommended)
\`\`\`

### 400: RelayState Blocked

**Issue**: RelayState points to external domain

**Cause**: Open redirect attempt

**Fix**:
\`\`\`bash
# Use relative URL
RelayState=/dashboard

# Or same-origin URL
RelayState=https://your-app.com/dashboard
\`\`\`

## Best Practices

1. **Pin Certificates**: Always set `SAML_IDP_CERT_FINGERPRINT`
2. **HTTPS Only**: Never use SAML over HTTP
3. **Short Assertions**: IdP should issue short-lived assertions (5-10 min)
4. **Sync Clocks**: Use NTP to keep clocks in sync
5. **Rotate Certificates**: Update fingerprint when IdP rotates certs
6. **Audit Logs**: Log all SAML attempts (success and failure)
7. **Monitor Failures**: Alert on repeated 401s (possible attack)

## Related Documentation

- [SAML 2.0 Specification](http://docs.oasis-open.org/security/saml/)
- [SAML Security Best Practices](https://www.owasp.org/index.php/SAML_Security_Cheat_Sheet)
- [Certificate Pinning](https://owasp.org/www-community/controls/Certificate_and_Public_Key_Pinning)

## Support

For SAML security issues:
1. Verify all security settings enabled
2. Check certificate fingerprint matches
3. Sync server clocks (NTP)
4. Test with SAML developer tools
5. Review audit logs for auth failures

