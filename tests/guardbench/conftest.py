"""Shared fixtures for GuardBench tests."""

from __future__ import annotations

import pathlib

import pytest

# Resolve builtin fixture path
_BUILTIN = pathlib.Path(__file__).parent.parent.parent / "guardbench" / "data" / "builtin"


@pytest.fixture
def sample_records():
    """Load the built-in 10-row JSONL fixture."""
    from guardbench.data.loader import load_dataset
    return load_dataset(_BUILTIN / "sample_10.jsonl")


@pytest.fixture
def tmp_db(tmp_path):
    """Return a SQLiteStore in a temp directory."""
    from guardbench.store.sqlite import SQLiteStore
    return SQLiteStore(db_path=tmp_path / "test.db")


@pytest.fixture
def regex_baseline():
    """Return a RegexGuard with 'baseline' profile."""
    from guardbench.guards.regex_guard import RegexGuard
    return RegexGuard(profile="baseline")


@pytest.fixture
def regex_enhanced():
    """Return a RegexGuard with 'enhanced' profile."""
    from guardbench.guards.regex_guard import RegexGuard
    return RegexGuard(profile="enhanced")
