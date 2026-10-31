"""Unit tests for CLI flag drift, default value mismatch, and generalized return types."""

from docdrift.drift_detector import DriftDetector
from docdrift.models import DriftSeverity, DriftType


def test_cli_flag_renamed_slide_scenario(tmp_path):
    """Exact scenario from Rishihood Hack Day Problem 5 slide."""
    code_file = tmp_path / "cli.py"
    code_file.write_text(
        "import argparse\n"
        "parser = argparse.ArgumentParser()\n"
        "parser.add_argument('--deadline', type=int, default=30, help='Max run deadline in seconds')\n"
    )

    doc_file = tmp_path / "README.md"
    doc_file.write_text(
        "# Job Runner CLI\n\n"
        "## Options\n"
        "Use `--timeout` to stop slow jobs.\n"
    )

    detector = DriftDetector()
    report = detector.analyze(code_path=code_file, docs_path=doc_file)

    assert report.is_clean is False
    assert report.breaking_count >= 1
    issue = next(i for i in report.issues if i.drift_type == DriftType.CLI_FLAG_MISMATCH)
    assert issue.symbol_name == "--timeout"
    assert issue.severity == DriftSeverity.BREAKING
    assert "still references CLI flag `--timeout`" in issue.description


def test_default_value_mismatch(tmp_path):
    """Detects when code default parameter changes without updating doc."""
    code_file = tmp_path / "simulation.py"
    code_file.write_text(
        "def simulate(history, horizon=30, policy=None):\n"
        "    pass\n"
    )

    doc_file = tmp_path / "README.md"
    doc_file.write_text(
        "### `simulate()`\n"
        "| Parameter | Description |\n"
        "| `history` | Past sales history |\n"
        "| `horizon` | Simulation horizon (default: 60) |\n"
    )

    detector = DriftDetector()
    report = detector.analyze(code_path=code_file, docs_path=doc_file)

    assert report.is_clean is False
    issue = next(i for i in report.issues if i.drift_type == DriftType.DEFAULT_VALUE_MISMATCH)
    assert issue.symbol_name == "simulate"
    assert "default is `30`, but documentation states `60`" in issue.description


def test_generalized_return_type_mismatch(tmp_path):
    """Detects return type contradiction across bool, int, dict, list."""
    code_file = tmp_path / "auth.py"
    code_file.write_text(
        "def is_admin(user_id: int) -> bool:\n"
        "    return True\n"
    )

    doc_file = tmp_path / "README.md"
    doc_file.write_text(
        "### `is_admin()`\n"
        "Checks permissions. Returns string status of admin role.\n"
    )

    detector = DriftDetector()
    report = detector.analyze(code_path=code_file, docs_path=doc_file)

    assert report.is_clean is False
    issue = next(i for i in report.issues if i.drift_type == DriftType.RETURN_TYPE_MISMATCH)
    assert issue.symbol_name == "is_admin"
    assert "code returns `bool`" in issue.description
