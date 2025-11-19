# Business Continuity Plan - Solo Founder Edition

**Version**: 1.0  
**Effective Date**: October 11, 2025  
**Owner**: Solo Founder  
**Review**: Annual

---

## Purpose

Ensure SeaRei can continue operating during disruptions.

---

## Critical Business Functions

1. **API Service** - Core scoring endpoints must stay up
2. **Data Integrity** - Customer data must not be lost
3. **Customer Support** - Must be able to respond to customers

---

## Recovery Objectives

- **RTO (Recovery Time Objective)**: 24 hours
- **RPO (Recovery Point Objective)**: 24 hours

(Realistic for solo founder - adjust as you grow)

---

## Backup Strategy

### What to Backup
- Database (`history.db`) - Daily
- Configuration files (`config.yaml`, `policy/policy.yaml`)
- Custom code (already in Git)

### How to Backup

**Option 1: Simple File Backup** (Start Here)
```bash
# Daily backup script
cp history.db backups/history_$(date +%Y%m%d).db
tar -czf backups/config_$(date +%Y%m%d).tar.gz config.yaml policy/
```

**Option 2: Cloud Backup** (When You Have Revenue)
- AWS S3 or Backblaze B2 (~$5/month)
- Automated daily backups
- Geographic redundancy

### Backup Testing
- **Frequency**: Quarterly
- **Process**: Restore backup to test system, verify data
- **Documentation**: Note test date and results

---

## Disaster Scenarios & Recovery

### Scenario 1: Laptop/Computer Failure

**Impact**: Can't work on the project  
**Recovery**:
1. Get new computer or borrow one
2. Clone code from GitHub
3. Restore database from backup
4. Reinstall dependencies
5. Resume operations

**Time**: 4-8 hours  
**Prevention**: 
- Keep Git repo up to date
- Daily backups to external drive or cloud
- Document setup process

---

### Scenario 2: Database Corruption

**Impact**: Data lost or unreadable  
**Recovery**:
1. Stop application
2. Restore from most recent backup
3. Check data integrity
4. Resume operations

**Time**: 1-2 hours  
**Prevention**:
- Daily backups
- SQLite WAL mode (already enabled)
- Regular database integrity checks

---

### Scenario 3: Code Loss

**Impact**: Lost recent work  
**Recovery**:
1. Clone from GitHub
2. Check last commit date
3. Redo recent work if needed

**Time**: 1-4 hours  
**Prevention**:
- Commit and push daily (at minimum)
- Push after any significant work

---

### Scenario 4: Hosting Provider Down

**Impact**: Service unavailable  
**Recovery**:
1. Wait for provider recovery, OR
2. Deploy to alternative hosting
3. Update DNS if needed

**Time**: 2-8 hours  
**Prevention**:
- Document deployment process
- Keep Docker/deployment configs updated
- Consider backup hosting (when revenue allows)

---

## Communication Plan

### If Service is Down

**Internal** (You):
- Note incident start time
- Document what happened
- Track recovery actions

**External** (Customers):
- Update status page (if you have one)
- Email affected customers
- Provide ETA for recovery

**Template Email**:
```
Subject: SeaRei Service Disruption - [Brief Description]

Hi [Customer],

We're experiencing a service disruption affecting [what's affected].

Status: Investigating / In Progress / Resolved
Impact: [describe impact]
ETA: [estimated recovery time]

We'll update you as we learn more.

Sorry for the inconvenience.
[Your name]
```

---

## Emergency Contacts

**Primary**: [Your Phone/Email]  
**Backup**: [Trusted Friend/Colleague]  
**Hosting Support**: [Provider's support number]

---

## Critical Dependencies

| Dependency | Impact if Lost | Backup Plan |
|------------|----------------|-------------|
| GitHub | Can't access code | Local clone |
| Hosting | Service down | Deploy elsewhere |
| Domain | Can't reach site | Alternative domain |
| Email | Can't notify customers | Alternative email |

---

## Testing

- **Backup Restore Test**: Quarterly
- **Plan Review**: After any major incident
- **Full DR Drill**: Annual (when practical)

**Last Tested**: __________  
**Next Test**: __________

---

## Key Assets Inventory

1. **Code Repository**: GitHub
2. **Database**: `history.db` (132MB+)
3. **Configuration**: `config.yaml`, `policy/policy.yaml`
4. **Documentation**: All .md files
5. **Evidence**: `evidence/` folder (365-day retention)

---

## Simple Backup Script

```bash
#!/bin/bash
# Simple daily backup for solo founder

BACKUP_DIR="backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup database
cp history.db "$BACKUP_DIR/history.db"

# Backup configs
tar -czf "$BACKUP_DIR/config.tar.gz" config.yaml policy/ .env 2>/dev/null

# Keep last 30 days only
find backups/ -type d -mtime +30 -exec rm -rf {} + 2>/dev/null

echo "✅ Backup complete: $BACKUP_DIR"
```

**Setup**:
```bash
chmod +x backup.sh
# Run daily via cron
0 3 * * * /path/to/backup.sh
```

---

## Recovery Checklist

When disaster strikes:

- [ ] Stay calm
- [ ] Assess situation (what's broken?)
- [ ] Stop making it worse (stop services if needed)
- [ ] Document what happened
- [ ] Check backups availability
- [ ] Restore from backup
- [ ] Test restored system
- [ ] Resume operations
- [ ] Notify customers
- [ ] Write post-incident review

---

**Approved By**: [Founder]  
**Date**: __________  
**Last Incident**: None (yet)  
**Last DR Test**: __________


