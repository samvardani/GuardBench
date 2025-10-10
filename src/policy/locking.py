"""Policy write locking to prevent concurrent modifications."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import portalocker
except ImportError:
    portalocker = None
    logger.warning("portalocker not installed - policy locking disabled")


class PolicyWriteLock:
    """File-based lock for policy writes.
    
    Prevents concurrent policy writes and git races using OS file locks.
    """
    
    def __init__(self, lock_path: Path, timeout: float = 30.0):
        """Initialize policy write lock.
        
        Args:
            lock_path: Path to lock file
            timeout: Lock timeout in seconds
        """
        self.lock_path = lock_path
        self.timeout = timeout
        self.lock_file: Optional[object] = None
        
        # Ensure lock directory exists
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
    
    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire lock.
        
        Args:
            timeout: Optional timeout override
            
        Returns:
            True if lock acquired, False if timeout
            
        Raises:
            RuntimeError: If portalocker not available
        """
        if portalocker is None:
            logger.warning("portalocker not available - lock not acquired")
            return True  # Allow operation without lock
        
        timeout = timeout if timeout is not None else self.timeout
        
        start = time.time()
        
        try:
            # Open lock file
            self.lock_file = open(self.lock_path, "w")
            
            # Try to acquire lock with timeout
            portalocker.lock(
                self.lock_file,
                portalocker.LOCK_EX | portalocker.LOCK_NB  # Exclusive, non-blocking
            )
            
            logger.info(f"Policy write lock acquired: {self.lock_path}")
            return True
        
        except portalocker.LockException:
            # Lock is held, try with timeout
            elapsed = 0.0
            
            while elapsed < timeout:
                try:
                    portalocker.lock(
                        self.lock_file,
                        portalocker.LOCK_EX | portalocker.LOCK_NB
                    )
                    
                    logger.info(f"Policy write lock acquired after {elapsed:.2f}s")
                    return True
                
                except portalocker.LockException:
                    # Still locked, sleep and retry
                    time.sleep(0.1)
                    elapsed = time.time() - start
            
            # Timeout
            logger.warning(f"Policy write lock timeout after {timeout}s")
            
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            
            return False
    
    def release(self) -> None:
        """Release lock."""
        if self.lock_file:
            try:
                if portalocker is not None:
                    portalocker.unlock(self.lock_file)
                
                self.lock_file.close()
                logger.info("Policy write lock released")
            
            except Exception as e:
                logger.error(f"Error releasing lock: {e}")
            
            finally:
                self.lock_file = None
    
    def __enter__(self):
        """Context manager entry."""
        if not self.acquire():
            raise TimeoutError(f"Failed to acquire policy lock within {self.timeout}s")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
        return False


@contextmanager
def with_policy_lock(policy_path: Path, timeout: float = 30.0):
    """Context manager for policy write lock.
    
    Args:
        policy_path: Policy file path
        timeout: Lock timeout
        
    Yields:
        PolicyWriteLock instance
        
    Raises:
        TimeoutError: If lock cannot be acquired
    """
    lock_path = policy_path.parent / f".{policy_path.name}.lock"
    lock = PolicyWriteLock(lock_path=lock_path, timeout=timeout)
    
    with lock:
        yield lock


__all__ = ["PolicyWriteLock", "with_policy_lock"]

