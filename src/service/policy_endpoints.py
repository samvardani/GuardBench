"""
Policy Customization API Endpoints
Enables users to customize content moderation policies via API
"""

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

# Create router
router = APIRouter(prefix="/policy", tags=["policy"])

# Policy storage path
CUSTOM_POLICIES_DIR = Path("data/custom_policies")
CUSTOM_POLICIES_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CategoryConfig(BaseModel):
    """Category enable/disable configuration"""
    violence: bool = True
    self_harm: bool = True
    sexual: bool = True
    harassment: bool = True
    illegal: bool = True
    spam: bool = False


class ThresholdConfig(BaseModel):
    """Confidence threshold configuration"""
    rules: float = Field(default=0.50, ge=0.0, le=1.0)
    ml: float = Field(default=0.60, ge=0.0, le=1.0)
    transformer: float = Field(default=0.70, ge=0.0, le=1.0)
    ensemble: float = Field(default=0.50, ge=0.0, le=1.0)


class CustomRule(BaseModel):
    """Custom regex rule"""
    id: int
    name: str = Field(min_length=1, max_length=100)
    category: str
    pattern: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)
    action: str = Field(default="flag")  # flag, block, review


class BlocklistItem(BaseModel):
    """Blocklist term"""
    id: float
    term: str = Field(min_length=1, max_length=200)
    case_sensitive: bool = False


class AdvancedConfig(BaseModel):
    """Advanced configuration options"""
    obfuscation: bool = True
    context: bool = True
    multilang: bool = True
    routing: str = "intelligent"
    return_categories: bool = True
    return_explanation: bool = True
    return_patterns: bool = False
    log_requests: bool = False
    log_flagged: bool = True
    webhook_url: Optional[str] = None


class PolicyConfig(BaseModel):
    """Complete policy configuration"""
    version: str = "2.1.0"
    categories: CategoryConfig
    thresholds: ThresholdConfig
    custom_rules: List[CustomRule] = []
    blocklist: List[BlocklistItem] = []
    advanced: AdvancedConfig


class PolicyMetadata(BaseModel):
    """Policy metadata for listing"""
    policy_id: str
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: str
    active: bool = False
    checksum: str


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_policy_id(config: PolicyConfig) -> str:
    """Generate unique policy ID based on content"""
    content = json.dumps(config.dict(), sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def save_policy_to_disk(policy_id: str, config: PolicyConfig, metadata: Dict[str, Any]) -> None:
    """Save policy configuration to disk"""
    policy_file = CUSTOM_POLICIES_DIR / f"{policy_id}.json"
    
    data = {
        "metadata": metadata,
        "config": config.dict()
    }
    
    with open(policy_file, 'w') as f:
        json.dump(data, f, indent=2)


def load_policy_from_disk(policy_id: str) -> Optional[Dict[str, Any]]:
    """Load policy configuration from disk"""
    policy_file = CUSTOM_POLICIES_DIR / f"{policy_id}.json"
    
    if not policy_file.exists():
        return None
    
    with open(policy_file, 'r') as f:
        return json.load(f)


def list_all_policies() -> List[PolicyMetadata]:
    """List all saved policies"""
    policies = []
    
    for policy_file in CUSTOM_POLICIES_DIR.glob("*.json"):
        try:
            with open(policy_file, 'r') as f:
                data = json.load(f)
                metadata = data.get("metadata", {})
                policies.append(PolicyMetadata(**metadata))
        except Exception:
            continue
    
    return sorted(policies, key=lambda p: p.updated_at, reverse=True)


def compile_policy_to_runtime(config: PolicyConfig) -> Dict[str, Any]:
    """Compile policy config into runtime-ready format"""
    # This would integrate with the actual guard system
    # For now, return a structured format
    
    runtime_config = {
        "enabled_categories": [k for k, v in config.categories.dict().items() if v],
        "thresholds": config.thresholds.dict(),
        "custom_patterns": {
            rule.category: {
                "pattern": rule.pattern,
                "confidence": rule.confidence,
                "action": rule.action
            }
            for rule in config.custom_rules
        },
        "blocklist": {
            item.term: {"case_sensitive": item.case_sensitive}
            for item in config.blocklist
        },
        "advanced": config.advanced.dict()
    }
    
    return runtime_config


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/save", response_model=Dict[str, Any])
async def save_policy(config: PolicyConfig, request: Request):
    """
    Save a custom policy configuration
    
    **Request Body:**
    - Complete policy configuration with categories, thresholds, rules, blocklist
    
    **Returns:**
    - policy_id: Unique identifier for the saved policy
    - checksum: SHA256 checksum for verification
    - saved_at: Timestamp of save operation
    """
    try:
        # Generate policy ID
        policy_id = generate_policy_id(config)
        
        # Create metadata
        metadata = {
            "policy_id": policy_id,
            "name": f"Custom Policy {policy_id[:8]}",
            "description": f"Custom policy with {len(config.custom_rules)} rules and {len(config.blocklist)} blocked terms",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "active": False,
            "checksum": policy_id
        }
        
        # Save to disk
        save_policy_to_disk(policy_id, config, metadata)
        
        return {
            "success": True,
            "policy_id": policy_id,
            "checksum": policy_id,
            "saved_at": metadata["updated_at"],
            "message": "Policy saved successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save policy: {str(e)}")


@router.get("/load", response_model=PolicyConfig)
async def load_active_policy():
    """
    Load the currently active policy configuration
    
    **Returns:**
    - Complete policy configuration
    """
    # For now, return default configuration
    # In production, this would load from active policy file
    
    return PolicyConfig(
        version="2.1.0",
        categories=CategoryConfig(),
        thresholds=ThresholdConfig(),
        custom_rules=[],
        blocklist=[],
        advanced=AdvancedConfig()
    )


@router.get("/load/{policy_id}", response_model=PolicyConfig)
async def load_policy_by_id(policy_id: str):
    """
    Load a specific policy by ID
    
    **Path Parameters:**
    - policy_id: Unique policy identifier
    
    **Returns:**
    - Complete policy configuration
    """
    data = load_policy_from_disk(policy_id)
    
    if not data:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return PolicyConfig(**data["config"])


@router.get("/list", response_model=List[PolicyMetadata])
async def list_policies():
    """
    List all saved policy configurations
    
    **Returns:**
    - Array of policy metadata (id, name, timestamps, etc.)
    """
    return list_all_policies()


@router.post("/activate/{policy_id}", response_model=Dict[str, Any])
async def activate_policy(policy_id: str):
    """
    Activate a specific policy for use
    
    **Path Parameters:**
    - policy_id: Unique policy identifier
    
    **Returns:**
    - Success status and activation details
    """
    data = load_policy_from_disk(policy_id)
    
    if not data:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Deactivate all other policies
    for policy in list_all_policies():
        if policy.policy_id != policy_id:
            policy_data = load_policy_from_disk(policy.policy_id)
            if policy_data:
                policy_data["metadata"]["active"] = False
                save_policy_to_disk(policy.policy_id, PolicyConfig(**policy_data["config"]), policy_data["metadata"])
    
    # Activate this policy
    data["metadata"]["active"] = True
    data["metadata"]["updated_at"] = datetime.now().isoformat()
    save_policy_to_disk(policy_id, PolicyConfig(**data["config"]), data["metadata"])
    
    return {
        "success": True,
        "policy_id": policy_id,
        "activated_at": data["metadata"]["updated_at"],
        "message": "Policy activated successfully"
    }


@router.delete("/delete/{policy_id}", response_model=Dict[str, Any])
async def delete_policy(policy_id: str):
    """
    Delete a saved policy
    
    **Path Parameters:**
    - policy_id: Unique policy identifier
    
    **Returns:**
    - Success status
    """
    policy_file = CUSTOM_POLICIES_DIR / f"{policy_id}.json"
    
    if not policy_file.exists():
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Check if active
    data = load_policy_from_disk(policy_id)
    if data and data["metadata"].get("active"):
        raise HTTPException(status_code=400, detail="Cannot delete active policy. Deactivate first.")
    
    policy_file.unlink()
    
    return {
        "success": True,
        "policy_id": policy_id,
        "message": "Policy deleted successfully"
    }


@router.post("/export/{policy_id}")
async def export_policy(policy_id: str):
    """
    Export policy as downloadable JSON
    
    **Path Parameters:**
    - policy_id: Unique policy identifier
    
    **Returns:**
    - Policy configuration as JSON
    """
    data = load_policy_from_disk(policy_id)
    
    if not data:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return data


@router.post("/import", response_model=Dict[str, Any])
async def import_policy(config: PolicyConfig):
    """
    Import a policy configuration
    
    **Request Body:**
    - Complete policy configuration
    
    **Returns:**
    - New policy ID and import status
    """
    try:
        # Generate new policy ID
        policy_id = generate_policy_id(config)
        
        # Check if already exists
        if load_policy_from_disk(policy_id):
            return {
                "success": True,
                "policy_id": policy_id,
                "message": "Policy already exists",
                "duplicate": True
            }
        
        # Create metadata
        metadata = {
            "policy_id": policy_id,
            "name": f"Imported Policy {policy_id[:8]}",
            "description": "Imported custom policy",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "active": False,
            "checksum": policy_id
        }
        
        # Save to disk
        save_policy_to_disk(policy_id, config, metadata)
        
        return {
            "success": True,
            "policy_id": policy_id,
            "message": "Policy imported successfully",
            "duplicate": False
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import policy: {str(e)}")


@router.post("/validate", response_model=Dict[str, Any])
async def validate_policy(config: PolicyConfig):
    """
    Validate a policy configuration without saving
    
    **Request Body:**
    - Policy configuration to validate
    
    **Returns:**
    - Validation results and any errors/warnings
    """
    errors = []
    warnings = []
    
    # Validate thresholds
    if config.thresholds.ensemble < 0.3:
        warnings.append("Very low ensemble threshold may cause high false positive rate")
    if config.thresholds.ensemble > 0.8:
        warnings.append("Very high ensemble threshold may miss unsafe content")
    
    # Validate custom rules
    for rule in config.custom_rules:
        try:
            import re
            re.compile(rule.pattern)
        except re.error as e:
            errors.append(f"Invalid regex in rule '{rule.name}': {str(e)}")
    
    # Validate blocklist
    if len(config.blocklist) > 10000:
        warnings.append("Very large blocklist may impact performance")
    
    # Check for enabled categories
    if not any(config.categories.dict().values()):
        errors.append("At least one category must be enabled")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "enabled_categories": sum(config.categories.dict().values()),
            "custom_rules": len(config.custom_rules),
            "blocklist_size": len(config.blocklist)
        }
    }


@router.get("/presets", response_model=Dict[str, Any])
async def get_presets():
    """
    Get predefined policy presets for different use cases
    
    **Returns:**
    - Dictionary of preset configurations
    """
    presets = {
        "education": {
            "name": "Education (K-12)",
            "description": "Strict filtering for educational environments",
            "config": PolicyConfig(
                categories=CategoryConfig(violence=True, self_harm=True, sexual=True, harassment=True, illegal=True, spam=True),
                thresholds=ThresholdConfig(rules=0.30, ml=0.40, transformer=0.50, ensemble=0.30),
                custom_rules=[],
                blocklist=[],
                advanced=AdvancedConfig(obfuscation=True, context=True)
            )
        },
        "social_media": {
            "name": "Social Media",
            "description": "Balanced filtering for social platforms",
            "config": PolicyConfig(
                categories=CategoryConfig(violence=True, self_harm=True, sexual=True, harassment=True, illegal=True, spam=True),
                thresholds=ThresholdConfig(rules=0.50, ml=0.60, transformer=0.70, ensemble=0.50),
                custom_rules=[],
                blocklist=[],
                advanced=AdvancedConfig()
            )
        },
        "forum": {
            "name": "Adult Forum",
            "description": "Permissive filtering for adult communities",
            "config": PolicyConfig(
                categories=CategoryConfig(violence=True, self_harm=True, sexual=False, harassment=True, illegal=True, spam=True),
                thresholds=ThresholdConfig(rules=0.70, ml=0.80, transformer=0.85, ensemble=0.70),
                custom_rules=[],
                blocklist=[],
                advanced=AdvancedConfig()
            )
        },
        "enterprise": {
            "name": "Enterprise Workspace",
            "description": "Professional content filtering",
            "config": PolicyConfig(
                categories=CategoryConfig(violence=True, self_harm=True, sexual=True, harassment=True, illegal=True, spam=True),
                thresholds=ThresholdConfig(rules=0.40, ml=0.50, transformer=0.60, ensemble=0.40),
                custom_rules=[],
                blocklist=[],
                advanced=AdvancedConfig(log_requests=True, log_flagged=True)
            )
        }
    }
    
    return presets


@router.post("/test", response_model=Dict[str, Any])
async def test_policy(config: PolicyConfig, text: str = Field(..., min_length=1, max_length=10000)):
    """
    Test a policy configuration on sample text
    
    **Request Body:**
    - config: Policy configuration to test
    - text: Sample text to analyze
    
    **Returns:**
    - Moderation result with policy-specific settings applied
    """
    # This would integrate with the actual prediction system
    # For now, return a mock result
    
    # Compile policy
    runtime_config = compile_policy_to_runtime(config)
    
    # Mock prediction (in production, call actual guard)
    result = {
        "prediction": "pass",
        "score": 0.15,
        "method": "policy_test",
        "latency_ms": 2.5,
        "categories": {},
        "explanation": f"Tested with custom policy. Enabled categories: {', '.join(runtime_config['enabled_categories'])}",
        "policy_applied": {
            "enabled_categories": runtime_config["enabled_categories"],
            "thresholds": runtime_config["thresholds"],
            "custom_rules_matched": 0,
            "blocklist_matched": False
        }
    }
    
    return result


# Health check for policy service
@router.get("/health")
async def policy_service_health():
    """Health check for policy customization service"""
    return {
        "status": "healthy",
        "service": "policy_customization",
        "policies_directory": str(CUSTOM_POLICIES_DIR),
        "total_policies": len(list(CUSTOM_POLICIES_DIR.glob("*.json"))),
        "timestamp": datetime.now().isoformat()
    }












