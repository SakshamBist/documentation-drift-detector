"""Unit tests for failure cases: malformed markdown, Ollama errors, and false-positive guards."""

from unittest.mock import patch, MagicMock
import requests

from docdrift.drift_detector import DriftDetector
from docdrift.llm_evaluator import LLMEvaluator
from docdrift.models import CodeSymbol, DocSection, ParameterInfo, DriftType


def test_malformed_markdown_handling(tmp_path):
    """Ensure scanner does not crash on broken markdown, missing pipes, or raw unicode."""
    malformed_doc = tmp_path / "broken.md"
    malformed_doc.write_text(
        "# Broken Guide\n"
        "| Parameter | Description\n"  # missing closing pipe
        "| `timeout` \n"               # missing column
        "```python\n"                 # unclosed code block
        "def broken(\n"
        "\x00\x01\x02\n"              # control chars
    )

    code_file = tmp_path / "app.py"
    code_file.write_text("def run(timeout: int): pass\n")

    detector = DriftDetector()
    report = detector.analyze(code_path=code_file, docs_path=malformed_doc)
    assert isinstance(report.issues, list)


def test_ollama_offline_uses_heuristic_fallback():
    """Ensure offline Ollama server gracefully uses deterministic fallback without exception."""
    evaluator = LLMEvaluator(ollama_host="http://localhost:99999", timeout_seconds=1)

    sym = CodeSymbol(
        name="fetch_data",
        file_path="fetch.py",
        line_number=5,
        parameters=[ParameterInfo(name="url")],
    )
    doc_sec = DocSection(
        file_path="README.md",
        heading="fetch_data",
        line_number=10,
        content="| Parameter | Description |\n| `url` | target |\n| `timeout` | ghost |",
        documented_params={"url": "target", "timeout": "ghost"},
    )

    issue = evaluator.evaluate_drift(sym, doc_sec)
    assert issue is not None
    assert issue.drift_type == DriftType.PARAM_MISMATCH
    assert "timeout" in issue.description


def test_ollama_invalid_json_retry_and_recovery():
    """Ensure invalid JSON or bad enum response from model retries and falls back safely."""
    evaluator = LLMEvaluator(timeout_seconds=2)

    sym = CodeSymbol(
        name="do_work",
        file_path="work.py",
        line_number=1,
        parameters=[ParameterInfo(name="task")],
    )
    doc_sec = DocSection(
        file_path="README.md",
        heading="do_work",
        line_number=1,
        content="| Parameter | Description |\n| `task` | current task |",
        documented_params={"task": "current task"},
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "INVALID JSON GIBBERISH"}

    with patch("requests.post", return_value=mock_resp):
        issue = evaluator.evaluate_drift(sym, doc_sec)
        # Should gracefully return None because docs match code
        assert issue is None


def test_false_positive_guard_private_functions(tmp_path):
    """Private helpers and internal refactoring must NOT trigger false alarms."""
    code_file = tmp_path / "internal.py"
    code_file.write_text(
        "def _private_calculator(a, b, c, debug=True):\n"
        "    return a + b + c\n\n"
        "# Comment mentioning parameter: timeout_secs\n"
        "def public_api(query: str):\n"
        "    return _private_calculator(1, 2, 3)\n"
    )

    doc_file = tmp_path / "README.md"
    doc_file.write_text(
        "### `public_api()`\n"
        "| Parameter | Description |\n"
        "| `query` | Search query |\n"
    )

    detector = DriftDetector()
    report = detector.analyze(code_path=code_file, docs_path=doc_file)

    # ZERO false positives: private function ignored, comment ignored
    assert report.is_clean is True
    assert len(report.issues) == 0
