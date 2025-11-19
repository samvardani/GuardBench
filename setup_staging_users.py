#!/usr/bin/env python3
"""Quick script to create test users for the Virtual Staging Platform."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from service.db import create_tenant, create_user

def main():
    print("Creating test users for Virtual Staging Platform...")
    print("-" * 50)
    
    # Create tenant
    try:
        tenant = create_tenant("Staging Company", slug="staging-co")
        print(f"✅ Tenant created: {tenant['name']}")
        print(f"   Tenant ID: {tenant['tenant_id']}")
        print(f"   Slug: {tenant['slug']}")
    except ValueError as e:
        print(f"⚠️  Tenant may already exist: {e}")
        # Try to continue with existing tenant
        tenant = {"tenant_id": "existing", "name": "Existing Tenant"}
    
    print()
    
    # Create users
    users = [
        ("client@example.com", "ClientPass123!", "client", "Client"),
        ("staff@example.com", "StaffPass123!", "staff", "Staff"),
        ("admin@example.com", "AdminPass123!", "admin", "Admin"),
    ]
    
    for email, password, role, label in users:
        try:
            user = create_user(tenant["tenant_id"], email, password, role=role)
            print(f"✅ {label} user created:")
            print(f"   Email: {email}")
            print(f"   Password: {password}")
            print(f"   Role: {role}")
        except ValueError as e:
            print(f"⚠️  {label} user may already exist: {e}")
    
    print()
    print("-" * 50)
    print("Setup complete!")
    print()
    print("You can now log in at: http://localhost:8001/staging/")
    print()
    print("Test credentials:")
    print("  Client: client@example.com / ClientPass123!")
    print("  Staff:  staff@example.com / StaffPass123!")
    print("  Admin:  admin@example.com / AdminPass123!")

if __name__ == "__main__":
    main()




