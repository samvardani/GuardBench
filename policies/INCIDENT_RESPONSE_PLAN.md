# Incident Response Plan

**Version**: 1.0  
**Effective Date**: October 11, 2025  
**Owner**: Solo Founder  
**Review**: Annual

---

## Purpose

Define how to respond to security incidents for SeaRei platform.

---

## Incident Classification

| Severity | Definition | Examples | Response Time |
|----------|-----------|----------|---------------|
| **P0 - Critical** | Data breach, system down | Database compromised, site offline | Immediate |
| **P1 - High** | Security event, degraded service | Unauthorized access attempt, slow response | 1 hour |
| **P2 - Medium** | Minor security issue | Failed login spike, config error | 4 hours |
| **P3 - Low** | Potential concern | Suspicious activity, minor bug | 24 hours |

---

## Response Procedures

### 1. Detection
- Automated monitoring (Prometheus alerts)
- Log review (audit_events)
- User reports
- System alerts

### 2. Initial Response (First 15 Minutes)
- Assess severity (P0-P3)
- Document incident (create ticket/note)
- Notify if P0/P1

### 3. Containment
- Isolate affected systems if needed
- Disable compromised accounts
- Block malicious IPs if applicable
- Preserve evidence (don't delete logs!)

### 4. Investigation
- Review audit logs (`evidence/` folder)
- Check access logs
- Examine change logs (Git)
- Identify root cause

### 5. Eradication
- Remove threat
- Patch vulnerabilities
- Update configurations
- Reset credentials if compromised

### 6. Recovery
- Restore from backups if needed
- Verify system integrity
- Resume normal operations
- Monitor closely

### 7. Post-Incident Review (Within 1 Week)
- Document what happened
- Root cause analysis
- What worked / what didn't
- Preventive measures
- Update this plan if needed

---

## Contact List (Solo Founder)

**Primary Contact**: [Your Phone/Email]  
**Backup**: [Trusted Friend/Colleague if available]

---

## Evidence Preservation

**DO NOT DELETE**:
- Audit logs
- Access logs
- System logs
- Backups from incident time

Evidence stored in `evidence/` folder (365-day retention).

---

## Common Scenarios

### Scenario 1: Brute Force Login Attempts
**Detection**: Failed login spike in logs  
**Response**: Rate limiting (already implemented), block IP if needed  
**Prevention**: MFA (now implemented)

### Scenario 2: Data Breach
**Detection**: Unauthorized data access  
**Response**: Immediate containment, notify affected users  
**Prevention**: Encryption (at rest + in transit)

### Scenario 3: Service Outage
**Detection**: Health check fails, monitoring alerts  
**Response**: Investigate, restore from backup if needed  
**Prevention**: Circuit breakers, redundancy

### Scenario 4: Compromised Credentials
**Detection**: Login from unusual location/time  
**Response**: Force password reset, invalidate tokens  
**Prevention**: MFA, strong passwords

---

## Testing

- **Tabletop Exercise**: Annual (simulate incident)
- **Plan Review**: After any P0/P1 incident
- **Plan Update**: Annual

---

## Documentation

All incidents documented in:
- `evidence/` folder (automated collection)
- audit_events table (database)
- Separate incident notes (create folder if needed)

---

**Approved By**: [Founder]  
**Date**: __________  
**Last Tested**: __________


