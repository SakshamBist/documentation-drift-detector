"""Core drift detector correlating code symbols, Git PR diffs, and markdown documentation."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from docdrift.ast_parser import ASTParser
from docdrift.git_diff import GitDiffParser, GitDiffSummary
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
    """Detects discrepancies between codebase symbols, Git PR diffs, and markdown documentation."""

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
        diff_text: Optional[str] = None,
        git_range: Optional[str] = None,
    ) -> DriftReport:
        """Analyze code vs documentation, optionally filtering by Git PR diff."""
        symbols_map: Dict[str, CodeSymbol] = self.ast_parser.parse_directory(code_path)
        doc_sections: List[DocSection] = self.markdown_scanner.scan_directory(docs_path)

        # 1. Parse Git diff if provided (or if git_range is specified)
        diff_summary: Optional[GitDiffSummary] = None
        if diff_text:
            diff_summary = GitDiffParser.parse(diff_text)
        elif git_range:
            diff_summary = GitDiffParser.from_git(repo_path=str(code_path), diff_args=git_range)

        # 2. Filter symbols if Git diff mode is active
        diff_mode_active = diff_summary is not None and len(diff_summary.files) > 0
        evaluated_symbols: Dict[str, CodeSymbol] = {}

        if diff_mode_active:
            for name, sym in symbols_map.items():
                if diff_summary.is_line_modified(sym.file_path, sym.line_number, sym.end_line_number):
                    evaluated_symbols[name] = sym
            changed_symbols_count = len(evaluated_symbols)
        else:
            evaluated_symbols = symbols_map
            changed_symbols_count = len(symbols_map)

        issues: List[DriftIssue] = []

        # 3. Correlate symbols with doc sections
        for sym_name, symbol in evaluated_symbols.items():
            pr_diff_chunk = diff_summary.get_diff_snippet_for_line(
                symbol.file_path, symbol.line_number, symbol.end_line_number
            ) if diff_summary else None

            # Handle CLI flags
            if symbol.symbol_type == "cli_flag":
                continue

            matching_sections = [
                sec for sec in doc_sections
                if sym_name in sec.mentioned_symbols or bool(re.search(rf"\b{re.escape(sym_name)}\b", sec.heading, re.IGNORECASE))
            ]

            for sec in matching_sections:
                # 3a. Parameter & Default drift evaluation (LLM + AST fallback)
                issue = self.llm_evaluator.evaluate_drift(
                    symbol=symbol,
                    doc_section=sec,
                    param_diff={},
                    pr_diff_context=pr_diff_chunk,
                )
                if issue:
                    issues.append(issue)

                # 3b. Generalized return type discrepancy check
                return_issue = self._check_return_type_drift(symbol, sec, pr_diff_chunk)
                if return_issue:
                    issues.append(return_issue)

        # 4. Check for documented functions that were deleted from code
        dead_doc_issues = self._check_dead_documentation(symbols_map, doc_sections, diff_summary)
        issues.extend(dead_doc_issues)

        # 5. Check for deleted / obsolete CLI flags mentioned in docs
        cli_drift_issues = self._check_obsolete_cli_flags(symbols_map, doc_sections, diff_summary)
        issues.extend(cli_drift_issues)

        return DriftReport(
            total_symbols_analyzed=len(symbols_map),
            total_docs_analyzed=len(doc_sections),
            diff_mode_active=diff_mode_active,
            changed_symbols_in_diff=changed_symbols_count,
            issues=issues,
        )

    def _check_obsolete_cli_flags(
        self,
        symbols_map: Dict[str, CodeSymbol],
        doc_sections: List[DocSection],
        diff_summary: Optional[GitDiffSummary] = None,
    ) -> List[DriftIssue]:
        """Catch CLI flags documented in README that were deleted/renamed in code."""
        issues: List[DriftIssue] = []
        known_code_flags = {sym.name for sym in symbols_map.values() if sym.symbol_type == "cli_flag"}
        if not known_code_flags:
            return []

        deleted_in_diff: Set[str] = set()
        if diff_summary:
            for fdiff in diff_summary.files.values():
                for dline in fdiff.deleted_lines:
                    match = re.search(r"(--[a-zA-Z0-9_-]+)", dline)
                    if match:
                        deleted_in_diff.add(match.group(1))

        for sec in doc_sections:
            for doc_flag in sec.mentioned_cli_flags:
                if doc_flag not in known_code_flags:
                    if deleted_in_diff and doc_flag not in deleted_in_diff:
                        continue

                    exact_sent = None
                    for line in sec.content.splitlines():
                        if doc_flag in line:
                            exact_sent = line.strip(" `")
                            break

                    issues.append(
                        DriftIssue(
                            symbol_name=doc_flag,
                            file_code="cli.py",
                            file_doc=sec.file_path,
                            line_doc=sec.line_number,
                            severity=DriftSeverity.BREAKING,
                            drift_type=DriftType.CLI_FLAG_MISMATCH,
                            description=(
                                f"Documentation still references CLI flag `{doc_flag}`, "
                                "which does not exist or was renamed in current code."
                            ),
                            exact_doc_sentence=exact_sent,
                            suggested_fix=f"Replace or remove obsolete CLI flag `{doc_flag}` in {sec.file_path}.",
                        )
                    )

        return issues

    def _check_return_type_drift(
        self,
        symbol: CodeSymbol,
        doc_section: DocSection,
        pr_diff_chunk: Optional[str] = None,
    ) -> Optional[DriftIssue]:
        """Generalized return type discrepancy check across Python types."""
        if not symbol.return_type:
            return None

        clean_type = symbol.return_type.strip().lower()
        sec_lower = doc_section.content.lower()

        conflicts = [
            ("dict", ["returns string", "returns str", "returns int", "returns list"]),
            ("list", ["returns string", "returns str", "returns dict", "returns int"]),
            ("bool", ["returns string", "returns dict", "returns int", "returns list"]),
            ("int", ["returns string", "returns str", "returns dict", "returns bool"]),
            ("str", ["returns dict", "returns list", "returns int", "returns bool"]),
        ]

        for code_t, invalid_phrases in conflicts:
            if code_t in clean_type:
                for phrase in invalid_phrases:
                    if phrase in sec_lower:
                        return DriftIssue(
                            symbol_name=symbol.name,
                            file_code=symbol.file_path,
                            file_doc=doc_section.file_path,
                            line_code=symbol.line_number,
                            line_doc=doc_section.line_number,
                            severity=DriftSeverity.WARNING,
                            drift_type=DriftType.RETURN_TYPE_MISMATCH,
                            description=(
                                f"Return type mismatch for `{symbol.name}`: code returns `{symbol.return_type}`, "
                                f"but documentation claims it {phrase}."
                            ),
                            exact_code_change=symbol.raw_source,
                            exact_doc_sentence=f"Function documentation claims `{phrase}`",
                            suggested_fix=f"Update return type description to `{symbol.return_type}` in {doc_section.file_path}.",
                            pr_diff_context=pr_diff_chunk,
                        )
        return None

    def _check_dead_documentation(
        self,
        symbols_map: Dict[str, CodeSymbol],
        doc_sections: List[DocSection],
        diff_summary: Optional[GitDiffSummary] = None,
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
                            line_doc=sec.line_number,
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
