"""Unit tests for DocDrift CLI."""

import subprocess
import sys
from pathlib import Path


def test_cli_help():
    cmd = [sys.executable, "-m", "docdrift.cli", "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "DocDrift: Automated Documentation Drift Detector" in result.stdout


def test_cli_breaking_drift_exits_one():
    base = Path(__file__).parent.parent / "examples" / "scenario_1_param_rename"
    cmd = [
        sys.executable,
        "-m",
        "docdrift.cli",
        "check",
        "--code",
        str(base / "client.py"),
        "--docs",
        str(base / "README.md"),
        "--fail-on-breaking",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 1
    assert "BREAKING: connect_to_database" in result.stdout
    assert "Suggested Fix" in result.stdout


def test_cli_json_format():
    base = Path(__file__).parent.parent / "examples" / "scenario_1_param_rename"
    cmd = [
        sys.executable,
        "-m",
        "docdrift.cli",
        "check",
        "--code",
        str(base / "client.py"),
        "--docs",
        str(base / "README.md"),
        "--format",
        "json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert '"symbol_name": "connect_to_database"' in result.stdout
