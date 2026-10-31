"""Auto-fixer engine to automatically synchronize markdown documentation with code."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from docdrift.ast_parser import ASTParser
from docdrift.models import CodeSymbol, DriftIssue, DriftType


class AutoFixer:
    """Applies automated patches to markdown documentation to resolve drift."""

    def __init__(self, ast_parser: Optional[ASTParser] = None):
        self.ast_parser = ast_parser or ASTParser()

    def fix_issues(
        self,
        issues: List[DriftIssue],
        code_path: str,
        backup: bool = False,
    ) -> List[Tuple[str, int]]:
        """Fix a list of detected drift issues by updating markdown documentation on disk."""
        symbols_map: Dict[str, CodeSymbol] = self.ast_parser.parse_directory(code_path)
        docs_to_issues: Dict[str, List[DriftIssue]] = {}

        for issue in issues:
            docs_to_issues.setdefault(issue.file_doc, []).append(issue)

        results: List[Tuple[str, int]] = []

        for doc_file, doc_issues in docs_to_issues.items():
            p = Path(doc_file)
            if not p.is_file():
                continue

            content = p.read_text(encoding="utf-8", errors="ignore")
            original_content = content
            total_fixed = 0

            for issue in doc_issues:
                symbol = symbols_map.get(issue.symbol_name)
                content, count = self._apply_single_fix(content, issue, symbol)
                total_fixed += count

            if total_fixed > 0 and content != original_content:
                if backup:
                    p.with_suffix(p.suffix + ".bak").write_text(original_content, encoding="utf-8")
                p.write_text(content, encoding="utf-8")
                results.append((doc_file, total_fixed))

        return results

    def _apply_single_fix(
        self,
        content: str,
        issue: DriftIssue,
        symbol: Optional[CodeSymbol],
    ) -> Tuple[str, int]:
        """Apply a patch for a single drift issue to markdown content."""
        if issue.drift_type == DriftType.PARAM_MISMATCH and symbol:
            return self._fix_param_mismatch(content, issue, symbol)

        if issue.drift_type == DriftType.RETURN_TYPE_MISMATCH and symbol:
            return self._fix_return_type_mismatch(content, issue, symbol)

        return content, 0

    def _fix_param_mismatch(
        self,
        content: str,
        issue: DriftIssue,
        symbol: CodeSymbol,
    ) -> Tuple[str, int]:
        """Replace or remove outdated parameter rows in markdown tables and lists."""
        lines = content.splitlines()
        new_lines: List[str] = []
        fixed_count = 0

        code_params = {p.name: p for p in symbol.parameters}
        param_names_in_code = symbol.param_names()

        # Find stale parameters mentioned in issue description
        stale_params_match = re.search(r"parameter\(s\)\s+([^.]+)\s+which do not exist", issue.description)
        stale_params = set()
        if stale_params_match:
            raw_str = stale_params_match.group(1)
            stale_params = {p.strip(" `") for p in raw_str.split(",")}

        for line in lines:
            # Check if this line is a table row defining one of the stale parameters
            row_match = re.match(r"^(\|\s*`?([a-zA-Z_][a-zA-Z0-9_]*)`?\s*\|\s*)([^|]+)(\|.*)$", line)
            bullet_match = re.match(r"^(\s*[-*]\s+`?([a-zA-Z_][a-zA-Z0-9_]*)`?\s*[:\-]\s*)(.*)$", line)

            if row_match and row_match.group(2) in stale_params:
                old_param = row_match.group(2)
                # Find if there is a replacement parameter in code not yet in table
                replacement_param = None
                for cp in param_names_in_code:
                    if f"`{cp}`" not in content and cp not in content:
                        replacement_param = code_params[cp]
                        break

                if replacement_param:
                    # Replace obsolete row with new parameter row
                    type_str = replacement_param.type_annotation or "Any"
                    desc_str = f"Updated parameter (default: {replacement_param.default_value})" if replacement_param.default_value else "Parameter for " + symbol.name
                    new_line = f"| `{replacement_param.name}` | {type_str} | {desc_str} |"
                    new_lines.append(new_line)
                    fixed_count += 1
                else:
                    # Parameter was simply removed from code; delete the obsolete doc row
                    fixed_count += 1
                    continue
            elif bullet_match and bullet_match.group(2) in stale_params:
                # Obsolete bullet point; drop it
                fixed_count += 1
                continue
            else:
                new_lines.append(line)

        return "\n".join(new_lines) + ("\n" if content.endswith("\n") else ""), fixed_count

    def _fix_return_type_mismatch(
        self,
        content: str,
        issue: DriftIssue,
        symbol: CodeSymbol,
    ) -> Tuple[str, int]:
        """Update return type descriptions in markdown."""
        if not symbol.return_type:
            return content, 0

        # Look for phrases like "Returns string" or "returns string"
        pattern = re.compile(r"(returns\s+)string", re.IGNORECASE)
        if pattern.search(content):
            new_content = pattern.sub(f"\\1`{symbol.return_type}`", content)
            return new_content, 1

        return content, 0
