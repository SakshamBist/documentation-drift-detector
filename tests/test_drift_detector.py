"""Unit tests for Drift Detector on example scenarios."""

from pathlib import Path
from docdrift.drift_detector import DriftDetector
from docdrift.models import DriftSeverity, DriftType


def test_scenario_1_param_rename():
    base = Path(__file__).parent.parent / "examples" / "scenario_1_param_rename"
    detector = DriftDetector()
    report = detector.analyze(code_path=base / "client.py", docs_path=base / "README.md")

    assert not report.is_clean
    assert report.breaking_count == 1
    issue = report.issues[0]
    assert issue.symbol_name == "connect_to_database"
    assert issue.severity == DriftSeverity.BREAKING
    assert issue.drift_type == DriftType.PARAM_MISMATCH
    assert "timeout_secs" in issue.description
    assert issue.suggested_fix is not None


def test_scenario_2_return_type_drift():
    base = Path(__file__).parent.parent / "examples" / "scenario_2_return_type_drift"
    detector = DriftDetector()
    report = detector.analyze(code_path=base / "service.py", docs_path=base / "README.md")

    assert not report.is_clean
    assert report.warning_count == 1
    issue = report.issues[0]
    assert issue.symbol_name == "fetch_user_profile"
    assert issue.severity == DriftSeverity.WARNING
    assert issue.drift_type == DriftType.RETURN_TYPE_MISMATCH


def test_scenario_3_removed_argument():
    base = Path(__file__).parent.parent / "examples" / "scenario_3_removed_argument"
    detector = DriftDetector()
    report = detector.analyze(code_path=base / "auth.py", docs_path=base / "README.md")

    assert not report.is_clean
    assert report.breaking_count == 1
    issue = report.issues[0]
    assert issue.symbol_name == "authenticate_user"
    assert "use_ssl" in issue.description


def test_clean_code_no_drift():
    code = """
def greet(name: str) -> str:
    return f"Hello, {name}"
"""
    doc = """
### `greet()`
| Parameter | Description |
| `name` | Person name |
"""
    from docdrift.ast_parser import ASTParser
    from docdrift.markdown_scanner import MarkdownScanner

    parser = ASTParser()
    scanner = MarkdownScanner()

    symbols = {s.name: s for s in parser.parse_source(code)}
    sections = scanner.scan_content(doc)

    detector = DriftDetector()
    issue = detector.llm_evaluator.evaluate_drift(symbols["greet"], sections[0], {})
    assert issue is None
