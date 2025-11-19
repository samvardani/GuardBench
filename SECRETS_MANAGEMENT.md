# Secrets Management - Environment Variables

**Goal**: Move secrets out of code into environment variables  
**Method**: .env files + environment variables  
**Cost**: $0  
**Time**: 2-3 hours  
**SOC 2 Benefit**: Secure key management ✅

---

## ✅ DONE - Quick Setup

### 1. Created .env.example Template
- Location: `.env.example`
- Contains all secrets your app needs
- Safe to commit to git (no real values)

### 2. Setup Instructions

```bash
# Copy template
cp .env.example .env

# Generate encryption key
python3 -c "import secrets; print('DB_ENCRYPTION_KEY=' + secrets.token_hex(32))" >> .env

# Generate policy admin token
python3 -c "import secrets; print('POLICY_ADMIN_TOKEN=' + secrets.token_hex(32))" >> .env

# Add .env to .gitignore (if not already)
echo ".env" >> .gitignore
```

### 3. Load in Python

```python
# At top of your modules
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file

# Use secrets
db_key = os.getenv("DB_ENCRYPTION_KEY")
admin_token = os.getenv("POLICY_ADMIN_TOKEN")
```

---

## ✅ What This Achieves

SOC 2 Requirements:
- ✅ Secrets not in code
- ✅ Secrets not in version control
- ✅ Easy rotation (just change .env)
- ✅ Different secrets per environment (dev/prod)

---

## Next Level (Optional, Later)

When you have budget:
- HashiCorp Vault ($0 open source, but complex)
- AWS Secrets Manager ($0.40/secret/month)
- Azure Key Vault (similar pricing)

For now, .env files are **perfectly acceptable for SOC 2**.

---

**Status**: ✅ COMPLETE for solo founder!


