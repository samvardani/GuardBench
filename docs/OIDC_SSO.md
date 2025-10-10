# OIDC SSO Integration Guide

Set up Single Sign-On for Safety-Eval-Mini using OpenID Connect (OIDC).

## Overview

The OIDC SSO module provides:
- **Authentication**: Verify user identity via OIDC providers
- **Authorization**: Role-based access control (RBAC) from OIDC groups
- **Audit Trail**: User identity stamping in audit logs
- **Protected Routes**: Secure /ui/* and POST endpoints

## Quick Start

### 1. Install Dependencies

```bash
pip install authlib httpx
```

### 2. Configure OIDC Provider

**Environment Variables**:
```bash
export OIDC_ISSUER="https://your-auth0-domain.auth0.com"
export OIDC_CLIENT_ID="your-client-id"
export OIDC_CLIENT_SECRET="your-client-secret"
export OIDC_AUDIENCE="https://api.your-domain.com"  # Optional
```

### 3. Start Service

```bash
make sso-dev
# or
PYTHONPATH=src uvicorn service.api:app --port 8001
```

### 4. Test Authentication

```bash
# Get token from your OIDC provider
TOKEN="eyJhbGc..."

# Access protected endpoint
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/ui/monitor/
```

## Supported Providers

### Auth0

**Setup**:
1. Create application in Auth0 dashboard
2. Set application type: Machine to Machine
3. Configure allowed callback URLs
4. Enable RBAC in API settings
5. Add custom claims for groups

**Configuration**:
```bash
export OIDC_ISSUER="https://your-tenant.auth0.com"
export OIDC_CLIENT_ID="<your-client-id>"
export OIDC_CLIENT_SECRET="<your-client-secret>"
export OIDC_AUDIENCE="https://api.your-domain.com"
```

**Add Groups to Token** (Auth0 Rule):
```javascript
function(user, context, callback) {
  const namespace = 'https://your-domain.com';
  context.idToken[namespace + '/groups'] = user.app_metadata.groups || [];
  callback(null, user, context);
}
```

### Keycloak

**Setup**:
1. Create realm and client in Keycloak
2. Set access type: confidential
3. Enable service accounts
4. Configure groups and roles
5. Add group membership mapper

**Configuration**:
```bash
export OIDC_ISSUER="https://keycloak.your-domain.com/realms/your-realm"
export OIDC_CLIENT_ID="safety-eval-client"
export OIDC_CLIENT_SECRET="<your-client-secret>"
export OIDC_AUDIENCE="safety-eval-api"
```

**Group Mapper**:
- Mapper Type: Group Membership
- Token Claim Name: groups
- Add to ID token: ON
- Add to access token: ON

### Okta

**Setup**:
1. Create application in Okta
2. Application type: Web
3. Grant type: Authorization Code
4. Add groups claim to token

**Configuration**:
```bash
export OIDC_ISSUER="https://your-domain.okta.com"
export OIDC_CLIENT_ID="<your-client-id>"
export OIDC_CLIENT_SECRET="<your-client-secret>"
export OIDC_AUDIENCE="api://default"
```

## Role Mapping

### Default Mapping

OIDC groups → RBAC roles:

| OIDC Group | RBAC Role | Permissions |
|------------|-----------|-------------|
| `admin`, `admins`, `safety-admin` | admin | Full access |
| `developer`, `developers` | developer | API + UI access |
| `analyst`, `analysts` | analyst | Read + analyze |
| `viewer`, `viewers` | viewer | Read-only |

### Custom Mapping

Configure custom role mapping:

```python
from seval.auth import OIDCAuth

custom_mapping = {
    "org-admins": "admin",
    "ml-engineers": "developer",
    "data-scientists": "analyst",
    "everyone": "viewer",
}

oidc = OIDCAuth(role_mapping=custom_mapping)
```

Or via configuration file:

```yaml
# config.yaml
oidc:
  role_mapping:
    org-admins: admin
    ml-engineers: developer
    data-scientists: analyst
```

## Protected Routes

### Automatically Protected

**UI Routes** (require auth):
- `/ui/*` - All UI endpoints

**API Routes** (require auth):
- `POST /score`
- `POST /score-image`
- `POST /batch-score`

**Public Routes** (no auth):
- `GET /healthz`
- `GET /metrics`
- `GET /docs`
- `GET /openapi.json`

### Adding Protection

**Protect specific endpoint**:
```python
from fastapi import Depends
from seval.auth import require_auth, UserInfo

@app.get("/protected")
async def protected_endpoint(user: UserInfo = Depends(require_auth)):
    return {"user": user.email}
```

**Require specific role**:
```python
from seval.auth import require_role

@app.post("/admin-only")
async def admin_endpoint(user: UserInfo = Depends(require_role("admin"))):
    return {"message": "Admin access granted"}
```

## Token Format

### Required Claims

```json
{
  "iss": "https://auth.example.com",
  "sub": "user-123",
  "aud": "https://api.example.com",
  "exp": 1234567890,
  "iat": 1234567800,
  "email": "user@example.com",
  "name": "Test User",
  "groups": ["developers", "analysts"]
}
```

### Optional Claims

- `preferred_username`: Fallback for `name`
- `groups`: List of group memberships
- Custom claims based on provider configuration

## Audit Logging

### User Identity Stamping

All audit events automatically include user information:

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "action": "guard.score",
  "resource": "candidate-v1",
  "user_id": "user-123",
  "user_email": "user@example.com",
  "tenant_id": "default",
  "context": {
    "category": "violence",
    "language": "en",
    "blocked": false
  }
}
```

### PII Redaction

Sensitive user content is automatically redacted based on privacy mode:

```python
# Full privacy mode
privacy_mode = "full"
# User input not logged, only hash

# Partial privacy mode  
privacy_mode = "partial"
# First/last few characters preserved

# No privacy mode
privacy_mode = "off"
# Full content logged (dev only)
```

## Development Setup

### Local Development (No OIDC)

```bash
# Unset OIDC vars for public access
unset OIDC_ISSUER OIDC_CLIENT_ID OIDC_CLIENT_SECRET

# Start service
make sso-dev
```

### With Mock OIDC

```bash
# Use mock OIDC for testing
export OIDC_ISSUER="https://mock.auth.example.com"
export OIDC_CLIENT_ID="mock-client"
export OIDC_CLIENT_SECRET="mock-secret"
export OIDC_MOCK_MODE="true"

make sso-dev
```

### With Real OIDC (Auth0 Example)

```bash
# Configure Auth0
export OIDC_ISSUER="https://your-tenant.auth0.com"
export OIDC_CLIENT_ID="<from Auth0 dashboard>"
export OIDC_CLIENT_SECRET="<from Auth0 dashboard>"
export OIDC_AUDIENCE="https://api.your-domain.com"

# Start service
make sso-dev

# Get token (using Auth0 CLI or API)
AUTH0_TOKEN=$(curl -X POST https://your-tenant.auth0.com/oauth/token \
  -H 'content-type: application/json' \
  -d '{
    "client_id":"'$OIDC_CLIENT_ID'",
    "client_secret":"'$OIDC_CLIENT_SECRET'",
    "audience":"'$OIDC_AUDIENCE'",
    "grant_type":"client_credentials"
  }' | jq -r '.access_token')

# Use token
curl -H "Authorization: Bearer $AUTH0_TOKEN" \
  http://localhost:8001/ui/monitor/
```

## Testing

### Unit Tests

```bash
# Run OIDC tests
pytest tests/test_oidc*.py -v

# Test role mapping
pytest tests/test_oidc_auth.py::test_oidc_auth_map_groups_to_roles -v

# Test dependencies
pytest tests/test_oidc_dependencies.py -v
```

### Mock OIDC Provider

```python
from unittest.mock import AsyncMock, patch
from seval.auth.oidc import UserInfo

# Mock token verification
mock_user = UserInfo(
    sub="test-user",
    email="test@example.com",
    roles=["developer"]
)

with patch("seval.auth.oidc.OIDCAuth.verify_token", new_callable=AsyncMock) as mock_verify:
    mock_verify.return_value = mock_user
    
    # Make authenticated request
    response = client.post("/score", headers={"Authorization": "Bearer mock-token"})
```

## Troubleshooting

### "OIDC not configured" Warning

**Cause**: Missing environment variables

**Solution**:
```bash
# Check configuration
env | grep OIDC

# Set required vars
export OIDC_ISSUER="..."
export OIDC_CLIENT_ID="..."
export OIDC_CLIENT_SECRET="..."
```

### "Invalid token" Error

**Causes**:
1. Token expired
2. Wrong audience
3. Invalid signature
4. Clock skew

**Solutions**:
```bash
# Check token expiration
echo $TOKEN | cut -d. -f2 | base64 -d | jq .exp

# Verify issuer matches
echo $TOKEN | cut -d. -f2 | base64 -d | jq .iss

# Check audience
echo $TOKEN | cut -d. -f2 | base64 -d | jq .aud
```

### "Insufficient permissions" Error

**Cause**: User doesn't have required role

**Solution**:
1. Check user's groups in OIDC provider
2. Verify role mapping configuration
3. Ensure groups are included in token claims

```bash
# Decode token to check groups
echo $TOKEN | cut -d. -f2 | base64 -d | jq .groups
```

### JWKS Fetch Fails

**Cause**: Cannot reach OIDC provider's JWKS endpoint

**Solution**:
```bash
# Test JWKS endpoint
curl https://your-issuer/.well-known/jwks.json

# Check network/firewall
# Verify issuer URL is correct
```

## Security Best Practices

1. **Use HTTPS**: Always use HTTPS in production
2. **Rotate Secrets**: Rotate client secrets regularly
3. **Short Token Lifetime**: Configure short-lived tokens (< 1 hour)
4. **Validate Audience**: Always set and validate audience claim
5. **Monitor Failed Logins**: Alert on repeated auth failures
6. **Rate Limit**: Add rate limiting for auth endpoints
7. **Log Security Events**: Audit all authentication attempts

## Production Checklist

- [ ] OIDC provider configured (Auth0/Keycloak/Okta)
- [ ] Environment variables set in secure secret store
- [ ] Groups/roles configured in OIDC provider
- [ ] Group claims added to tokens
- [ ] Role mapping verified
- [ ] Test with real users
- [ ] Audit logging verified
- [ ] Error handling tested
- [ ] Monitoring alerts configured
- [ ] Documentation updated for team

## API Reference

### UserInfo

```python
@dataclass
class UserInfo:
    sub: str                    # User ID (subject)
    email: Optional[str]        # Email address
    name: Optional[str]         # Display name
    groups: List[str]           # OIDC groups
    roles: List[str]            # Mapped RBAC roles
```

### Dependencies

```python
# Optional auth (returns None if no token)
user: Optional[UserInfo] = Depends(get_current_user)

# Required auth (raises 401 if no token)
user: UserInfo = Depends(require_auth)

# Require specific role (raises 403 if insufficient)
user: UserInfo = Depends(require_role("admin"))
```

### OIDCAuth Methods

```python
oidc = OIDCAuth()

# Check if configured
oidc.is_configured() -> bool

# Verify token
user_info = await oidc.verify_token(token) -> UserInfo

# Map groups to roles
roles = oidc._map_groups_to_roles(groups) -> List[str]

# Get primary role
primary = oidc.get_primary_role(roles) -> str
```

## Migration Guide

### From No Auth to OIDC

**Step 1**: Deploy without OIDC (backward compatible)
```bash
# No OIDC env vars = public access mode
PYTHONPATH=src uvicorn service.api:app
```

**Step 2**: Enable OIDC (start protecting routes)
```bash
# Set OIDC vars
export OIDC_ISSUER="..."
export OIDC_CLIENT_ID="..."
export OIDC_CLIENT_SECRET="..."

# Restart service
PYTHONPATH=src uvicorn service.api:app
```

**Step 3**: Enforce auth (remove public access fallbacks)
```python
# In code, remove the "not configured" fallback
if not oidc.is_configured():
    raise RuntimeError("OIDC must be configured in production")
```

### Testing Migration

```bash
# Phase 1: No OIDC (baseline)
pytest tests/test_service_api.py -v

# Phase 2: Mock OIDC
OIDC_MOCK_MODE=1 pytest tests/test_oidc*.py -v

# Phase 3: Real OIDC (dev environment)
OIDC_ISSUER=... pytest tests/ -v
```

## Examples

### Protecting Custom Route

```python
from fastapi import Depends
from seval.auth import require_auth, require_role, UserInfo

@app.get("/my-protected-route")
async def my_route(user: UserInfo = Depends(require_auth)):
    return {
        "message": f"Hello {user.name}",
        "email": user.email,
        "roles": user.roles
    }

@app.post("/admin-action")
async def admin_action(user: UserInfo = Depends(require_role("admin"))):
    # Only admins can access
    return {"status": "admin action performed"}
```

### Custom Audit with User

```python
from seval.auth import get_current_user

@app.post("/custom-endpoint")
async def custom_endpoint(
    user: Optional[UserInfo] = Depends(get_current_user)
):
    # Log with user info
    db.create_audit_event(
        tenant_id="default",
        action="custom.action",
        resource="my-resource",
        user_id=user.sub if user else None,
        user_email=user.email if user else None,
        context={"custom": "data"}
    )
```

### Role-Based Logic

```python
@app.get("/dashboard")
async def dashboard(user: UserInfo = Depends(require_auth)):
    # Different data based on role
    if "admin" in user.roles:
        return {"data": "full_admin_view"}
    elif "developer" in user.roles:
        return {"data": "developer_view"}
    else:
        return {"data": "viewer_view"}
```

## Monitoring

### Auth Metrics

Monitor authentication in logs:
```bash
# Failed auth attempts
grep "401" /var/log/safety-eval.log

# Successful auth
grep "Authenticated user" /var/log/safety-eval.log
```

### Prometheus Metrics (Future)

Potential metrics to add:
- `auth_requests_total{result="success|failure"}`
- `auth_latency_seconds`
- `auth_token_verifications_total`

## Advanced Configuration

### Custom JWKS Caching

```python
from seval.auth import OIDCAuth

oidc = OIDCAuth(
    issuer="https://auth.example.com",
    client_id="client123",
    client_secret="secret123",
)

# JWKS is fetched on each token verification
# Consider adding caching for production
```

### Multiple OIDC Providers

For supporting multiple identity providers:

```python
# Configure primary provider via env vars
# Add secondary providers programmatically
providers = {
    "auth0": OIDCAuth(issuer="https://auth0.example.com", ...),
    "keycloak": OIDCAuth(issuer="https://keycloak.example.com", ...),
}

# Route to appropriate provider based on token issuer
```

## Limitations

1. **Single Provider**: Currently supports one OIDC provider
2. **No Token Refresh**: Refresh token flow not implemented
3. **No Session Management**: Stateless (token per request)
4. **Groups Required**: Role mapping requires groups in token
5. **Synchronous Only**: Some operations not async-optimized

## Future Enhancements

- [ ] Token caching/validation cache
- [ ] Refresh token support
- [ ] Session management
- [ ] Multiple provider support
- [ ] OAuth2 password flow
- [ ] JWT signing for outbound tokens
- [ ] Fine-grained permissions (beyond roles)
- [ ] User provisioning hooks

## Support

For issues or questions:
- Check logs: `grep OIDC /var/log/safety-eval.log`
- Enable debug logging: `export LOG_LEVEL=DEBUG`
- Review token claims: Decode JWT at https://jwt.io
- Verify provider configuration in OIDC provider dashboard

