"""Core drift detector correlating code symbols and markdown documentation."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Union

from docdrift.ast_parser import ASTParser
from docdrift.llm_evaluator import LLMEvaluator
from docdrift.markdown_scanner import MarkdownScanner
from docdrift.models import (
    CodeSymbol,
    DocSection,
    DriftIssue,
    DriftReport,
    DriftSeverity,
    DriftType,
)


class DriftDetector:
    """Detects discrepancies between codebase symbols and markdown documentation."""

    def __init__(
        self,
        ast_parser: Optional[ASTParser] = None,
        markdown_scanner: Optional[MarkdownScanner] = None,
        llm_evaluator: Optional[LLMEvaluator] = None,
    ):
        self.ast_parser = ast_parser or ASTParser()
        self.markdown_scanner = markdown_scanner or MarkdownScanner()
        self.llm_evaluator = llm_evaluator or LLMEvaluator()

    def analyze(
        self,
        code_path: Union[str, Path],
        docs_path: Union[str, Path],
    ) -> DriftReport:
        """Analyze code files vs documentation files and generate a DriftReport."""
        symbols_map: Dict[str, CodeSymbol] = self.ast_parser.parse_directory(code_path)
        doc_sections: List[DocSection] = self.markdown_scanner.scan_directory(docs_path)

        issues: List[DriftIssue] = []

        # Map symbols to sections that mention them
        for sym_name, symbol in symbols_map.items():
            matching_sections = [
                sec for sec in doc_sections
                if sym_name in sec.mentioned_symbols or sym_name.lower() in sec.heading.lower()
            ]

            for sec in matching_sections:
                # 1. Parameter drift evaluation
                issue = self.llm_evaluator.evaluate_drift(
                    symbol=symbol,
                    doc_section=sec,
                    param_diff={},
                )
                if issue:
                    issues.append(issue)

                # 2. Return type discrepancy check
                return_issue = self._check_return_type_drift(symbol, sec)
                if return_issue:
                    issues.append(return_issue)

        # 3. Check for documented symbols that no longer exist in code
        dead_doc_issues = self._check_dead_documentation(symbols_map, doc_sections)
        issues.extend(dead_doc_issues)

        return DriftReport(
            total_symbols_analyzed=len(symbols_map),
            total_docs_analyzed=len(doc_sections),
            issues=issues,
        )

    def _check_return_type_drift(
        self,
        symbol: CodeSymbol,
        doc_section: DocSection,
    ) -> Optional[DriftIssue]:
        """Check if documented return type contradicts code annotation."""
        if not symbol.return_type:
            return None

        sec_lower = doc_section.content.lower()
        # If code returns dict/list/tuple but doc says returns string or int
        if "dict" in symbol.return_type.lower() and "returns string" in sec_lower:
            return DriftIssue(
                symbol_name=symbol.name,
                file_code=symbol.file_path,
                file_doc=doc_section.file_path,
                severity=DriftSeverity.WARNING,
                drift_type=DriftType.RETURN_TYPE_MISMATCH,
                description=(
                    f"Return type mismatch for `{symbol.name}`: code returns `{symbol.return_type}`, "
                    f"but documentation claims it returns `string`."
                ),
                suggested_fix=f"Update return type description to `{symbol.return_type}` in {doc_section.file_path}.",
            )
        return None

    def _check_dead_documentation(
        self,
        symbols_map: Dict[str, CodeSymbol],
        doc_sections: List[DocSection],
    ) -> List[DriftIssue]:
        """Identify functions documented in guides that were deleted from code."""
        dead_issues: List[DriftIssue] = []
        known_code_symbols = set(symbols_map.keys())

        for sec in doc_sections:
            func_in_heading = re.search(r"`([a-zA-Z_][a-zA-Z0-9_]*)(?:\(\))?`", sec.heading)
            if func_in_heading:
                func_name = func_in_heading.group(1)
                if func_name not in known_code_symbols and len(sec.documented_params) > 0:
                    dead_issues.append(
                        DriftIssue(
                            symbol_name=func_name,
                            file_code="<deleted>",
                            file_doc=sec.file_path,
                            severity=DriftSeverity.BREAKING,
                            drift_type=DriftType.DEPRECATED_STILL_DOCUMENTED,
                            description=(
                                f"Symbol `{func_name}` is documented with parameters in {sec.heading}, "
                                "but cannot be found in the current codebase."
                            ),
                            suggested_fix=f"Remove or archive documentation for deprecated symbol `{func_name}`.",
                        )
                    )
        return dead_issues
