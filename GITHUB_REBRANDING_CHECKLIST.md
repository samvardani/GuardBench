# GitHub Rebranding Checklist
## Update Repository to SeaRei by SeaTechOne LLC

**All code changes are complete and pushed.** This checklist covers GitHub-specific settings that need manual updates.

---

## ✅ Completed (Automated)

- [x] Updated README.md header
- [x] Updated pyproject.toml (package name: searei)
- [x] Updated all evaluation documents
- [x] Updated Dockerfile metadata
- [x] Updated docker-compose.yml container names
- [x] Committed and pushed all changes

---

## 📋 GitHub Repository Settings (Manual)

### 1. Repository Name (Optional but Recommended)

**Current:** `safety-eval-mini`  
**Recommended:** `searei`

**Steps:**
1. Go to https://github.com/samvardani/safety-eval-mini/settings
2. Scroll to "Repository name"
3. Change to: `searei`
4. Click "Rename"

**Note:** GitHub will automatically redirect old URLs, so this is safe.

### 2. Repository Description

**Update to:**
```
SeaRei by SeaTechOne LLC - Enterprise AI safety evaluation platform with REST/gRPC APIs, red-team automation, and governance
```

**Steps:**
1. Go to https://github.com/samvardani/safety-eval-mini
2. Click "⚙️" (gear icon) next to "About"
3. Update description
4. Add website: `https://seatechone.com` (if applicable)
5. Add topics:
   - `ai-safety`
   - `content-moderation`
   - `enterprise`
   - `governance`
   - `red-teaming`
   - `mlops`
6. Click "Save changes"

### 3. Repository Topics/Tags

**Add these topics:**
```
ai-safety
content-moderation
llm-safety
enterprise
governance
red-teaming
policy-as-code
evidence-packs
mlops
fastapi
grpc
```

### 4. Update README Badges (If Any)

If you have badges in README.md, update them:

**Change:**
```markdown
![Build](https://github.com/samvardani/safety-eval-mini/workflows/test/badge.svg)
```

**To:**
```markdown
![Build](https://github.com/samvardani/searei/workflows/test/badge.svg)
```

### 5. GitHub Organization (Recommended)

**Current:** Personal repo (`samvardani/safety-eval-mini`)  
**Recommended:** Organization repo (`seatechone/searei`)

**Benefits:**
- Professional appearance
- Team collaboration
- Access management
- Brand consistency

**Steps:**
1. Create organization: https://github.com/organizations/new
2. Name: `seatechone`
3. Transfer repository: Settings → "Danger Zone" → "Transfer ownership"
4. New owner: `seatechone`
5. New name: `searei`

### 6. Update Default Branch Description

**Current:** `improve/2025-10-seval`  
**Consider:** Rename to `improve/2025-10-searei` or `main`

**Steps:**
1. Create new branch: `git checkout -b main`
2. Push: `git push -u origin main`
3. Go to Settings → Branches → Default branch
4. Change to `main`
5. Update branch protection rules

### 7. GitHub Pages (If Using)

If you have GitHub Pages enabled:

**Update site title:**
1. Go to Settings → Pages
2. Update any custom domain to: `searei.seatechone.com`
3. Update site content/branding

### 8. Repository Social Preview

**Upload a custom social preview image:**
1. Go to Settings → "Social preview"
2. Upload image with SeaRei branding
3. Recommended size: 1280 x 640 px

### 9. License File

**Verify LICENSE file credits SeaTechOne LLC:**

```
MIT License

Copyright (c) 2025 SeaTechOne LLC

Permission is hereby granted...
```

### 10. Security & Support Files

Create/Update:
- `SECURITY.md` - Security policy with SeaTechOne contact
- `SUPPORT.md` - Support channels for SeaRei
- `CODE_OF_CONDUCT.md` - Community guidelines

---

## 🔧 Additional Updates

### 11. GitHub Actions Workflow Names

Update workflow files in `.github/workflows/`:

```yaml
# .github/workflows/test.yml
name: SeaRei CI

on:
  push:
    branches: [main, improve/*]
```

### 12. Issue Templates

Create `.github/ISSUE_TEMPLATE/`:

```markdown
---
name: Bug Report
about: Report a bug in SeaRei
labels: bug
---

**SeaRei Version:** 0.3.1
**Company:** SeaTechOne LLC
...
```

### 13. Pull Request Template

Create `.github/PULL_REQUEST_TEMPLATE.md`:

```markdown
## SeaRei Pull Request

**Company:** SeaTechOne LLC

### Description
...
```

---

## 📢 Communication Updates

### 14. Update External References

If you have external references, update them:

- [ ] Docker Hub: `seatechone/searei`
- [ ] PyPI: Publish as `searei`
- [ ] Documentation site: Update domain
- [ ] Blog posts: Update product name
- [ ] Social media: Announce rebranding

### 15. Update Links in Documentation

**Search and replace in all docs:**
```bash
# Find old references
grep -r "safety-eval-mini" docs/

# Replace with
# searei or SeaRei (context-dependent)
```

---

## ✅ Verification Checklist

After completing above steps, verify:

- [ ] Repository name is `searei` (or old name with redirects working)
- [ ] Description mentions "SeaRei by SeaTechOne LLC"
- [ ] Topics/tags include ai-safety, enterprise, governance
- [ ] README.md shows SeaRei branding
- [ ] Social preview image has SeaRei branding
- [ ] All PRs reference SeaRei
- [ ] Issues reference SeaRei
- [ ] Workflows have correct names

---

## 🚀 Post-Rebranding Launch

### Announce the Rebrand

1. **GitHub Release:**
   ```bash
   git tag v0.3.1-rebrand
   git push origin v0.3.1-rebrand
   ```
   
   Create release with notes:
   ```
   # SeaRei v0.3.1 - Official Rebrand
   
   SafetyEval Mini is now **SeaRei by SeaTechOne LLC**
   
   - Professional enterprise branding
   - Same powerful features
   - Enhanced governance focus
   - Ready for enterprise adoption
   ```

2. **Social Media Announcement:**
   - LinkedIn post about SeaRei launch
   - Twitter announcement
   - Dev.to blog post

3. **Update Website:**
   - Launch seatechone.com/searei
   - Product page
   - Documentation portal
   - Download/installation guide

---

## 📝 Notes

**Repository URL Will Change:**
- Old: `https://github.com/samvardani/safety-eval-mini`
- New: `https://github.com/seatechone/searei` (if transferred to org)

**Clones Will Need Update:**
```bash
# Update remote URL after transfer
git remote set-url origin https://github.com/seatechone/searei.git
```

**Package Name:**
- PyPI package: Will be `searei` (when published)
- Import: May stay `seval` or change to `searei`

---

## 🎯 Recommended: Complete All Steps

**Why:**
- Professional appearance for enterprise sales
- Consistent branding across all channels
- Easier to find and recognize
- SEO benefits (searchable as "SeaRei")

**Timeline:**
- Manual steps: 30-60 minutes
- Organization setup: 1-2 hours
- Full verification: 30 minutes

**Total: 2-3 hours** for complete GitHub rebranding.

---

**Status:** Code rebranding complete ✅  
**Next:** Follow this checklist for GitHub UI updates  
**Goal:** Professional SeaRei brand across all channels  

