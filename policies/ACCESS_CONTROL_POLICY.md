# Access Control Policy

**Version**: 1.0  
**Effective Date**: October 11, 2025  
**Owner**: Solo Founder  
**Review**: Annual

---

## Purpose

Define how access to SeaRei systems is granted, managed, and revoked.

---

## Scope

All SeaRei systems: production, development, databases, and admin tools.

---

## Access Principles

1. **Least Privilege**: Users get minimum access needed
2. **Need-to-Know**: Access based on job requirements
3. **Separation of Duties**: No single person has all privileges
4. **Defense in Depth**: Multiple layers of security

---

## User Roles

| Role | Access Level | Can Do |
|------|--------------|--------|
| **viewer** | Read-only | View reports, dashboards |
| **analyst** | Read + Run | View + run evaluations |
| **admin** | Full tenant mgmt | All tenant operations |
| **owner** | Everything | All access + billing |

**Default**: New users get "viewer" role (least privilege)

---

## Authentication

### Password Requirements
- Minimum 12 characters
- Uppercase + lowercase + number + special char
- No common passwords
- Enforced via `password_policy.py`

### Multi-Factor Authentication (MFA)
- **TOTP-based** (Google Authenticator, Authy)
- **Required for**: Admin and owner roles  
- **Optional for**: Viewer and analyst roles
- **Backup codes**: 10 recovery codes provided

### API Tokens
- SHA-256 hashed before storage
- Optional expiration
- Revocable anytime
- Last-used tracking

---

## Access Provisioning

### New User
1. Account created by admin/owner
2. Email invitation sent
3. User sets password (must meet policy)
4. Default role: viewer
5. MFA setup (required for admins)

### Role Changes
1. Requested by user's manager
2. Approved by tenant owner
3. Logged in audit_events
4. Takes effect immediately

### Access Removal
1. User status set to 'inactive'
2. All tokens invalidated
3. MFA disabled
4. Logged in audit_events

---

## Access Reviews

- **Frequency**: Quarterly (every 3 months)
- **Process**: Export user list, review roles, remove inactive
- **Tool**: `scripts/collect_evidence.py` (collects user snapshots)
- **Documentation**: Review results saved to evidence folder

---

## Monitoring

- Login attempts logged (audit_events)
- Failed logins tracked
- MFA usage logged
- Token usage tracked (last_used_at)
- Suspicious activity alerts

---

## Exceptions

None. All users follow this policy.

---

**Approved By**: [Founder]  
**Date**: __________


