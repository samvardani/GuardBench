"""Tests for the Click CLI."""

from __future__ import annotations

import json
import pathlib

import pytest
from click.testing import CliRunner

from guardbench.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_help_exits_zero(runner):
    """guardbench --help should exit 0."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0, result.output


def test_compare_help(runner):
    """guardbench compare --help should exit 0."""
    result = runner.invoke(cli, ["compare", "--help"])
    assert result.exit_code == 0


def test_report_help(runner):
    """guardbench report --help should exit 0."""
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0


def test_gate_help(runner):
    """guardbench gate --help should exit 0."""
    result = runner.invoke(cli, ["gate", "--help"])
    assert result.exit_code == 0


def test_runs_list_empty_store(runner, tmp_path):
    """runs list on an empty store should exit 0."""
    db = tmp_path / "test.db"
    result = runner.invoke(cli, ["runs", "list", "--store", str(db)])
    assert result.exit_code == 0


def test_init_creates_files(runner, tmp_path):
    """init should create config.yaml and gate.json."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0, result.output
        assert pathlib.Path("config.yaml").exists()
        assert pathlib.Path("gate.json").exists()


def test_compare_end_to_end(runner, tmp_path):
    """Full compare command should succeed and print a run ID."""
    builtin = (
        pathlib.Path(__file__).parent.parent.parent
        / "guardbench" / "data" / "builtin" / "sample_10.jsonl"
    )
    db = tmp_path / "test.db"
    result = runner.invoke(cli, [
        "compare",
        "--baseline", "regex",
        "--candidate", "regex",
        "--dataset", str(builtin),
        "--store", str(db),
    ])
    assert result.exit_code == 0, result.output
    assert "Run ID:" in result.output
