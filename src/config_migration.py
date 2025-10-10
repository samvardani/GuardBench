"""Migration guide and helper for transitioning to centralized config.

This module provides utilities to help migrate from os.getenv() to centralized config.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple


def find_os_getenv_usage(directory: Path) -> List[Tuple[Path, int, str]]:
    """Find all os.getenv() usage in Python files.
    
    Args:
        directory: Directory to search
        
    Returns:
        List of (file_path, line_number, line_content)
    """
    results = []
    
    for py_file in directory.rglob("*.py"):
        if ".venv" in str(py_file) or "site-packages" in str(py_file):
            continue
            
        try:
            with open(py_file, "r") as f:
                for line_num, line in enumerate(f, 1):
                    if "os.getenv" in line:
                        results.append((py_file, line_num, line.strip()))
        except Exception:
            pass
    
    return results


def suggest_migration(line: str) -> str:
    """Suggest migration from os.getenv() to config.
    
    Args:
        line: Line containing os.getenv()
        
    Returns:
        Suggested replacement
    """
    # Extract env var name and default
    match = re.search(r'os\.getenv\(["\']([^"\']+)["\'](?:,\s*([^)]+))?\)', line)
    
    if not match:
        return "# Could not parse - manual migration needed"
    
    env_var = match.group(1)
    default = match.group(2) if match.group(2) else None
    
    # Convert env var name to config attribute
    # e.g., GRPC_PORT -> grpc_port
    config_attr = env_var.lower()
    
    suggestion = f"config.{config_attr}"
    
    if default:
        suggestion += f"  # Default: {default}"
    
    return f"# Replace with: {suggestion}"


def generate_migration_report(src_dir: str = "src") -> str:
    """Generate migration report.
    
    Args:
        src_dir: Source directory to analyze
        
    Returns:
        Migration report as string
    """
    directory = Path(src_dir)
    usages = find_os_getenv_usage(directory)
    
    report = []
    report.append("=" * 80)
    report.append("CENTRALIZED CONFIG MIGRATION REPORT")
    report.append("=" * 80)
    report.append(f"\nFound {len(usages)} os.getenv() calls to migrate\n")
    
    # Group by file
    by_file: dict[Path, List[Tuple[int, str]]] = {}
    for file_path, line_num, line in usages:
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append((line_num, line))
    
    for file_path in sorted(by_file.keys()):
        report.append(f"\n{file_path}")
        report.append("-" * 80)
        
        for line_num, line in by_file[file_path]:
            report.append(f"  Line {line_num}: {line}")
            report.append(f"    {suggest_migration(line)}")
    
    report.append("\n" + "=" * 80)
    report.append("MIGRATION STEPS")
    report.append("=" * 80)
    report.append("""
1. Add at top of file:
   from config import get_config
   
2. Get config instance (typically in main/startup):
   config = get_config()
   
3. Replace os.getenv() calls:
   Before: port = int(os.getenv("GRPC_PORT", "50051"))
   After:  port = config.grpc_port
   
4. For boolean env vars:
   Before: enabled = os.getenv("FEATURE_ENABLED", "false").lower() in {"1", "true", "yes"}
   After:  enabled = config.feature_enabled
   
5. For secret values:
   Before: token = os.getenv("API_TOKEN")
   After:  token = config.api_token.get_secret_value()  # if SecretStr
   
6. Pass config to functions/classes:
   Before: def my_function():
              host = os.getenv("HOST", "localhost")
   After:  def my_function(config):
              host = config.host
""")
    
    return "\n".join(report)


if __name__ == "__main__":
    print(generate_migration_report())

