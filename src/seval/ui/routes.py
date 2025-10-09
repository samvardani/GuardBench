"""FastAPI routes for Policy Management UI."""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader

from .models import PolicyModel, PolicyUpdateRequest, TestRequest, TestResponse
from policy.schema import validate_policy, PolicyValidationError
from guards.candidate import predict as candidate_predict

logger = logging.getLogger(__name__)

# Router setup
router = APIRouter(prefix="/ui", tags=["ui"])

# Template setup
ROOT_DIR = Path(__file__).resolve().parents[3]
UI_TEMPLATE_DIR = ROOT_DIR / "templates" / "ui"
UI_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

_env = Environment(loader=FileSystemLoader(UI_TEMPLATE_DIR))

# Policy path
POLICY_PATH = ROOT_DIR / "policy" / "policy.yaml"


def _load_policy_yaml() -> Dict[str, Any]:
    """Load policy YAML from disk."""
    with open(POLICY_PATH, "r") as f:
        return yaml.safe_load(f)


def _save_policy_yaml(content: str) -> None:
    """Save policy YAML to disk with git commit."""
    # Parse and validate
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")
    
    # Validate with Pydantic
    try:
        PolicyModel(**data)
    except Exception as e:
        raise ValueError(f"Policy validation failed: {e}")
    
    # Additional validation with schema
    try:
        validate_policy(data)
    except PolicyValidationError as e:
        raise ValueError(f"Policy schema validation failed: {e}")
    
    # Write to disk
    with open(POLICY_PATH, "w") as f:
        f.write(content)
    
    # Git commit
    _git_commit_policy()
    
    # Reload policy cache
    _reload_policy_cache()


def _git_commit_policy() -> None:
    """Commit policy changes to git."""
    try:
        subprocess.run(
            ["git", "add", str(POLICY_PATH)],
            cwd=ROOT_DIR,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "feat(policy): update policy via UI"],
            cwd=ROOT_DIR,
            check=False,  # Don't fail if nothing to commit
            capture_output=True,
        )
        logger.info("Policy changes committed to git")
    except Exception as e:
        logger.warning(f"Failed to commit policy to git: {e}")


def _reload_policy_cache() -> None:
    """Reload policy cache after changes."""
    try:
        from policy import policy_cache
        if hasattr(policy_cache, "reload"):
            policy_cache.reload()
        logger.info("Policy cache reloaded")
    except Exception as e:
        logger.warning(f"Failed to reload policy cache: {e}")


@router.get("/", response_class=HTMLResponse)
async def ui_home(request: Request) -> HTMLResponse:
    """Render the main policy management UI."""
    try:
        policy_data = _load_policy_yaml()
        policy_yaml = yaml.dump(policy_data, default_flow_style=False, sort_keys=False)
        
        template = _env.get_template("policy_ui.html")
        html = template.render(
            policy_yaml=policy_yaml,
            policy_version=policy_data.get("version", "unknown"),
            num_slices=len(policy_data.get("slices", [])),
        )
        return HTMLResponse(content=html)
    except Exception as e:
        logger.error(f"Failed to load policy UI: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load UI: {e}")


@router.get("/policies", response_class=JSONResponse)
async def get_policies() -> JSONResponse:
    """Get current policy as JSON."""
    try:
        policy_data = _load_policy_yaml()
        return JSONResponse(content=policy_data)
    except Exception as e:
        logger.error(f"Failed to load policies: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load policies: {e}")


@router.post("/policies", response_class=JSONResponse)
async def update_policy(request: PolicyUpdateRequest) -> JSONResponse:
    """Update policy with validation and git commit."""
    try:
        _save_policy_yaml(request.yaml_content)
        return JSONResponse(
            content={
                "success": True,
                "message": "Policy updated successfully",
            }
        )
    except ValueError as e:
        logger.warning(f"Policy validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update policy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update policy: {e}")


@router.get("/test", response_class=HTMLResponse)
async def test_ui(request: Request) -> HTMLResponse:
    """Render the policy test UI."""
    try:
        template = _env.get_template("test_ui.html")
        html = template.render()
        return HTMLResponse(content=html)
    except Exception as e:
        logger.error(f"Failed to load test UI: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load UI: {e}")


@router.post("/test", response_class=JSONResponse)
async def run_test(request: TestRequest) -> JSONResponse:
    """Run a quick test with the current policy."""
    try:
        start_time = time.perf_counter()
        
        # Get current policy version
        policy_data = _load_policy_yaml()
        policy_version = f"v{policy_data.get('version', 'unknown')}"
        
        # Run prediction
        result = candidate_predict(
            text=request.text,
            category=request.category,
            language=request.language,
        )
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        return JSONResponse(
            content={
                "score": result.get("score", 0.0),
                "blocked": result.get("blocked", False),
                "category": request.category,
                "language": request.language,
                "latency_ms": latency_ms,
                "policy_version": policy_version,
            }
        )
    except Exception as e:
        logger.error(f"Failed to run test: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {e}")

