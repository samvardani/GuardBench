# Branch Protection Setup for SeaRei
## Enforce Quality Gates

**Go to:** https://github.com/samvardani/SeaRei/settings/branches

---

## Step 1: Add Branch Protection Rule

**Click:** "Add branch protection rule"

**Branch name pattern:** `improve/2025-10-seval` (or `main`)

---

## Step 2: Configure Protection Rules

### ✅ **Pull Request Requirements**

Enable these:
```
✅ Require a pull request before merging
   └─ Require approvals: 1 (solo) or 2 (team)
   └─ Dismiss stale reviews when new commits pushed
   └─ Require review from Code Owners (uses CODEOWNERS file!)
   └─ Require approval of the most recent reviewable push

✅ Require conversation resolution before merging
```

### ✅ **Status Checks** (When you add GitHub Actions)

Enable these:
```
✅ Require status checks to pass before merging
   └─ Require branches to be up to date before merging

   Status checks to require (add when workflows exist):
   ├─ pytest (all tests)
   ├─ mypy (type checking)
   ├─ ruff (linting)
   ├─ snyk (security scan)
   └─ coverage (70%+ gate)
```

### ✅ **Additional Protections**

```
✅ Require signed commits (for SOC2 compliance)

✅ Require linear history (cleaner git log)

✅ Include administrators (you can't bypass either!)

✅ Restrict who can push:
   └─ Add: @samvardani (only you can push directly)
```

### ✅ **Rules for Deletions**

```
✅ Do not allow bypassing the above settings

✅ Do not allow force pushes

✅ Do not allow deletions
```

---

## Step 3: Save

**Click:** "Create" or "Save changes"

---

## ✅ Result After Setup

**Protection Active:**
```
❌ Cannot merge without approval
❌ Cannot merge with failing tests
❌ Cannot merge without code owner review
❌ Cannot force push (preserves history)
❌ Cannot delete branch accidentally
✅ All changes must go through PR + review
```

**SOC2 Benefits:**
- Evidence of code review (required for CC5.2)
- Audit trail of approvals (required for CC6.1)
- Change management process (required for CC8.1)

---

## 🎯 Impact on Your Roadmap

**Week 1-2: Emergency Fixes**
```
Before: Could accidentally break main
After: ✅ Must pass tests + get approval
```

**Week 3-8: Test Expansion (200+ tests)**
```
Before: Could add failing tests
After: ✅ Coverage gate enforced, tests must pass
```

**Month 4-6: SOC2 Certification**
```
SOC2 Auditor: "How do you control changes?"
You: "Protected branches + required reviews + status checks"
Evidence: ✅ GitHub audit log
```

---

## 📊 Time to Set Up

**Total Time:** 5 minutes
**Immediate Benefits:**
- Zero broken builds
- Mandatory code review
- SOC2 compliance evidence
- Quality enforcement

**Do this now!** It prevents the issues that caused your 3 test failures.

