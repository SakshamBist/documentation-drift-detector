"""Unit tests for DocDrift AutoFixer engine."""

import shutil
from pathlib import Path
from docdrift.auto_fixer import AutoFixer
from docdrift.drift_detector import DriftDetector


def test_auto_fix_param_rename(tmp_path: Path):
    # Setup temporary test scenario
    code_file = tmp_path / "client.py"
    doc_file = tmp_path / "README.md"

    code_file.write_text(
        "def connect_to_database(host: str, port: int = 5432, timeout_ms: int = 3000) -> bool:\n    return True\n"
    )
    doc_file.write_text(
        "### `connect_to_database()`\n\n| Parameter | Type | Description |\n| :--- | :--- | :--- |\n| `host` | str | Server |\n| `port` | int | Port |\n| `timeout_secs` | int | Obsolete |\n"
    )

    detector = DriftDetector()
    report = detector.analyze(code_path=code_file, docs_path=doc_file)

    assert not report.is_clean
    assert report.breaking_count == 1

    # Apply AutoFixer
    fixer = AutoFixer()
    results = fixer.fix_issues(report.issues, code_path=str(code_file))

    assert len(results) == 1
    assert results[0][1] == 1  # 1 fixed item

    # Verify drift is 100% eliminated after fix
    new_report = detector.analyze(code_path=code_file, docs_path=doc_file)
    assert new_report.is_clean
    assert "timeout_ms" in doc_file.read_text()
    assert "timeout_secs" not in doc_file.read_text()


def test_auto_fix_return_type_mismatch(tmp_path: Path):
    code_file = tmp_path / "service.py"
    doc_file = tmp_path / "README.md"

    code_file.write_text(
        "from typing import Dict, Any\ndef fetch_user() -> Dict[str, Any]:\n    return {}\n"
    )
    doc_file.write_text(
        "### `fetch_user()`\n\nReturns string representation of user profile.\n"
    )

    detector = DriftDetector()
    report = detector.analyze(code_path=code_file, docs_path=doc_file)
    assert not report.is_clean

    fixer = AutoFixer()
    fixer.fix_issues(report.issues, code_path=str(code_file))

    new_report = detector.analyze(code_path=code_file, docs_path=doc_file)
    assert new_report.is_clean
    assert "`Dict[str, Any]`" in doc_file.read_text()
