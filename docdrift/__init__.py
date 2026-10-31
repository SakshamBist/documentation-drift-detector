"""DocDrift: Automated Documentation Drift Detector for Open-Source Projects."""

from docdrift.ast_parser import ASTParser
from docdrift.git_diff import GitDiffParser, GitDiffSummary
from docdrift.markdown_scanner import MarkdownScanner
from docdrift.drift_detector import DriftDetector
from docdrift.llm_evaluator import LLMEvaluator
from docdrift.models import (
    DriftIssue,
    DriftReport,
    CodeSymbol,
    DocSection,
    DriftSeverity,
    DriftType,
)

__version__ = "0.2.0"
__all__ = [
    "ASTParser",
    "GitDiffParser",
    "GitDiffSummary",
    "MarkdownScanner",
    "DriftDetector",
    "LLMEvaluator",
    "DriftIssue",
    "DriftReport",
    "CodeSymbol",
    "DocSection",
    "DriftSeverity",
    "DriftType",
]
