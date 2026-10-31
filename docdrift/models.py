"""Data models for DocDrift Documentation Drift Detector."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DriftSeverity(str, Enum):
    """Severity levels for documentation drift."""
    BREAKING = "BREAKING"     # e.g., argument removed, renamed, or CLI flag deleted
    WARNING = "WARNING"       # e.g., return type changed, default value changed
    COSMETIC = "COSMETIC"     # e.g., minor phrasing or formatting discrepancy


class DriftType(str, Enum):
    """Categorized types of drift."""
    PARAM_MISMATCH = "PARAM_MISMATCH"
    CLI_FLAG_MISMATCH = "CLI_FLAG_MISMATCH"
    DEFAULT_VALUE_MISMATCH = "DEFAULT_VALUE_MISMATCH"
    RETURN_TYPE_MISMATCH = "RETURN_TYPE_MISMATCH"
    DEPRECATED_STILL_DOCUMENTED = "DEPRECATED_STILL_DOCUMENTED"
    UNDOCUMENTED_NEW_FEATURE = "UNDOCUMENTED_NEW_FEATURE"
    STALE_CODE_EXAMPLE = "STALE_CODE_EXAMPLE"


class ParameterInfo(BaseModel):
    """Metadata about a function, method, or CLI argument parameter."""
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None
    is_cli_flag: bool = False
    help_text: Optional[str] = None


class CodeSymbol(BaseModel):
    """Representation of an extracted code symbol (function, method, class, CLI flag)."""
    name: str
    symbol_type: str = "function"  # "function", "method", "class", "cli_flag"
    file_path: str
    line_number: int
    end_line_number: Optional[int] = None
    parameters: List[ParameterInfo] = Field(default_factory=list)
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    raw_source: Optional[str] = None

    def param_names(self) -> List[str]:
        return [p.name for p in self.parameters if p.name not in ("self", "cls")]


class DocSection(BaseModel):
    """Representation of a markdown section, CLI usage guide, or parameter table."""
    file_path: str
    heading: str
    line_number: int
    content: str
    code_blocks: List[str] = Field(default_factory=list)
    documented_params: Dict[str, str] = Field(default_factory=dict)
    documented_defaults: Dict[str, str] = Field(default_factory=dict)
    mentioned_symbols: List[str] = Field(default_factory=list)
    mentioned_cli_flags: List[str] = Field(default_factory=list)


class DriftIssue(BaseModel):
    """A detected documentation drift incident."""
    symbol_name: str
    file_code: str
    file_doc: str
    line_code: Optional[int] = None
    line_doc: Optional[int] = None
    severity: DriftSeverity
    drift_type: DriftType
    description: str
    exact_code_change: Optional[str] = None
    exact_doc_sentence: Optional[str] = None
    code_snippet: Optional[str] = None
    doc_snippet: Optional[str] = None
    suggested_fix: Optional[str] = None
    pr_diff_context: Optional[str] = None


class DriftReport(BaseModel):
    """Aggregated report of documentation drift across the repository."""
    total_symbols_analyzed: int = 0
    total_docs_analyzed: int = 0
    diff_mode_active: bool = False
    changed_symbols_in_diff: int = 0
    issues: List[DriftIssue] = Field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return len(self.issues) == 0

    @property
    def breaking_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == DriftSeverity.BREAKING)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == DriftSeverity.WARNING)

    def to_markdown(self) -> str:
        """Render report as GitHub Flavored Markdown for PR comments."""
        if self.is_clean:
            return "### ✅ DocDrift: All Documentation is In Sync with Code!\n\nNo documentation drift detected."

        mode_badge = " *(PR Diff Mode: Changed Symbols Only)*" if self.diff_mode_active else ""
        md = [
            f"### ⚠️ DocDrift: Documentation Drift Detected{mode_badge}\n",
            f"**Summary:** Found **{len(self.issues)} drift issues** "
            f"({self.breaking_count} Critical/Breaking, {self.warning_count} Warnings).\n",
            "| Severity | Drift Type | Symbol | Code Location | Doc Location | Description |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        for issue in self.issues:
            badge = "🔴 BREAKING" if issue.severity == DriftSeverity.BREAKING else "🟡 WARNING"
            code_loc = f"`{issue.file_code}:{issue.line_code}`" if issue.line_code else f"`{issue.file_code}`"
            doc_loc = f"`{issue.file_doc}:{issue.line_doc}`" if issue.line_doc else f"`{issue.file_doc}`"
            md.append(
                f"| **{badge}** | `{issue.drift_type.value}` | `{issue.symbol_name}` | "
                f"{code_loc} | {doc_loc} | {issue.description} |"
            )

        md.append("\n#### Suggested Documentation Fixes:\n")
        for i, issue in enumerate(self.issues, 1):
            if issue.suggested_fix:
                md.append(f"**Issue {i}: `{issue.symbol_name}`**")
                if issue.exact_code_change:
                    md.append(f"> **PR Code Change:** `{issue.exact_code_change}`")
                if issue.exact_doc_sentence:
                    md.append(f"> **Outdated Doc Sentence:** *\"{issue.exact_doc_sentence}\"*")
                md.append(f"```suggestion\n{issue.suggested_fix}\n```\n")

        return "\n".join(md)
