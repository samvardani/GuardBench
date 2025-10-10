"""Policy storage with write locking and verification."""

from __future__ import annotations

import hashlib
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .locking import with_policy_lock

logger = logging.getLogger(__name__)


class PolicyConflictError(Exception):
    """Raised when policy write conflicts with concurrent modification."""
    pass


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file.
    
    Args:
        file_path: File to hash
        
    Returns:
        Hex digest of SHA-256
    """
    if not file_path.exists():
        return ""
    
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verify_no_external_changes(
    file_path: Path,
    original_hash: str
) -> None:
    """Verify file hasn't been modified externally.
    
    Args:
        file_path: File to check
        original_hash: Original file hash
        
    Raises:
        PolicyConflictError: If file was modified externally
    """
    current_hash = compute_file_hash(file_path)
    
    if current_hash != original_hash:
        raise PolicyConflictError(
            f"Policy file was modified externally. "
            f"Original hash: {original_hash[:8]}, "
            f"current hash: {current_hash[:8]}"
        )


def save_policy_with_lock(
    policy_data: Dict[str, Any],
    policy_path: Path,
    commit_message: str = "Update policy",
    timeout: float = 30.0
) -> None:
    """Save policy with write lock and git commit.
    
    Critical section:
    1. Acquire lock
    2. Write YAML
    3. Git add + commit
    4. Release lock
    
    Args:
        policy_data: Policy configuration
        policy_path: Policy file path
        commit_message: Git commit message
        timeout: Lock timeout in seconds
        
    Raises:
        PolicyConflictError: If lock timeout
    """
    lock_path = policy_path.parent / f".{policy_path.name}.lock"
    
    try:
        # Acquire lock (with timeout)
        with with_policy_lock(policy_path, timeout=timeout):
            logger.info(f"Saving policy with lock")
            
            # Write YAML
            with open(policy_path, "w") as f:
                yaml.safe_dump(policy_data, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Policy written to {policy_path}")
            
            # Git add + commit (atomic within lock)
            try:
                subprocess.run(
                    ["git", "add", str(policy_path)],
                    cwd=policy_path.parent,
                    check=True,
                    capture_output=True
                )
                
                subprocess.run(
                    ["git", "commit", "-m", commit_message],
                    cwd=policy_path.parent,
                    check=True,
                    capture_output=True
                )
                
                logger.info(f"Policy committed: {commit_message}")
            
            except subprocess.CalledProcessError as e:
                logger.warning(f"Git commit failed (may be no changes): {e}")
    
    except TimeoutError:
        logger.error(f"Failed to acquire policy lock within {timeout}s")
        raise PolicyConflictError(
            f"Another policy save is in progress. Please try again in a few seconds."
        )
    
    except Exception as e:
        logger.exception(f"Error saving policy: {e}")
        raise


__all__ = ["save_policy_with_lock", "PolicyConflictError"]

