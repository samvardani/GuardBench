#!/usr/bin/env python3
"""Static scanner for stray os.getenv() calls.

Scans source code for direct os.getenv() calls that bypass centralized config.
All environment reads should go through config.get_config() instead.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import List, Tuple


class EnvCallVisitor(ast.NodeVisitor):
    """AST visitor to find os.getenv() calls."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[Tuple[int, str]] = []
    
    def visit_Call(self, node: ast.Call):
        """Visit function call nodes."""
        # Check for os.getenv()
        if isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
                and node.func.attr == "getenv"
            ):
                # Found os.getenv() call
                line = node.lineno
                
                # Get the key being accessed
                if node.args:
                    key_node = node.args[0]
                    if isinstance(key_node, ast.Constant):
                        key = key_node.value
                    else:
                        key = "<dynamic>"
                else:
                    key = "<unknown>"
                
                self.violations.append((line, key))
        
        # Continue visiting
        self.generic_visit(node)


def scan_file(file_path: Path) -> List[Tuple[int, str]]:
    """Scan a Python file for os.getenv() calls.
    
    Args:
        file_path: Path to Python file
        
    Returns:
        List of (line_number, env_key) tuples
    """
    try:
        with open(file_path, "r") as f:
            source = f.read()
        
        tree = ast.parse(source, filename=str(file_path))
        visitor = EnvCallVisitor(str(file_path))
        visitor.visit(tree)
        
        return visitor.violations
    
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}", file=sys.stderr)
        return []
    
    except Exception as e:
        print(f"Error scanning {file_path}: {e}", file=sys.stderr)
        return []


def scan_directory(directory: Path, exclude_patterns: List[str] = None) -> dict:
    """Scan directory for os.getenv() calls.
    
    Args:
        directory: Directory to scan
        exclude_patterns: List of patterns to exclude
        
    Returns:
        Dictionary mapping file paths to violations
    """
    if exclude_patterns is None:
        exclude_patterns = [
            "*/test_*",
            "*/__pycache__/*",
            "*/.venv/*",
            "*/venv/*",
            "*/.pytest_cache/*",
        ]
    
    violations = {}
    
    # Find all Python files
    for py_file in directory.rglob("*.py"):
        # Skip excluded patterns
        skip = False
        for pattern in exclude_patterns:
            if py_file.match(pattern):
                skip = True
                break
        
        if skip:
            continue
        
        # Scan file
        file_violations = scan_file(py_file)
        
        if file_violations:
            violations[py_file] = file_violations
    
    return violations


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Scan for stray os.getenv() calls"
    )
    parser.add_argument(
        "path",
        type=Path,
        default=Path("src"),
        nargs="?",
        help="Path to scan (default: src/)"
    )
    parser.add_argument(
        "--allow-config",
        action="store_true",
        help="Allow os.getenv() in config.py"
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        help="Additional patterns to exclude"
    )
    
    args = parser.parse_args()
    
    # Set up exclusions
    exclude_patterns = [
        "*/test_*",
        "*/__pycache__/*",
        "*/.venv/*",
        "*/venv/*",
        "*/.pytest_cache/*",
    ]
    
    if args.allow_config:
        exclude_patterns.append("*/config.py")
    
    if args.exclude:
        exclude_patterns.extend(args.exclude)
    
    # Scan
    print(f"Scanning {args.path} for os.getenv() calls...")
    print(f"Excluding: {', '.join(exclude_patterns)}")
    print()
    
    violations = scan_directory(args.path, exclude_patterns)
    
    # Report
    if not violations:
        print("✅ No stray os.getenv() calls found!")
        return 0
    
    print(f"❌ Found {len(violations)} file(s) with stray os.getenv() calls:")
    print()
    
    total_violations = 0
    for file_path, file_violations in sorted(violations.items()):
        print(f"{file_path}:")
        for line, key in file_violations:
            print(f"  Line {line}: os.getenv({key!r})")
            total_violations += 1
        print()
    
    print(f"Total violations: {total_violations}")
    print()
    print("⚠️  All environment reads should use config.get_config() instead!")
    
    return 1


if __name__ == "__main__":
    sys.exit(main())

