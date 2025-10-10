

# SAML 2.0 SSO Integration

This document describes the SAML 2.0 Single Sign-On (SSO) integration for enterprise authentication.

## Overview

The SAML SSO integration allows enterprise clients to authenticate users via their corporate Identity Providers (IdPs) such as Okta, OneLogin, Azure AD, Google Workspace, etc. This eliminates the need for separate user accounts and passwords, providing seamless integration with existing enterprise identity infrastructure.

## Features

- ✅ **SAML 2.0 Compliant**: Full support for SAML 2.0 protocol
- ✅ **Multi-Tenant**: Separate SAML configuration per tenant
- ✅ **Auto-Provisioning**: Automatically create users on first login
- ✅ **Attribute Mapping**: Flexible mapping of SAML attributes to user fields
- ✅ **SP Metadata**: Automatic generation of Service Provider metadata
- ✅ **Single Logout**: Optional SLO support for IdP-initiated logout
- ✅ **Signature Validation**: Verify SAML assertion signatures
- ✅ **Role Mapping**: Configure default roles for SSO users
- ✅ **Session Management**: Secure cookie-based authentication

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│                 │   (1)   │                  │   (3)   │                 │
│   End User      │────────▶│  Service         │────────▶│  Identity       │
│                 │         │  Provider (SP)   │         │  Provider (IdP) │
│                 │◀────────│  (Safety-Eval)   │◀────────│  (Okta/Azure)   │
│                 │   (6)   │                  │   (4)   │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                     │                          
                                     │ (5)                      
                                     ▼                          
                            ┌─────────────────┐                
                            │  User Database  │                
                            └─────────────────┘                

Flow:
1. User clicks "Login via SSO"
2. SP redirects to IdP with SAML AuthnRequest
3. User authenticates at IdP
4. IdP sends SAML Response to SP ACS endpoint
5. SP validates assertion, provisions/authenticates user
6. User is redirected to application with session cookie
```

## Configuration

### Database Schema

The SAML configuration is stored per tenant in the `saml_config` table:

```sql
CREATE TABLE saml_config (
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
    attribute_mapping TEXT,           -- JSON
    default_role TEXT DEFAULT 'viewer',
    enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `sp_entity_id` | Service Provider entity ID (your application) | `https://safety-eval.example.com` |
| `sp_acs_url` | Assertion Consumer Service URL (where IdP sends response) | `https://safety-eval.example.com/auth/saml/acs` |
| `idp_entity_id` | Identity Provider entity ID | `https://idp.okta.com/abc123` |
| `idp_sso_url` | IdP Single Sign-On URL | `https://idp.okta.com/sso/saml2/0oa123` |
| `idp_x509_cert` | IdP public certificate (PEM format, without headers) | `MIICXDCCAcUCAg...` |

### Optional Fields

| Field | Description | Default |
|-------|-------------|---------|
| `sp_sls_url` | Single Logout Service URL | `None` |
| `idp_slo_url` | IdP Single Logout URL | `None` |
| `name_id_format` | SAML NameID format | `emailAddress` |
| `authn_requests_signed` | Sign authentication requests | `False` |
| `want_assertions_signed` | Require signed assertions | `True` |
| `attribute_mapping` | Custom attribute mapping (JSON) | `{}` |
| `default_role` | Default role for new users | `viewer` |
| `enabled` | Enable SAML for this tenant | `True` |

## Setup Guide

### Step 1: Configure Identity Provider

Configure your IdP (Okta, Azure AD, etc.) with a new SAML app:

1. **Create New SAML App** in your IdP
2. **Download SP Metadata** from:
   ```
   GET /auth/saml/metadata/{tenant_id}
   ```
3. **Upload metadata** to your IdP, or manually configure:
   - **Entity ID**: Your SP entity ID (e.g., `https://safety-eval.example.com`)
   - **ACS URL**: `https://safety-eval.example.com/auth/saml/acs`
   - **Name ID Format**: `emailAddress`
4. **Configure Attribute Statements** (optional):
   - `email` → user email address
   - `firstName` → user given name
   - `lastName` → user surname
   - `displayName` → user display name
5. **Download IdP Metadata** or note:
   - IdP Entity ID
   - SSO URL
   - x509 Certificate

### Step 2: Configure Service Provider (Programmatic)

```python
from auth.saml_config import SAMLConfig, set_saml_config

config = SAMLConfig(
    tenant_id="acme-corp",
    sp_entity_id="https://safety-eval.example.com",
    sp_acs_url="https://safety-eval.example.com/auth/saml/acs",
    sp_sls_url="https://safety-eval.example.com/auth/saml/sls/acme-corp",
    idp_entity_id="https://idp.okta.com/abc123",
    idp_sso_url="https://idp.okta.com/sso/saml2/0oa123",
    idp_slo_url="https://idp.okta.com/slo/saml2/0oa123",  # Optional
    idp_x509_cert="MIICXDCCAcUCAg...",  # From IdP metadata
    name_id_format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    authn_requests_signed=False,
    want_assertions_signed=True,
    attribute_mapping={
        "email": "emailAddress",
        "first_name": "givenName",
        "last_name": "surname",
    },
    default_role="viewer",
    enabled=True,
)

set_saml_config(config)
```

### Step 3: Configure Service Provider (Database)

```sql
INSERT INTO saml_config (
    tenant_id,
    sp_entity_id,
    sp_acs_url,
    idp_entity_id,
    idp_sso_url,
    idp_x509_cert,
    default_role,
    enabled
) VALUES (
    'acme-corp',
    'https://safety-eval.example.com',
    'https://safety-eval.example.com/auth/saml/acs',
    'https://idp.okta.com/abc123',
    'https://idp.okta.com/sso/saml2/0oa123',
    'MIICXDCCAcUCAg...',
    'viewer',
    1
);
```

## API Endpoints

### Initiate Login

```
GET /auth/saml/login/{tenant_id}?redirect_url={optional_redirect}
```

Initiates SAML login by redirecting the user to the IdP SSO page.

**Example**:
```
GET /auth/saml/login/acme-corp?redirect_url=/dashboard
```

**Response**: 307 Redirect to IdP

### Assertion Consumer Service (ACS)

```
POST /auth/saml/acs
```

Receives and processes SAML responses from the IdP. This is called automatically by the IdP.

**Form Data**:
- `SAMLResponse`: Base64-encoded SAML assertion
- `RelayState`: State parameter (contains tenant ID and redirect URL)

**Response**:
- **Success**: 302 Redirect with `auth_token` cookie
- **Failure**: 400 with error message

### SP Metadata

```
GET /auth/saml/metadata/{tenant_id}
```

Returns Service Provider metadata XML.

**Example**:
```bash
curl https://safety-eval.example.com/auth/saml/metadata/acme-corp > sp_metadata.xml
```

**Response**: XML metadata document

### Initiate Logout

```
GET /auth/saml/logout/{tenant_id}?name_id={user}&session_index={session}&redirect_url={optional}
```

Initiates Single Logout (if configured).

**Example**:
```
GET /auth/saml/logout/acme-corp?redirect_url=/
```

**Response**: 302 Redirect to IdP SLO or local logout

### Single Logout Service (SLS)

```
GET/POST /auth/saml/sls/{tenant_id}
```

Processes Single Logout responses from the IdP.

## User Provisioning

When a user logs in via SAML for the first time:

1. **Extract Identity**: Name ID and attributes from SAML assertion
2. **Check Existing User**: Query database by email (case-insensitive)
3. **Create User** (if new):
   - Email: From `email` attribute or Name ID
   - Role: From `default_role` config
   - Status: `active`
   - Password: Random (unused, SAML-only login)
4. **Generate Token**: Create API token for user
5. **Set Cookie**: Return session cookie (`auth_token`)

**Attribute Mapping**:

The `attribute_mapping` field defines how SAML attributes map to user fields:

```json
{
  "email": "emailAddress",
  "first_name": "givenName",
  "last_name": "surname",
  "display_name": "displayName"
}
```

If no mapping is provided, standard attribute names are tried:
- Email: `email`, `mail`, `emailAddress`
- First Name: `firstName`, `givenName`
- Last Name: `lastName`, `surname`, `sn`
- Display Name: `displayName`, `cn`

## Security

### Signature Validation

SAML assertions should be signed by the IdP to prevent tampering:

```python
config.want_assertions_signed = True  # Recommended
```

The IdP's x509 certificate is used to verify the signature.

### Certificate Management

- **Rotation**: Update `idp_x509_cert` when IdP certificate changes
- **Format**: PEM format without `-----BEGIN CERTIFICATE-----` headers
- **Storage**: Stored in database (consider encryption for production)

### Session Security

- **HTTPOnly Cookies**: Session tokens set as HTTPOnly
- **Secure Flag**: HTTPS-only cookies in production
- **SameSite**: `lax` to prevent CSRF
- **TTL**: 24-hour default session lifetime

### XML Security

The `python3-saml` library provides protection against:
- XML External Entity (XXE) attacks
- XML signature wrapping attacks
- Replay attacks (via timestamp validation)

## Testing

### Run Tests

```bash
pytest tests/test_saml.py -v
```

**21 comprehensive tests** covering:
- ✅ Configuration management
- ✅ Validation
- ✅ SAML authentication flow
- ✅ User provisioning
- ✅ Attribute mapping
- ✅ API endpoints
- ✅ Error handling

### Manual Testing with Test IdP

Use a test SAML IdP like:
- **SAML Test**: https://samltest.id
- **Mocksaml**: https://mocksaml.com
- **OneLogin**: Free developer account
- **Okta**: Free developer account

**Steps**:

1. **Get SP Metadata**:
   ```bash
   curl http://localhost:8001/auth/saml/metadata/test-tenant > sp_metadata.xml
   ```

2. **Configure Test IdP**:
   - Upload `sp_metadata.xml`
   - Configure attribute statements
   - Note IdP metadata details

3. **Configure Service Provider**:
   ```python
   from auth.saml_config import SAMLConfig, set_saml_config
   
   config = SAMLConfig(
       tenant_id="test-tenant",
       sp_entity_id="http://localhost:8001",
       sp_acs_url="http://localhost:8001/auth/saml/acs",
       idp_entity_id="https://samltest.id/saml/idp",
       idp_sso_url="https://samltest.id/idp/profile/SAML2/Redirect/SSO",
       idp_x509_cert="<cert from samltest.id>",
       default_role="viewer",
       enabled=True,
   )
   set_saml_config(config)
   ```

4. **Test Login**:
   - Visit: `http://localhost:8001/auth/saml/login/test-tenant`
   - Authenticate at IdP
   - Verify redirect back with session cookie

5. **Verify User Creation**:
   ```sql
   SELECT * FROM users WHERE tenant_id = 'test-tenant';
   ```

## Troubleshooting

### SAML Response Errors

**Error**: "Invalid signature"
- **Cause**: IdP certificate mismatch
- **Fix**: Update `idp_x509_cert` with correct certificate from IdP metadata

**Error**: "Invalid audience"
- **Cause**: `sp_entity_id` doesn't match IdP configuration
- **Fix**: Ensure SP entity ID in config matches IdP settings

**Error**: "Replay attack detected"
- **Cause**: SAML assertion replayed
- **Fix**: This is normal security - user must re-authenticate

### Configuration Issues

**Error**: "SAML not configured for tenant"
- **Cause**: No config in database or `enabled = 0`
- **Fix**: Run `set_saml_config()` or check database

**Error**: "Invalid ACS URL"
- **Cause**: URL format invalid
- **Fix**: Ensure full URL with https: `https://example.com/auth/saml/acs`

### User Provisioning Issues

**Error**: User created but wrong email
- **Cause**: Attribute mapping mismatch
- **Fix**: Check IdP attribute statements and update `attribute_mapping`

**Error**: Duplicate user error
- **Cause**: Case-insensitive email match failed
- **Fix**: Database uses `LOWER(email)` - should not happen

## Production Deployment

### HTTPS Required

SAML requires HTTPS in production:

```python
config.sp_acs_url = "https://safety-eval.example.com/auth/saml/acs"
# NOT: http://...
```

### Certificate Signing

For enhanced security, sign SAML requests:

1. Generate SP certificate:
   ```bash
   openssl req -new -x509 -days 3652 -nodes -out sp.crt -keyout sp.key
   ```

2. Configure:
   ```python
   config.authn_requests_signed = True
   # Add sp_x509_cert and sp_private_key to settings
   ```

### Load Balancing

If using multiple servers:
- Session cookies must work across all servers
- Consider sticky sessions or shared session storage
- Ensure all servers can validate SAML responses

### Monitoring

Log SAML events:
```python
import logging
logger = logging.getLogger("auth.saml")
logger.setLevel(logging.INFO)
```

Monitor:
- Login success/failure rates
- SAML response processing time
- Certificate expiration dates
- User provisioning errors

## Multi-Tenant Considerations

### Separate Configurations

Each tenant can have independent SAML configuration:

```python
# Tenant A: Okta
set_saml_config(SAMLConfig(tenant_id="tenant-a", ...))

# Tenant B: Azure AD
set_saml_config(SAMLConfig(tenant_id="tenant-b", ...))
```

### Tenant Identification

The tenant is identified via `RelayState` parameter:
```
RelayState=tenant:acme-corp:redirect:/dashboard
```

### Isolation

- Each tenant's users are isolated in database (`tenant_id` column)
- SAML assertions from Tenant A's IdP cannot authenticate Tenant B users
- Tokens are scoped to tenant

## Migration from Password Auth

To migrate existing users to SAML:

1. **Enable SAML** alongside password auth
2. **Communicate** to users: "Login via SSO now available"
3. **Match by Email**: First SAML login links to existing user
4. **Disable Passwords** (optional): Set `password_hash = NULL` after SAML adoption

Users can continue using passwords until they login via SAML.

## Advanced Configuration

### Custom Attribute Mapping

Map complex SAML attributes:

```python
attribute_mapping = {
    "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
    "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
    "roles": "http://schemas.microsoft.com/ws/2008/06/identity/claims/role",
}
```

### Role Mapping from SAML

To map SAML roles to application roles, extend user provisioning logic:

```python
# In saml_routes.py _provision_user()
saml_roles = saml_user.attributes.get("role", [])
if "admin" in saml_roles:
    role = "admin"
elif "analyst" in saml_roles:
    role = "analyst"
else:
    role = config.default_role
```

### Just-In-Time Provisioning

Current implementation provisions users on first login. To disable auto-provisioning:

1. Modify `_provision_user()` in `saml_routes.py`
2. Check if user exists
3. Return error if not found (instead of creating)

## API Reference

### Python API

```python
from auth.saml_config import SAMLConfig, get_saml_config, set_saml_config
from auth.saml import SAMLAuth, validate_saml_config

# Get configuration
config = get_saml_config("tenant-id")

# Set configuration
set_saml_config(config)

# Validate
is_valid, errors = validate_saml_config(config)

# Initialize auth handler
saml_auth = SAMLAuth(config)

# Get SSO URL
sso_url = saml_auth.get_sso_url(request_data, relay_state="...")

# Process response
success, user, errors = saml_auth.process_saml_response(request_data)

# Get metadata
metadata_xml = saml_auth.get_sp_metadata()
```

## Related Documentation

- [Multi-Tenant Authentication](AUTH.md)
- [OIDC SSO](OIDC_SSO.md) (alternative to SAML)
- [User Management](USER_MANAGEMENT.md)
- [Security Best Practices](SECURITY.md)

## Support

For SAML SSO issues:
- Check IdP documentation (Okta, Azure AD, etc.)
- Review IdP logs for SAML errors
- Enable debug logging: `logging.getLogger("auth.saml").setLevel(logging.DEBUG)`
- Test with SAML tracer browser extension

