"""Unit tests for Git PR Diff parser and symbol filtering."""

from docdrift.git_diff import GitDiffParser
from docdrift.models import CodeSymbol, ParameterInfo
from docdrift.drift_detector import DriftDetector


SAMPLE_PR_DIFF = """diff --git a/client.py b/client.py
index 1111111..2222222 100644
--- a/client.py
+++ b/client.py
@@ -3,3 +3,3 @@
-def connect_to_database(host, timeout_secs=30):
+def connect_to_database(host, timeout_ms=30000):
     pass
"""

def test_parse_unified_diff():
    summary = GitDiffParser.parse(SAMPLE_PR_DIFF)
    assert "client.py" in summary.files
    fdiff = summary.files["client.py"]
    assert len(fdiff.hunks) == 1
    assert fdiff.touches_line(3) is True
    assert fdiff.touches_line(50) is False


def test_diff_filters_unchanged_symbols(tmp_path):
    code_file = tmp_path / "service.py"
    code_file.write_text(
        "def unchanged_func(a, b):\n"
        "    pass\n\n"
        "def changed_func(x, new_param=True):\n"
        "    pass\n"
    )

    doc_file = tmp_path / "README.md"
    doc_file.write_text(
        "### `unchanged_func()`\n"
        "| Parameter | Description |\n"
        "| `a` | first |\n"
        "| `old_param` | ghost param |\n\n"
        "### `changed_func()`\n"
        "| Parameter | Description |\n"
        "| `x` | first |\n"
        "| `old_param` | ghost param |\n"
    )

    diff_text = """diff --git a/service.py b/service.py
index 1111111..2222222 100644
--- a/service.py
+++ b/service.py
@@ -4,2 +4,2 @@
-def changed_func(x, old_param=False):
+def changed_func(x, new_param=True):
     pass
"""

    detector = DriftDetector()
    report = detector.analyze(code_path=code_file, docs_path=doc_file, diff_text=diff_text)

    assert report.diff_mode_active is True
    assert report.changed_symbols_in_diff == 1
    # Only changed_func should be reported, unchanged_func was NOT touched in the PR diff!
    assert len(report.issues) == 1
    assert report.issues[0].symbol_name == "changed_func"
