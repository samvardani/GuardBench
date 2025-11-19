#!/usr/bin/env python3
"""
Policy Loader with Checksum Generation
Loads policy.yaml and generates SHA256 checksums for integrity verification
"""
import hashlib
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

# --- Configuration ---
DEFAULT_POLICY_PATH = "policy/policy.yaml"
CHECKSUM_CACHE_TTL = 3600  # 1 hour

# --- Global Cache ---
_policy_cache: Optional[Dict[str, Any]] = None
_checksum_cache: Optional[str] = None
_last_mtime: float = 0
_last_checksum_time: float = 0
_cache_lock = threading.Lock()


def get_policy_path() -> Path:
    """Get the policy file path"""
    # Try environment variable first
    policy_path = os.getenv("POLICY_PATH", DEFAULT_POLICY_PATH)
    
    # If relative, resolve from project root
    if not os.path.isabs(policy_path):
        # Try to find project root
        current = Path(__file__).resolve()
        while current.parent != current:
            if (current / "policy" / "policy.yaml").exists():
                policy_path = str(current / policy_path)
                break
            if (current / policy_path).exists():
                policy_path = str(current / policy_path)
                break
            current = current.parent
    
    return Path(policy_path)


def calculate_file_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file"""
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        # Read in chunks for memory efficiency
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()


def calculate_policy_checksum(policy_dict: Dict[str, Any]) -> str:
    """
    Calculate SHA256 checksum of policy content
    Uses canonical JSON representation for deterministic hashing
    """
    # Convert policy dict to canonical JSON (sorted keys)
    import json
    canonical_json = json.dumps(policy_dict, sort_keys=True, ensure_ascii=False)
    
    # Calculate SHA256
    sha256_hash = hashlib.sha256()
    sha256_hash.update(canonical_json.encode('utf-8'))
    
    return sha256_hash.hexdigest()


def load_policy(force_reload: bool = False) -> Tuple[Dict[str, Any], str]:
    """
    Load policy.yaml with caching based on file modification time
    
    Args:
        force_reload: Force reload even if cache is fresh
    
    Returns:
        Tuple of (policy_dict, checksum)
    """
    global _policy_cache, _checksum_cache, _last_mtime
    
    policy_path = get_policy_path()
    
    if not policy_path.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_path}")
    
    with _cache_lock:
        current_mtime = policy_path.stat().st_mtime
        
        # Check if cache is still valid
        if not force_reload and _policy_cache is not None and current_mtime == _last_mtime:
            return _policy_cache, _checksum_cache  # type: ignore
        
        # Load policy from file
        with open(policy_path, 'r', encoding='utf-8') as f:
            policy = yaml.safe_load(f)
        
        # Calculate checksum
        checksum = calculate_policy_checksum(policy)
        
        # Update cache
        _policy_cache = policy
        _checksum_cache = checksum
        _last_mtime = current_mtime
        
        print(f"✓ Policy loaded: {policy_path}")
        print(f"  Version: {policy.get('version', 'unknown')}")
        print(f"  Checksum: {checksum[:16]}...")
        
        return policy, checksum


def get_policy_checksum(use_file_hash: bool = False) -> str:
    """
    Get the current policy checksum
    
    Args:
        use_file_hash: If True, calculate checksum from file directly (slower but includes comments)
                      If False, use content-based checksum (faster, deterministic)
    
    Returns:
        SHA256 checksum hex string
    """
    global _checksum_cache, _last_checksum_time
    
    if use_file_hash:
        policy_path = get_policy_path()
        
        # Cache file hash for a short time to avoid repeated I/O
        current_time = time.time()
        if _checksum_cache and (current_time - _last_checksum_time) < CHECKSUM_CACHE_TTL:
            return _checksum_cache
        
        checksum = calculate_file_checksum(policy_path)
        _last_checksum_time = current_time
        return checksum
    else:
        # Use content-based checksum (from load_policy)
        _, checksum = load_policy()
        return checksum


def get_policy_metadata() -> Dict[str, Any]:
    """
    Get policy metadata including version, checksum, and last modified time
    
    Returns:
        Dict with metadata
    """
    policy, checksum = load_policy()
    policy_path = get_policy_path()
    
    metadata = {
        "version": policy.get("version", "unknown"),
        "name": policy.get("metadata", {}).get("name", "unknown"),
        "description": policy.get("metadata", {}).get("description", ""),
        "checksum": checksum,
        "checksum_short": checksum[:16],
        "file_path": str(policy_path),
        "last_modified": policy_path.stat().st_mtime,
        "last_modified_iso": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(policy_path.stat().st_mtime)
        ),
        "size_bytes": policy_path.stat().st_size,
    }
    
    # Count rules if available
    if "slices" in policy:
        total_rules = sum(
            len(slice_def.get("rules", []))
            for slice_def in policy["slices"]
        )
        metadata["total_rules"] = total_rules
        metadata["total_slices"] = len(policy["slices"])
    
    return metadata


def validate_policy(policy: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate policy structure
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields
    if "version" not in policy:
        return False, "Missing required field: version"
    
    if "slices" not in policy:
        return False, "Missing required field: slices"
    
    if not isinstance(policy["slices"], list):
        return False, "Field 'slices' must be a list"
    
    # Validate each slice
    for i, slice_def in enumerate(policy["slices"]):
        if "id" not in slice_def:
            return False, f"Slice {i} missing required field: id"
        
        if "category" not in slice_def:
            return False, f"Slice {slice_def['id']} missing required field: category"
        
        if "rules" in slice_def and not isinstance(slice_def["rules"], list):
            return False, f"Slice {slice_def['id']} field 'rules' must be a list"
    
    return True, None


# Auto-load policy on module import
try:
    load_policy()
except Exception as e:
    print(f"⚠ Warning: Could not load policy on module import: {e}")


if __name__ == "__main__":
    # Test the loader
    print("\n🔧 Policy Loader Test\n")
    
    print("1. Loading policy...")
    policy, checksum = load_policy()
    print(f"   ✓ Loaded policy version {policy.get('version')}")
    print(f"   ✓ Checksum: {checksum}")
    
    print("\n2. Getting metadata...")
    metadata = get_policy_metadata()
    for key, value in metadata.items():
        print(f"   {key}: {value}")
    
    print("\n3. Validating policy...")
    is_valid, error = validate_policy(policy)
    if is_valid:
        print("   ✓ Policy is valid")
    else:
        print(f"   ✗ Policy validation failed: {error}")
    
    print("\n4. Testing cache...")
    start = time.perf_counter()
    _, checksum1 = load_policy()
    time1 = time.perf_counter() - start
    
    start = time.perf_counter()
    _, checksum2 = load_policy()
    time2 = time.perf_counter() - start
    
    print(f"   First load:  {time1*1000:.2f}ms")
    print(f"   Cached load: {time2*1000:.2f}ms")
    print(f"   Speedup: {time1/time2:.1f}x")
    print(f"   Checksums match: {checksum1 == checksum2}")
    
    print("\n✅ Policy loader test complete")












