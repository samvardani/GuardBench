# Release Notes: v0.3.1 - "Improvements & Integrations"

**Release Date:** 2025-10-09  
**Branch:** `improve/2025-10-seval`  
**Python:** 3.11+ required

---

## 🎯 Overview

This release focuses on **stability improvements**, **viral growth mechanisms**, and **developer experience** enhancements. We've fixed critical bugs, added Slack integration for team collaboration, and modernized the package structure.

## ✨ What's New

### 🤖 Slack Bot Integration (Viral Growth!)
- `/safety-check <text>` - Real-time safety scoring from Slack
- `/safety-report` - Team usage analytics
- `@SafetyBot` mentions for quick checks
- Beautiful block-based UI with emojis (🚨 unsafe, ⚠️ caution, ✅ safe)
- Socket Mode + webhook support
- Full setup guide: `docs/SLACK_INTEGRATION.md`

### 🔧 Critical Bug Fixes
- **Import Paths Fixed**: All `src.*` imports converted to proper package imports
- **Module Shadowing Resolved**: Renamed `src/grpc` → `src/grpc_service` to avoid conflicts with `grpcio`
- **Port Conflicts**: Smart Makefile utility detects port-in-use with helpful solutions
- **gRPC Reflection**: Already implemented (ENABLE_GRPC_REFLECTION=true)
- **Graceful Shutdown**: Already implemented with 5s grace period

### 📦 Dependencies & Infrastructure
- **Python 3.11+ Required**: Modern type hints and performance
- **pyproject.toml**: Migrated from requirements.txt to modern packaging
- **Auto Package Discovery**: No more manual package lists
- **New Dependencies**:
  - `slack-bolt>=1.19.0` - Slack integration
  - `grpcio-reflection>=1.62.0` - gRPC introspection
  - `pydantic>=2.7.0` - Validation
  - `pydantic-settings>=2.2.0` - Config management

### 🛠️ Developer Experience
- **Smart Makefile Targets**:
  - `make serve` - Auto port detection
  - `make stubs` - gRPC stub generation
  - `make run-grpc` - Start gRPC server
  - `make grpc-smoke` - Smoke tests
- **CI/CD Updates**: GitHub Actions use new package structure
- **No PYTHONPATH Required**: Proper package installation

---

## 🐛 Bug Fixes

| Issue | Description | Fix |
|-------|-------------|-----|
| Import Errors | `ModuleNotFoundError: No module named 'src'` | Converted 71 files to package imports |
| gRPC Shadowing | `AttributeError: module 'grpc' has no attribute '__version__'` | Renamed to `grpc_service` |
| Port In Use | `OSError: Address already in use` | Smart Makefile with `lsof` hints |
| Circular Imports | Package initialization issues | Lazy imports in middleware |

---

## 📊 Changes Summary

- **Files Changed:** 90
- **Commits:** 3
- **Lines Added:** ~700
- **Lines Removed:** ~180

### Commit History
1. `bba91de` - Phase 1: Critical bug fixes (import paths, port utility)
2. `0276bbe` - Slack Bot integration for viral growth
3. `1592530` - CI/CD workflow updates

---

## 🚀 Upgrading

### From v0.3.0

```bash
# 1. Pull latest
git pull origin improve/2025-10-seval

# 2. Update dependencies
pip install -e ".[dev]"

# 3. Regenerate gRPC stubs (path changed)
make stubs

# 4. Update imports in custom code
# OLD: from src.seval import sdk
# NEW: from seval import sdk

# 5. Update server start commands
# OLD: python src/grpc/server.py
# NEW: python -m grpc_service.server
```

### Breaking Changes

⚠️ **Import Paths**: All `src.*` imports must be updated
⚠️ **gRPC Directory**: `src/grpc` → `src/grpc_service`
⚠️ **Python Version**: Now requires 3.11+ (was 3.9+)

### Migration Script

```bash
# Auto-fix imports in your code
find . -name "*.py" -type f -exec sed -i '' 's/from src\./from /g' {} +
find . -name "*.py" -type f -exec sed -i '' 's/import src\./import /g' {} +
```

---

## 📚 New Documentation

- `docs/SLACK_INTEGRATION.md` - Complete Slack bot setup guide
- `RELEASE_NOTES_v0.3.1.md` - This file
- Updated `Makefile` with smart utilities

---

## 🔜 Future Work (Deferred to v0.4.0)

These features were planned but deferred for quality:

- [ ] **Policy Management UI** - Web-based YAML editor
- [ ] **Multi-Model Adapters** - OpenAI, Azure, Perspective integration
- [ ] **Monitoring Dashboard** - Real-time metrics visualization  
- [ ] **Image Moderation** - NSFW/violence detection
- [ ] **Kubernetes/Helm** - Cloud-native deployment
- [ ] **Enhanced Test Coverage** - 70%+ coverage goal

**Rationale**: Ship stable foundation first, iterate on features.

---

## 💡 Usage Examples

### Slack Bot

```bash
# Setup
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_SIGNING_SECRET="..."

# Run with FastAPI
uvicorn service.api:app --port 8001

# Or standalone (Socket Mode)
export SLACK_APP_TOKEN="xapp-..."
python -m integrations.slack_app
```

In Slack:
```
/safety-check How to make a weapon
→ 🚨 UNSAFE | Score: 0.99 | Latency: 12ms

/safety-report
→ 📊 Total: 47 | Unsafe: 3 | Caution: 8 | Safe: 36
```

### Smart Port Selection

```bash
# Auto-detect free port
make serve

# Or specify port
PORT=8080 make serve

# If port in use, get helpful hints
# → Try: lsof -ti :3001 | xargs kill -9
```

---

## 🙏 Contributors

- **Saeed M. Vardani** - Release engineering, bug fixes, Slack integration
- **AI Assistant** - Code generation, testing, documentation

---

## 📝 License

MIT License - See LICENSE file

---

## 🔗 Links

- **Documentation**: `docs/`
- **Slack Setup**: `docs/SLACK_INTEGRATION.md`
- **Changelog**: `CHANGELOG.md`
- **Issues**: Create GitHub issue for bugs/features

---

**Next Release (v0.4.0)**: Policy UI, Multi-Model, Monitoring Dashboard  
**ETA**: Q4 2025
