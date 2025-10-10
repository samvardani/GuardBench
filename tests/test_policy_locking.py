"""Tests for policy write locking."""

from __future__ import annotations

import concurrent.futures
import pytest
import time
import yaml
from pathlib import Path

from policy import PolicyWriteLock, with_policy_lock, save_policy_with_lock, PolicyConflictError


class TestPolicyWriteLock:
    """Test PolicyWriteLock."""
    
    @pytest.fixture
    def lock_path(self, tmp_path):
        """Create lock file path."""
        return tmp_path / ".policy.lock"
    
    def test_lock_creation(self, lock_path):
        """Test creating lock."""
        lock = PolicyWriteLock(lock_path=lock_path, timeout=10.0)
        
        assert lock.lock_path == lock_path
        assert lock.timeout == 10.0
    
    def test_acquire_release(self, lock_path):
        """Test acquiring and releasing lock."""
        lock = PolicyWriteLock(lock_path=lock_path)
        
        # Acquire
        acquired = lock.acquire()
        assert acquired is True
        
        # Release
        lock.release()
    
    def test_context_manager(self, lock_path):
        """Test using lock as context manager."""
        with PolicyWriteLock(lock_path=lock_path):
            # Lock is held
            pass
        
        # Lock is released
    
    def test_concurrent_lock_blocks(self, lock_path):
        """Test that second lock is blocked."""
        lock1 = PolicyWriteLock(lock_path=lock_path, timeout=1.0)
        lock2 = PolicyWriteLock(lock_path=lock_path, timeout=1.0)
        
        # Acquire first lock
        lock1.acquire()
        
        # Try to acquire second lock (should timeout)
        acquired = lock2.acquire(timeout=0.5)
        
        assert acquired is False
        
        # Release first lock
        lock1.release()
        
        # Now second lock can acquire
        acquired = lock2.acquire()
        assert acquired is True
        
        lock2.release()
    
    def test_lock_timeout(self, lock_path):
        """Test lock timeout."""
        lock1 = PolicyWriteLock(lock_path=lock_path)
        lock1.acquire()
        
        lock2 = PolicyWriteLock(lock_path=lock_path, timeout=0.5)
        
        # Should timeout
        start = time.time()
        acquired = lock2.acquire()
        elapsed = time.time() - start
        
        assert acquired is False
        assert 0.4 < elapsed < 1.0  # Around 0.5s
        
        lock1.release()


class TestPolicySaveWithLock:
    """Test save_policy_with_lock function."""
    
    @pytest.fixture
    def policy_path(self, tmp_path):
        """Create policy file path."""
        policy_dir = tmp_path / "policy"
        policy_dir.mkdir()
        
        # Initialize git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=policy_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=policy_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=policy_dir, capture_output=True)
        
        return policy_dir / "policy.yaml"
    
    def test_save_policy_success(self, policy_path):
        """Test successful policy save."""
        policy_data = {
            "thresholds": {"violence": 5.0},
            "enabled": True
        }
        
        # Save
        save_policy_with_lock(
            policy_data=policy_data,
            policy_path=policy_path,
            commit_message="Test policy update"
        )
        
        # Verify file exists
        assert policy_path.exists()
        
        # Verify content
        with open(policy_path) as f:
            loaded = yaml.safe_load(f)
        
        assert loaded["thresholds"]["violence"] == 5.0
        assert loaded["enabled"] is True
    
    def test_concurrent_saves_second_conflicts(self, policy_path):
        """Test concurrent saves - second returns conflict."""
        policy_data1 = {"version": 1}
        policy_data2 = {"version": 2}
        
        results = []
        errors = []
        
        def save_with_delay(data, delay, timeout):
            try:
                # Acquire lock with specific timeout
                with with_policy_lock(policy_path, timeout=timeout):
                    # Write
                    with open(policy_path, "w") as f:
                        yaml.safe_dump(data, f)
                    
                    # Simulate slow operation
                    time.sleep(delay)
                    
                    results.append(data["version"])
            
            except Exception as e:
                errors.append(e)
        
        # Run concurrent saves
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # First save (slow, long timeout)
            future1 = executor.submit(save_with_delay, policy_data1, 1.0, 5.0)
            
            # Second save (fast, short timeout - will fail to acquire)
            time.sleep(0.1)  # Ensure first starts and acquires lock first
            future2 = executor.submit(save_with_delay, policy_data2, 0.1, 0.5)
            
            concurrent.futures.wait([future1, future2])
        
        # First should succeed, second should timeout
        assert len(results) == 1  # Only one succeeded
        assert results[0] == 1  # First one succeeded
        assert len(errors) == 1  # One timed out
        assert isinstance(errors[0], TimeoutError)
    
    def test_lock_prevents_concurrent_writes(self, policy_path):
        """Test that lock prevents concurrent writes."""
        # Initial save
        initial_data = {"version": 1}
        with open(policy_path, "w") as f:
            yaml.safe_dump(initial_data, f)
        
        # First save with lock (slow)
        def slow_save():
            with with_policy_lock(policy_path, timeout=5.0):
                time.sleep(0.5)  # Hold lock
                with open(policy_path, "w") as f:
                    yaml.safe_dump({"version": 2}, f)
        
        # Second save attempt (should be blocked)
        def fast_save():
            with with_policy_lock(policy_path, timeout=0.2):
                with open(policy_path, "w") as f:
                    yaml.safe_dump({"version": 3}, f)
        
        # Run concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(slow_save)
            time.sleep(0.1)  # Ensure first starts first
            future2 = executor.submit(fast_save)
            
            # Wait
            concurrent.futures.wait([future1, future2])
            
            # First should succeed, second should timeout
            assert future1.exception() is None  # Success
            assert isinstance(future2.exception(), TimeoutError)  # Blocked


class TestConcurrentSaveScenarios:
    """Test various concurrent save scenarios."""
    
    @pytest.fixture
    def policy_path(self, tmp_path):
        """Create policy path with git."""
        policy_dir = tmp_path / "test_policy"
        policy_dir.mkdir()
        
        import subprocess
        subprocess.run(["git", "init"], cwd=policy_dir, capture_output=True, check=False)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=policy_dir, capture_output=True, check=False)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=policy_dir, capture_output=True, check=False)
        
        return policy_dir / "policy.yaml"
    
    def test_no_file_corruption(self, policy_path):
        """Test that concurrent saves don't corrupt file."""
        num_saves = 10
        save_count = [0]
        conflict_count = [0]
        
        def try_save(version):
            try:
                save_policy_with_lock(
                    policy_data={"version": version},
                    policy_path=policy_path,
                    commit_message=f"Update to v{version}",
                    timeout=2.0
                )
                save_count[0] += 1
            except (PolicyConflictError, TimeoutError):
                conflict_count[0] += 1
        
        # Run concurrent saves
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(try_save, i) for i in range(num_saves)]
            concurrent.futures.wait(futures)
        
        # Some should succeed, some should conflict
        total = save_count[0] + conflict_count[0]
        assert total == num_saves
        
        # At least one should succeed
        assert save_count[0] >= 1
        
        # File should be valid YAML
        if policy_path.exists():
            with open(policy_path) as f:
                data = yaml.safe_load(f)
            
            assert "version" in data
            assert isinstance(data["version"], int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

