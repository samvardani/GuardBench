#!/usr/bin/env python3
"""
Interactive MFA Demo

Shows exactly how MFA works with a real example.
Generates a working QR code you can scan!
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from service.mfa import (
    setup_mfa,
    verify_totp_code,
    get_current_totp_code,
    verify_backup_code
)
import json
import time


def main():
    print("=" * 60)
    print("🔐 MFA Interactive Demo")
    print("=" * 60)
    print()
    
    # Step 1: Setup MFA
    print("Step 1: Setting up MFA for user@example.com...")
    setup = setup_mfa("user@example.com", "SeaRei Demo")
    
    print("✅ MFA Setup Complete!")
    print()
    print(f"Secret: {setup.secret}")
    print()
    
    # Show QR code URL (can be used in HTML)
    print("QR Code URL (paste in browser):")
    print("-" * 60)
    qr_url = f"data:image/png;base64,{setup.qr_code_base64}"
    print(qr_url[:100] + "...")
    print("-" * 60)
    print()
    
    # Save QR code to file
    qr_file = Path("mfa_qr_code.html")
    with open(qr_file, 'w') as f:
        f.write(f"""
<!DOCTYPE html>
<html>
<head><title>MFA QR Code</title></head>
<body style="text-align:center; padding:50px; font-family:Arial;">
    <h1>SeaRei MFA Setup</h1>
    <p>Scan this QR code with Google Authenticator or Authy:</p>
    <img src="{qr_url}" alt="MFA QR Code" style="max-width:400px; border:2px solid #ccc; padding:20px;"/>
    <p>Account: user@example.com</p>
    <p>Secret (manual entry): <code>{setup.secret}</code></p>
</body>
</html>
        """)
    
    print(f"✅ QR Code saved to: {qr_file.absolute()}")
    print("   Open this file in your browser to scan!")
    print()
    
    # Show backup codes
    print("Backup Codes (save these!):")
    print("-" * 60)
    for i, code in enumerate(setup.backup_codes, 1):
        print(f"{i:2d}. {code}")
    print("-" * 60)
    print()
    
    # Step 2: Demonstrate code verification
    print("Step 2: Testing TOTP Codes...")
    print()
    
    for i in range(3):
        current_code = get_current_totp_code(setup.secret)
        print(f"Current TOTP code: {current_code}")
        
        # Verify it
        is_valid = verify_totp_code(setup.secret, current_code)
        print(f"✅ Code verified: {is_valid}")
        
        if i < 2:
            print("Waiting 30 seconds for next code...")
            time.sleep(30)
            print()
    
    print()
    
    # Step 3: Test backup code
    print("Step 3: Testing Backup Codes...")
    print()
    
    codes_json = json.dumps(setup.backup_codes)
    first_code = setup.backup_codes[0]
    
    print(f"Trying backup code: {first_code}")
    valid, updated_json = verify_backup_code(codes_json, first_code)
    
    if valid:
        print("✅ Backup code accepted!")
        remaining = json.loads(updated_json)
        print(f"   Remaining codes: {len(remaining)}/10")
    else:
        print("❌ Backup code rejected")
    
    print()
    
    # Try same code again (should fail)
    print(f"Trying same backup code again: {first_code}")
    valid2, _ = verify_backup_code(updated_json, first_code)
    
    if not valid2:
        print("✅ Correctly rejected (already used)")
    else:
        print("❌ ERROR: Code was accepted twice!")
    
    print()
    
    # Summary
    print("=" * 60)
    print("✅ MFA Demo Complete!")
    print("=" * 60)
    print()
    print("What just happened:")
    print("1. Generated MFA secret and QR code")
    print("2. Created 10 backup codes")
    print("3. Verified TOTP codes (changes every 30 sec)")
    print("4. Tested backup code (one-time use)")
    print()
    print("Next steps:")
    print("1. Open mfa_qr_code.html in your browser")
    print("2. Scan with Google Authenticator or Authy")
    print("3. App will show 6-digit codes")
    print("4. Use verify_totp_code() to check them")
    print()
    print("Your MFA is working! 🎉")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

