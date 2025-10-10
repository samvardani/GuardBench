# SAML SSO - Quick Start

Get enterprise SSO running in 10 minutes.

## Prerequisites

- Safety-Eval-Mini service running
- Access to your Identity Provider (IdP) admin console
- Database access

## Step 1: Install Dependencies

```bash
pip install python3-saml
```

Already included in `requirements.txt`.

## Step 2: Get SP Metadata

Start the service and download SP metadata:

```bash
curl http://localhost:8001/auth/saml/metadata/YOUR_TENANT_ID > sp_metadata.xml
```

Example:
```bash
curl http://localhost:8001/auth/saml/metadata/acme-corp > sp_metadata.xml
```

## Step 3: Configure Your IdP

### Okta

1. Go to **Applications** → **Create App Integration**
2. Select **SAML 2.0**
3. Upload `sp_metadata.xml` OR manually enter:
   - **Single sign on URL**: `http://localhost:8001/auth/saml/acs`
   - **Audience URI**: `http://localhost:8001`
   - **Name ID format**: `EmailAddress`
4. **Attribute Statements** (optional):
   - `email` → `user.email`
   - `firstName` → `user.firstName`
   - `lastName` → `user.lastName`
5. Assign users to the app
6. Go to **Sign On** tab → **View Setup Instructions**
7. Note down:
   - **Identity Provider Single Sign-On URL**
   - **Identity Provider Issuer**
   - **X.509 Certificate**

### Azure AD

1. Go to **Azure Active Directory** → **Enterprise Applications**
2. Click **New application** → **Create your own application**
3. Enter name, select **Integrate any other application**
4. Go to **Single sign-on** → **SAML**
5. Upload `sp_metadata.xml` OR manually enter:
   - **Identifier (Entity ID)**: `http://localhost:8001`
   - **Reply URL (ACS)**: `http://localhost:8001/auth/saml/acs`
6. **Attributes & Claims**:
   - `email` → `user.mail`
   - `firstName` → `user.givenname`
   - `lastName` → `user.surname`
7. Download **Federation Metadata XML**
8. Extract from XML:
   - `entityID` attribute → IdP Entity ID
   - `Location` in `SingleSignOnService` → SSO URL
   - `X509Certificate` value → Certificate

### Google Workspace

1. Go to **Apps** → **Web and mobile apps** → **Add app** → **Add custom SAML app**
2. Enter app name, click **Continue**
3. Download **IdP metadata** or note:
   - **SSO URL**
   - **Entity ID**
   - **Certificate**
4. Upload `sp_metadata.xml` OR enter:
   - **ACS URL**: `http://localhost:8001/auth/saml/acs`
   - **Entity ID**: `http://localhost:8001`
5. **Attribute Mapping**:
   - `email` → Basic Information → Primary email
   - `firstName` → Basic Information → First name
   - `lastName` → Basic Information → Last name
6. Turn on for users

## Step 4: Configure Service Provider

### Option A: Python Script

Create `configure_saml.py`:

```python
from auth.saml_config import SAMLConfig, set_saml_config

config = SAMLConfig(
    tenant_id="acme-corp",
    sp_entity_id="http://localhost:8001",
    sp_acs_url="http://localhost:8001/auth/saml/acs",
    sp_sls_url="http://localhost:8001/auth/saml/sls/acme-corp",
    
    # From IdP (Okta example)
    idp_entity_id="http://www.okta.com/exk123abc",
    idp_sso_url="https://dev-123456.okta.com/app/dev-123456_safeteval_1/exk123abc/sso/saml",
    idp_slo_url="https://dev-123456.okta.com/app/dev-123456_safeteval_1/exk123abc/slo/saml",  # Optional
    idp_x509_cert="""MIIDpDCCAoygAwIBAgIGAXqJvr...
... paste certificate here (remove BEGIN/END lines) ...""",
    
    name_id_format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    authn_requests_signed=False,
    want_assertions_signed=True,
    
    attribute_mapping={
        "email": "email",
        "first_name": "firstName",
        "last_name": "lastName",
    },
    
    default_role="viewer",
    enabled=True,
)

set_saml_config(config)
print("SAML configured successfully!")
```

Run:
```bash
PYTHONPATH=src python configure_saml.py
```

### Option B: Direct SQL

```sql
INSERT INTO saml_config (
    tenant_id,
    sp_entity_id,
    sp_acs_url,
    sp_sls_url,
    idp_entity_id,
    idp_sso_url,
    idp_slo_url,
    idp_x509_cert,
    name_id_format,
    authn_requests_signed,
    want_assertions_signed,
    attribute_mapping,
    default_role,
    enabled
) VALUES (
    'acme-corp',
    'http://localhost:8001',
    'http://localhost:8001/auth/saml/acs',
    'http://localhost:8001/auth/saml/sls/acme-corp',
    'http://www.okta.com/exk123abc',
    'https://dev-123456.okta.com/app/.../sso/saml',
    'https://dev-123456.okta.com/app/.../slo/saml',
    'MIIDpDCCAoygAwIBAgIGAXq...',
    'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
    0,
    1,
    '{"email": "email", "first_name": "firstName", "last_name": "lastName"}',
    'viewer',
    1
);
```

## Step 5: Test SSO Login

1. **Visit Login URL**:
   ```
   http://localhost:8001/auth/saml/login/acme-corp
   ```

2. **Authenticate** at your IdP

3. **Redirected back** with session cookie

4. **Verify User Created**:
   ```sql
   SELECT * FROM users WHERE tenant_id = 'acme-corp';
   ```

## Step 6: Add "Login via SSO" Button

### HTML Button

```html
<a href="/auth/saml/login/acme-corp?redirect_url=/dashboard" 
   class="btn btn-primary">
  Login via SSO
</a>
```

### With Company Logo

```html
<a href="/auth/saml/login/acme-corp" class="sso-button">
  <img src="/logos/acme.png" alt="Acme Corp">
  Sign in with Acme SSO
</a>
```

## Troubleshooting

### Issue: "SAML not configured for tenant"

**Fix**: Check database:
```sql
SELECT * FROM saml_config WHERE tenant_id = 'acme-corp' AND enabled = 1;
```

If no results, re-run configuration script.

### Issue: "Invalid signature"

**Fix**: Verify certificate format:
1. Certificate should NOT include `-----BEGIN CERTIFICATE-----` or `-----END CERTIFICATE-----`
2. Should be one continuous string (newlines removed)
3. Copy ONLY the certificate content from IdP metadata

### Issue: "Invalid audience"

**Fix**: Ensure SP entity ID matches:
- In SAML config: `sp_entity_id`
- In IdP config: Audience/Entity ID
- Both should be exactly the same (e.g., `http://localhost:8001`)

### Issue: User created but no email

**Fix**: Check attribute mapping:
1. View SAML response (browser dev tools → Network → ACS POST)
2. Check attribute names in response
3. Update `attribute_mapping` to match

## Production Checklist

- [ ] Use HTTPS URLs (`https://` not `http://`)
- [ ] Update `sp_entity_id` to production domain
- [ ] Update `sp_acs_url` to production domain
- [ ] Enable `want_assertions_signed = True`
- [ ] Test with real users
- [ ] Set up monitoring for SAML errors
- [ ] Document IdP contact for certificate rotation
- [ ] Consider signing SAML requests (`authn_requests_signed`)

## Common IdP Settings

### Okta

```python
idp_entity_id = "http://www.okta.com/exk..."
idp_sso_url = "https://dev-123456.okta.com/app/.../sso/saml"
name_id_format = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
```

### Azure AD

```python
idp_entity_id = "https://sts.windows.net/abc123.../"
idp_sso_url = "https://login.microsoftonline.com/.../saml2"
name_id_format = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
```

### Google Workspace

```python
idp_entity_id = "https://accounts.google.com/o/saml2?idpid=C..."
idp_sso_url = "https://accounts.google.com/o/saml2/idp?idpid=C..."
name_id_format = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
```

### OneLogin

```python
idp_entity_id = "https://app.onelogin.com/saml/metadata/..."
idp_sso_url = "https://app.onelogin.com/trust/saml2/http-post/sso/..."
name_id_format = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
```

## Next Steps

- Read full documentation: [SAML_SSO.md](SAML_SSO.md)
- Configure multiple tenants
- Set up role mapping
- Enable Single Logout
- Monitor SAML usage

## Support

For issues:
1. Check IdP logs
2. Enable debug logging: `logging.getLogger("auth.saml").setLevel(logging.DEBUG)`
3. Test with SAML tracer browser extension
4. Review [SAML_SSO.md](SAML_SSO.md) troubleshooting section

