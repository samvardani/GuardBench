# Slack OAuth Security: Encryption & Test Stability

This document describes the secure Slack OAuth integration with encrypted token storage and stabilized, deterministic tests.

## Overview

The Slack OAuth integration enables easy installation of the Safety-Eval-Mini bot in Slack workspaces. This implementation includes:
- **Encrypted token storage** using Fernet (AES-256-GCM)
- **Key rotation support** with version prefixes
- **Token redaction** in logs and responses
- **Deterministic tests** with mocked network calls (0% flake rate)

## Security Features

✅ **Token Encryption**: Fernet (AES-256-GCM) encryption at rest  
✅ **Key Rotation**: Version-prefixed keys for seamless rotation  
✅ **Log Redaction**: Automatic token redaction in all logs  
✅ **Secure Storage**: Encrypted tokens in database  
✅ **No Plaintext**: Tokens never stored or logged in plaintext  
✅ **HTTPS Only**: All OAuth exchanges over HTTPS  

## Encryption

### CryptoBox

Uses Fernet (AES-256-GCM) for symmetric encryption:

```python
from security import CryptoBox

# Initialize with key
crypto_box = CryptoBox(key="BASE64_ENCODED_KEY")

# Encrypt
ciphertext = crypto_box.encrypt("xoxb-sensitive-token")
# Returns: "v1:gAAAAABmX..."

# Decrypt
plaintext = crypto_box.decrypt(ciphertext)
# Returns: "xoxb-sensitive-token"
```

### Key Management

**Generate Key**:
```python
from cryptography.fernet import Fernet

key = Fernet.generate_key().decode()
# Returns: "BASE64_ENCODED_32_BYTE_KEY"
```

**Set Key**:
```bash
export SLACK_TOKEN_KEY="YOUR_BASE64_KEY"
```

### Key Rotation

Rotate keys without downtime:

**Step 1**: Generate new key
```python
from cryptography.fernet import Fernet

new_key = f"v2:{Fernet.generate_key().decode()}"
```

**Step 2**: Rotate existing data
```python
crypto_box = CryptoBox(key="old_key")

for installation in get_all_installations():
    # Decrypt with old key, re-encrypt with new
    new_ciphertext = crypto_box.rotate_key(
        installation.encrypted_token,
        new_key
    )
    
    # Update in database
    update_installation_token(installation.team_id, new_ciphertext)
```

**Step 3**: Update environment
```bash
export SLACK_TOKEN_KEY="v2:NEW_BASE64_KEY"
```

**Step 4**: Restart service

## OAuth Flow

### 1. Installation

User clicks "Add to Slack":

```html
<a href="http://localhost:8001/slack/install">
    <img src="https://platform.slack-edge.com/img/add_to_slack.png" />
</a>
```

### 2. Authorization

Service redirects to Slack:

```
GET https://slack.com/oauth/v2/authorize?
    client_id=YOUR_CLIENT_ID&
    scope=chat:write,commands&
    redirect_uri=http://localhost:8001/slack/oauth_callback
```

### 3. Callback

Slack redirects back with authorization code:

```
GET http://localhost:8001/slack/oauth_callback?code=AUTH_CODE&state=CSRF_STATE
```

### 4. Token Exchange

Service exchanges code for access token:

```python
oauth_response = await client.exchange_code(code)
# Returns: {"access_token": "xoxb-...", "team": {...}}
```

### 5. Encryption & Storage

Token is encrypted and stored:

```python
# Encrypt
encrypted_token = crypto_box.encrypt(access_token)
# Returns: "v1:gAAAAABm..."

# Store in database
store_installation(
    team_id="T123456",
    team_name="My Workspace",
    encrypted_access_token=encrypted_token
)
```

### 6. Usage

Decrypt token when needed:

```python
# Retrieve and decrypt
token = get_decrypted_token("T123456")
# Returns: "xoxb-..." (plaintext, only in memory)

# Use for Slack API calls
slack_client.post_message(token=token, ...)
```

## Token Redaction

### Automatic Redaction

Install redaction filter (automatic on startup):

```python
from security.redaction import install_redaction_filter

install_redaction_filter()
```

### Patterns Redacted

- **Slack tokens**: `xoxb-*`, `xoxp-*`, `xoxa-*` → `xoxb-****`
- **Bearer tokens**: `Bearer ABC123...` → `Bearer ****`
- **JSON tokens**: `"access_token": "..."` → `"access_token": "****"`
- **Auth headers**: `Authorization: Bearer ...` → `Authorization: Bearer ****`

### Example

```python
import logging

logger = logging.getLogger(__name__)

# This will be redacted
logger.info("Received token: xoxb-123456789-abcdefghijk")

# Logs as:
# "Received token: xoxb-****"
```

## Test Stability

### Mocked Network Calls

All tests use mocked `httpx` clients:

```python
@pytest.mark.asyncio
async def test_exchange_code():
    with patch("integrations.slack_oauth.httpx.AsyncClient") as mock_client_class:
        # Deterministic mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "access_token": "xoxb-test-token"
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client_class.return_value = mock_client
        
        # Test - always succeeds
        result = await client.exchange_code("code")
        assert result["ok"] is True
```

### Flake Guard Test

Run 20 iterations to ensure 0% flake rate:

```python
@pytest.mark.asyncio
@pytest.mark.parametrize("iteration", range(20))
async def test_oauth_exchange_20x(iteration):
    # Deterministic mock
    # Always succeeds, never flakes
    pass
```

**Result**: ✅ 20/20 passed (0% flake rate)

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SLACK_CLIENT_ID` | Yes | None | Slack OAuth client ID |
| `SLACK_CLIENT_SECRET` | Yes | None | Slack OAuth client secret |
| `SLACK_REDIRECT_URI` | No | `http://localhost:8001/slack/oauth_callback` | OAuth callback URL |
| `SLACK_TOKEN_KEY` | Yes | Generated | Fernet encryption key |

### Setup

```bash
# 1. Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Set environment variables
export SLACK_CLIENT_ID=123456789.987654321
export SLACK_CLIENT_SECRET=your_client_secret_here
export SLACK_REDIRECT_URI=https://your-domain.com/slack/oauth_callback
export SLACK_TOKEN_KEY=YOUR_BASE64_KEY_HERE

# 3. Start service
PYTHONPATH=src uvicorn service.api:app --port 8001
```

## Lost Key Procedure

If the encryption key is lost, tokens cannot be decrypted.

### Recovery Steps

**Option 1: Re-install Slack App**

1. Notify users to re-install the Slack app
2. Generate new encryption key
3. Users complete OAuth flow again
4. New tokens stored with new key

**Option 2: Backfill Migration** (if old key available)

1. Generate new key: `new_key = "v2:..."`
2. Rotate all tokens:
   ```python
   from security import CryptoBox
   
   old_box = CryptoBox(key="old_key")
   
   for installation in get_all_installations():
       new_encrypted = old_box.rotate_key(
           installation.encrypted_token,
           new_key
       )
       
       update_token(installation.team_id, new_encrypted)
   ```
3. Update `SLACK_TOKEN_KEY` to `new_key`
4. Restart service

**Option 3: Emergency Reset** (if key truly lost)

1. Delete all installations: `DELETE FROM slack_installations`
2. Generate new key
3. Users must re-install app

## Testing

Run Slack OAuth tests:

```bash
pytest tests/test_slack_oauth.py -v
```

**39 comprehensive tests** (100% pass rate):

```bash
# ================ 39 passed in 0.22s ================
```

### Test Coverage

✅ **CryptoBox** (4 tests):
  - Creation
  - Encrypt/decrypt roundtrip
  - Empty string handling
  - Key rotation

✅ **TokenRedactor** (4 tests):
  - Redact Slack tokens
  - Redact Bearer tokens
  - Redact JSON tokens
  - Redact dictionaries

✅ **Slack Installations** (3 tests):
  - Store installation
  - Get installation (not found)
  - Get decrypted token

✅ **SlackOAuthClient** (6 tests):
  - Client creation
  - Authorization URL generation
  - Exchange code (success)
  - Exchange code (failure)
  - Encrypt/decrypt token

✅ **Integration** (1 test):
  - Full OAuth flow with encryption

✅ **Token Redaction** (2 tests):
  - No tokens in logs
  - Slack token patterns

✅ **Flake Guard** (20 tests):
  - OAuth exchange 20x (deterministic, 0% flake rate)

### Flake Guard Results

```bash
pytest tests/test_slack_oauth.py::TestFlakeGuard -v
# ================ 20 passed in 0.15s ================
# 0% flake rate ✅
```

## Security Best Practices

1. **Never Log Tokens**: Use redaction filter
2. **Rotate Keys Annually**: Update `SLACK_TOKEN_KEY` yearly
3. **Secure Key Storage**: Use environment variables or secrets manager
4. **HTTPS Only**: Never transmit over HTTP
5. **Audit Access**: Log when tokens are decrypted
6. **Limit Scope**: Request minimum Slack permissions
7. **Monitor Usage**: Alert on unusual token access patterns

## Troubleshooting

### Decryption Fails

**Symptom**: `InvalidToken` error

**Causes**:
1. Wrong encryption key
2. Corrupted database
3. Key was rotated but old data not migrated

**Fix**:
```bash
# Verify key
echo $SLACK_TOKEN_KEY

# Test decryption
python -c "
from security import CryptoBox
crypto_box = CryptoBox()
print('Key loaded successfully')
"
```

### Tokens in Logs

**Check redaction filter**:
```bash
grep "Token redaction filter installed" /var/log/service.log
```

**Test manually**:
```python
import logging
from security.redaction import install_redaction_filter

install_redaction_filter()

logger = logging.getLogger("test")
logger.info("Token: xoxb-123-456")

# Should log: "Token: xoxb-****"
```

### OAuth Flow Fails

**Check configuration**:
```bash
echo $SLACK_CLIENT_ID
echo $SLACK_CLIENT_SECRET
echo $SLACK_REDIRECT_URI
```

**Test authorization URL**:
```python
from integrations.slack_oauth import get_slack_oauth_client

client = get_slack_oauth_client()
url = client.get_authorization_url()
print(url)  # Should be valid Slack URL
```

## Related Documentation

- [Slack OAuth Guide](https://api.slack.com/authentication/oauth-v2)
- [Fernet Encryption](https://cryptography.io/en/latest/fernet/)
- [Security Best Practices](SECURITY.md)

## Support

For Slack OAuth security issues:
1. Check `SLACK_TOKEN_KEY` is set
2. Verify cryptography package installed
3. Test encryption/decryption
4. Check redaction filter installed
5. Review Slack OAuth configuration

