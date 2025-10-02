import pytest

from src.policy.schema import validate_policy, PolicyValidationError
from src.policy.compiler import compile_policy


def test_validate_policy_success():
    data = {
        "version": 1,
        "slices": [
            {
                "category": "test",
                "language": "en",
                "threshold": 0.5,
                "rules": [
                    {
                        "id": "rule1",
                        "weight": 1.0,
                        "action": "block",
                        "match": {"regex": ["test"]},
                    }
                ],
            }
        ],
    }
    validate_policy(data)
    compiled = compile_policy(data)
    assert compiled.slices[("test", "en")].threshold == 0.5


def test_validate_policy_failure():
    data = {
        "version": 1,
        "slices": [
            {
                "category": "bad",
                "language": "en",
                "threshold": 1.0,
                "rules": [
                    {
                        "id": "missing-match",
                        "weight": 1.0,
                        "action": "block",
                        "match": {},
                    }
                ],
            }
        ],
    }
    with pytest.raises(PolicyValidationError):
        validate_policy(data)
