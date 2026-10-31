"""DocDrift: Automated Documentation Drift Detector for Open-Source Projects."""

from docdrift.ast_parser import ASTParser
from docdrift.markdown_scanner import MarkdownScanner
from docdrift.drift_detector import DriftDetector
from docdrift.llm_evaluator import LLMEvaluator
from docdrift.auto_fixer import AutoFixer
from docdrift.models import DriftIssue, DriftReport, CodeSymbol, DocSection

__version__ = "0.1.0"
__all__ = [
    "ASTParser",
    "MarkdownScanner",
    "DriftDetector",
    "LLMEvaluator",
    "AutoFixer",
    "DriftIssue",
    "DriftReport",
    "CodeSymbol",
    "DocSection",
]
