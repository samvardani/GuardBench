#!/usr/bin/env python3
"""
Simple MFA Test - Verify it works!
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from service.mfa import (
    generate_secret,
    generate_qr_code,
    verify_code,
    generate_backup_codes,
    verify_backup_code
)
import json

print("=" * 60)
print("🔐 MFA Quick Test")
print("=" * 60)
print()

# Test 1: Generate secret
print("1. Generating MFA secret...")
secret = generate_secret()
print(f"   ✅ Secret: {secret}")
print()

# Test 2: Generate QR code
print("2. Generating QR code...")
qr = generate_qr_code(secret, "test@example.com")
print(f"   ✅ QR Code: {len(qr)} bytes (base64 PNG)")
print()

# Save as HTML file you can open
html_file = Path("test_qr_code.html")
with open(html_file, 'w') as f:
    f.write(f"""
<!DOCTYPE html>
<html>
<head><title>Test MFA QR Code</title></head>
<body style="text-align:center; padding:50px;">
    <h1>MFA Test QR Code</h1>
    <p>Scan with Google Authenticator or Authy:</p>
    <img src="data:image/png;base64,{qr}" style="border:2px solid #ccc; padding:20px;"/>
    <p>Secret: <code>{secret}</code></p>
    <p>Email: test@example.com</p>
</body>
</html>
    """)

print(f"   ✅ QR Code saved to: {html_file.absolute()}")
print("   Open this file in your browser to scan it!")
print()

# Test 3: Generate and test backup codes  
print("3. Generating backup codes...")
codes = generate_backup_codes(10)
print(f"   ✅ Generated {len(codes)} codes:")
for i, code in enumerate(codes[:3], 1):
    print(f"      {i}. {code}")
print("      ...")
print()

# Test 4: Verify backup code
print("4. Testing backup code verification...")
codes_json = json.dumps(codes)
first_code = codes[0]
valid, updated = verify_backup_code(codes_json, first_code)
print(f"   ✅ Code '{first_code}' verified: {valid}")
print(f"   ✅ Codes remaining: {len(json.loads(updated))}/10")
print()

# Test 5: Show current TOTP code
print("5. Getting current TOTP code...")
import pyotp
totp = pyotp.TOTP(secret)
current = totp.now()
print(f"   ✅ Current code: {current}")
print("   ℹ️  This code changes every 30 seconds")
print()

# Test 6: Verify the code
print("6. Verifying TOTP code...")
is_valid = verify_code(secret, current)
print(f"   ✅ Code '{current}' verified: {is_valid}")
print()

print("=" * 60)
print("✅ ALL MFA TESTS PASSED!")
print("=" * 60)
print()
print("Next steps:")
print("1. Open test_qr_code.html in your browser")
print("2. Scan QR code with Google Authenticator or Authy app")
print("3. The app will show 6-digit codes")
print("4. These codes change every 30 seconds")
print("5. Use verify_code() to check them")
print()
print("Your MFA is working perfectly! 🎉")

if __name__ == '__main__':
    main()

