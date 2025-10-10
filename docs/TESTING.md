# Testing Guide

Comprehensive testing, coverage, and quality gates for Safety-Eval-Mini.

## Quick Start

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
PYTHONPATH=src MPLBACKEND=Agg pytest -q

# Run with coverage
PYTHONPATH=src pytest --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html
```

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── test_*.py               # Test modules
├── test_helm_chart.py      # Helm chart validation
└── README_HARDENING.md     # Security test docs
```

## Running Tests

### Basic Test Run

```bash
# All tests (quick)
pytest -q

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run specific test
pytest tests/test_policy_validate.py::test_valid_policy

# Run tests matching pattern
pytest -k "policy"
```

### With Coverage

```bash
# Coverage report in terminal
pytest --cov=src --cov-report=term-missing

# HTML coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# JSON coverage (for CI)
pytest --cov=src --cov-report=json

# Fail if coverage < 70%
pytest --cov=src --cov-fail-under=70
```

### Specific Module Coverage

```bash
# Test guards module
pytest tests/test_guards*.py --cov=src/guards

# Test policy module
pytest tests/test_policy*.py --cov=src/policy

# Test service API
pytest tests/test_service*.py tests/test_ops*.py --cov=src/service
```

## Coverage Requirements

**Overall**: 70% minimum (enforced in CI)

**Per-Module Targets**:
- Core modules (guards, policy, evaluation): >= 80%
- Service API: >= 70%
- Utils: >= 60%
- Optional modules (image, adapters): >= 60%

## Quality Gates

### Pre-Commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

**Hooks**:
- Trailing whitespace removal
- End-of-file fixer
- YAML/JSON/TOML validation
- Ruff linting and formatting
- MyPy type checking
- pytest check (on pre-push)

### Static Analysis

**Ruff (Linter + Formatter)**:
```bash
# Check code
ruff check src/ tests/

# Auto-fix
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/
```

**MyPy (Type Checker)**:
```bash
# Type check
mypy src/ --ignore-missing-imports

# Strict mode
mypy src/ --strict --ignore-missing-imports
```

## Test Categories

### Unit Tests

Fast, isolated tests for individual functions/classes:

```bash
# Run only unit tests (fast)
pytest tests/test_policy_validate.py tests/test_json_utils.py -v
```

### Integration Tests

Tests that interact with multiple components:

```bash
# Connector tests
pytest tests/test_connectors*.py

# Service API tests
pytest tests/test_service*.py
```

### E2E Tests

End-to-end tests with full stack:

```bash
# API E2E tests
pytest tests/test_ops_endpoints.py tests/test_cors_and_limits.py
```

### Security Tests (Hardening)

```bash
# Injection detection
pytest tests/test_hardening_injection.py

# Over-defense checks
pytest tests/test_hardening_overdefense.py
```

## Common Test Failures

### 1. Import Errors

**Problem**: `ModuleNotFoundError` or `ImportError`

**Solution**:
```bash
# Set PYTHONPATH
export PYTHONPATH=src
pytest

# Or use pytest with coverage
pytest --cov=src
```

### 2. gRPC Tests Failing

**Problem**: `ModuleNotFoundError: No module named 'grpc_service._cython'`

**Solution**:
```bash
# Reinstall grpcio
pip install --force-reinstall grpcio

# Or skip gRPC tests
pytest --ignore=tests/test_grpc_trailers.py
```

### 3. Matplotlib Backend Errors

**Problem**: `RuntimeError: Invalid DISPLAY variable`

**Solution**:
```bash
# Use non-interactive backend
export MPLBACKEND=Agg
pytest
```

### 4. Database Tests Failing

**Problem**: `sqlite3.OperationalError: no such table`

**Solution**:
```bash
# Initialize database
python -m src.store.init_db

# Or let tests auto-initialize
pytest tests/test_service_db.py
```

### 5. Coverage Below Threshold

**Problem**: `Coverage check failed: total coverage 65% < 70%`

**Solution**:
```bash
# Check which files need tests
coverage report --show-missing

# Add tests for low-coverage modules
pytest --cov=src --cov-report=term-missing | grep -A 20 "TOTAL"
```

## Continuous Integration

### GitHub Actions Workflow

The project uses `.github/workflows/tests.yaml` for CI:

- ✅ Multi-Python version testing (3.11, 3.12, 3.13)
- ✅ Ruff linting
- ✅ MyPy type checking
- ✅ pytest with coverage
- ✅ Coverage threshold enforcement (70%)
- ✅ Helm chart linting
- ✅ Coverage reports uploaded to Codecov

### CI Commands

```bash
# Run locally what CI runs
PYTHONPATH=src MPLBACKEND=Agg pytest tests/ \
  --cov=src \
  --cov-report=term-missing \
  --cov-fail-under=70 \
  --ignore=tests/test_grpc_trailers.py \
  -v
```

## Writing New Tests

### Test File Structure

```python
"""Test module for XYZ functionality."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_data():
    """Fixture for test data."""
    return {"key": "value"}


def test_function_success(sample_data):
    """Test successful case."""
    result = function_under_test(sample_data)
    assert result is not None


def test_function_error():
    """Test error handling."""
    with pytest.raises(ValueError):
        function_under_test(invalid_input)
```

### Using Fixtures

**From conftest.py**:
```python
def test_with_policy(sample_policy_dict):
    """Use shared policy fixture."""
    validate_policy(sample_policy_dict)


def test_with_temp_file(temp_policy_file):
    """Use temporary file fixture."""
    with open(temp_policy_file) as f:
        data = yaml.safe_load(f)
```

### Mocking External Services

```python
from unittest.mock import patch, MagicMock

def test_with_mock():
    """Test with mocked dependency."""
    with patch("module.external_service") as mock_service:
        mock_service.return_value = {"result": "mocked"}
        result = function_that_calls_service()
        assert result["result"] == "mocked"
```

## Coverage Best Practices

### Increasing Coverage

1. **Test Happy Path**: Normal successful execution
2. **Test Error Cases**: Exceptions, invalid inputs
3. **Test Edge Cases**: Empty inputs, nulls, boundaries
4. **Test Branches**: All if/else branches
5. **Test Loops**: Empty, single, multiple iterations

### What to Test

✅ **Test**:
- Public API functions
- Business logic
- Error handling
- Edge cases
- Integration points

❌ **Don't Over-Test**:
- Private methods (test through public API)
- Generated code (grpc_generated/)
- Third-party code
- Simple getters/setters

### Example Test Suite

```python
class TestMyFunction:
    """Test suite for my_function."""
    
    def test_success(self):
        """Test successful execution."""
        assert my_function("valid") == expected
    
    def test_invalid_input(self):
        """Test with invalid input."""
        with pytest.raises(ValueError):
            my_function(None)
    
    def test_edge_case_empty(self):
        """Test with empty input."""
        assert my_function("") == default_value
    
    def test_edge_case_large(self):
        """Test with large input."""
        large_input = "x" * 10000
        result = my_function(large_input)
        assert result is not None
```

## Debugging Tests

### Verbose Output

```bash
# Show print statements
pytest -s

# Very verbose
pytest -vv

# Show locals on failure
pytest -l

# Full traceback
pytest --tb=long
```

### Run Specific Tests

```bash
# Single test file
pytest tests/test_policy_validate.py

# Single test function
pytest tests/test_policy_validate.py::test_valid_policy

# Tests matching pattern
pytest -k "policy and validate"

# Failed tests from last run
pytest --lf

# Failed first, then others
pytest --ff
```

### Using pdb

```python
def test_with_debugger():
    """Test with debugger."""
    import pdb; pdb.set_trace()
    result = complex_function()
    assert result
```

Or use pytest's built-in:
```bash
pytest --pdb  # Drop into pdb on failure
pytest --trace  # Drop into pdb at start
```

## Performance Testing

### Benchmarking

```python
import pytest

def test_performance(benchmark):
    """Benchmark function performance."""
    result = benchmark(expensive_function, args)
    assert result is not None
```

### Load Testing

For API load testing, see:
- `make load-grpc`: gRPC load test with ghz
- Custom load tests with locust/k6

## Test Configuration

### pytest.ini

```ini
[pytest]
markers =
  asyncio: async tests
  timeout: set per-test timeout
  localstack: integration with localstack
  moto: moto-based AWS mocks

addopts = 
  --strict-markers
  --tb=short
  -ra
```

### .coveragerc

```ini
[run]
source = src
omit = */tests/*, */grpc_generated/*

[report]
fail_under = 70.0
show_missing = True
```

### pyproject.toml

```toml
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]

[tool.coverage.report]
fail_under = 70.0
```

## Continuous Improvement

### Coverage Trend

```bash
# Generate coverage badge
coverage-badge -o coverage.svg -f

# Track over time
coverage json
cat coverage.json | jq '.totals.percent_covered'
```

### Weekly Review

1. Check coverage report
2. Identify low-coverage modules
3. Add tests for uncovered lines
4. Review and update test fixtures
5. Refactor brittle tests

## Resources

- pytest documentation: https://docs.pytest.org
- coverage.py: https://coverage.readthedocs.io
- ruff: https://docs.astral.sh/ruff/
- mypy: https://mypy.readthedocs.io
- pre-commit: https://pre-commit.com

## Getting Help

### Test Failures

1. Read the error message carefully
2. Check common failures section above
3. Run with `-vv` for more details
4. Check CI logs if failing only in CI
5. Open an issue with minimal reproduction

### Coverage Questions

1. Check coverage report: `coverage report --show-missing`
2. Look at HTML report: `open htmlcov/index.html`
3. Focus on critical modules first
4. Ask maintainers for guidance

## Example: Adding Tests for New Feature

```bash
# 1. Create test file
touch tests/test_my_feature.py

# 2. Write tests
cat > tests/test_my_feature.py <<EOF
import pytest
from my_module import my_function

def test_my_function():
    assert my_function("input") == "expected"
EOF

# 3. Run tests
pytest tests/test_my_feature.py -v

# 4. Check coverage
pytest tests/test_my_feature.py --cov=src/my_module

# 5. Iterate until coverage >= target
pytest tests/test_my_feature.py --cov=src/my_module --cov-report=term-missing
```

## CI/CD Integration

### Pre-Push Checklist

Before pushing code:

```bash
# 1. Run tests
pytest -q

# 2. Check coverage
pytest --cov=src --cov-fail-under=70

# 3. Run linter
ruff check --fix src/ tests/

# 4. Format code
ruff format src/ tests/

# 5. Type check
mypy src/ --ignore-missing-imports

# Or use pre-commit
pre-commit run --all-files
```

### PR Requirements

All PRs must:
- ✅ Pass all tests in CI
- ✅ Maintain coverage >= 70%
- ✅ Pass ruff linting
- ✅ Pass mypy type checking (warnings OK)
- ✅ Include tests for new features
- ✅ Update documentation

## Troubleshooting

### Tests Pass Locally but Fail in CI

**Common causes**:
- Environment variables not set
- Different Python version
- Missing dependencies
- File paths (use Path, not string concatenation)
- Timezone differences

**Solution**:
```bash
# Match CI environment
docker run -it python:3.13 bash
pip install -r requirements.txt
pytest
```

### Flaky Tests

**Symptoms**: Tests pass sometimes, fail other times

**Common causes**:
- Race conditions
- Timing dependencies
- Shared global state
- Random number generation

**Solution**:
```python
# Add retries for flaky tests
@pytest.mark.flaky(reruns=3)
def test_potentially_flaky():
    ...

# Use deterministic randomness
import random
random.seed(42)
```

### Slow Tests

**Identify slow tests**:
```bash
pytest --durations=10
```

**Speed up**:
- Use fixtures instead of setup/teardown
- Mock expensive operations
- Run in parallel: `pytest -n auto` (requires pytest-xdist)
- Mark slow tests: `@pytest.mark.slow`

## Best Practices

1. **One assertion per test** (when possible)
2. **Clear test names** describing what is tested
3. **Arrange-Act-Assert** pattern
4. **Use fixtures** for shared setup
5. **Mock external dependencies**
6. **Test behavior, not implementation**
7. **Keep tests independent**
8. **Clean up after tests** (use fixtures with yield)
9. **Use parametrize** for similar test cases
10. **Document complex test logic**

## Example Test Suite

```python
"""Comprehensive test suite example."""

import pytest


class TestMyFeature:
    """Test suite for my feature."""
    
    @pytest.fixture
    def setup_data(self):
        """Setup test data."""
        return {"key": "value"}
    
    def test_success_case(self, setup_data):
        """Test successful execution."""
        result = my_feature(setup_data)
        assert result is not None
    
    def test_error_handling(self):
        """Test error is raised for invalid input."""
        with pytest.raises(ValueError, match="Invalid"):
            my_feature(None)
    
    @pytest.mark.parametrize("input,expected", [
        ("a", 1),
        ("b", 2),
        ("c", 3),
    ])
    def test_multiple_inputs(self, input, expected):
        """Test with multiple inputs."""
        assert my_feature(input) == expected
    
    @pytest.mark.asyncio
    async def test_async_function(self):
        """Test async function."""
        result = await my_async_feature()
        assert result is not None
```

---

For CI/CD configuration and automated quality gates, see `.github/workflows/tests.yaml`.

