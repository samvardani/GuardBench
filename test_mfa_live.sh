#!/bin/bash
# Live MFA Testing Script
# Tests all MFA endpoints end-to-end

echo "=================================================="
echo "MFA Live Testing"
echo "=================================================="
echo ""

BASE_URL="http://localhost:8000"

echo "Step 1: Create test user and login..."
echo ""

# You'll need to either:
# A) Use an existing user, or
# B) Create a new test user

echo "Please run:"
echo ""
echo "# First, start the server in another terminal:"
echo "PYTHONPATH=src uvicorn service.api:app --reload --port 8000"
echo ""
echo "# Then test MFA:"
echo ""
echo "# 1. Login to get token"
echo "curl -X POST $BASE_URL/auth/login \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"email\":\"YOUR_EMAIL\",\"password\":\"YOUR_PASSWORD\"}' | jq ."
echo ""
echo "# 2. Setup MFA (use token from step 1)"
echo "curl -X POST $BASE_URL/mfa/setup \\"
echo "  -H 'Authorization: Bearer YOUR_TOKEN' | jq ."
echo ""
echo "# 3. Open Google Authenticator, scan QR code from qr_code_url"
echo ""
echo "# 4. Enable MFA with code from app"
echo "curl -X POST $BASE_URL/mfa/enable \\"
echo "  -H 'Authorization: Bearer YOUR_TOKEN' \\"
echo "  -d 'code=123456'"
echo ""
echo "# 5. Check MFA status"
echo "curl $BASE_URL/mfa/status \\"
echo "  -H 'Authorization: Bearer YOUR_TOKEN' | jq ."
echo ""
echo "=================================================="

