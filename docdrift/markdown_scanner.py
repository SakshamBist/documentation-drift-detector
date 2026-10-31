"""Markdown scanner for extracting symbol mentions, CLI flags, default values, and parameter tables."""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Union

from docdrift.models import DocSection


class MarkdownScanner:
    """Parses markdown files to locate symbol documentation, CLI usage, and parameter tables."""

    def scan_content(self, content: str, file_path: str = "<memory>") -> List[DocSection]:
        """Scan raw markdown string and return structured DocSections."""
        sections: List[DocSection] = []
        lines = content.splitlines()

        current_heading = "Top-level Overview"
        current_heading_line = 1
        current_lines: List[str] = []

        subheading_names = {
            "parameters", "arguments", "args", "params", "returns", "return",
            "example", "examples", "usage", "cli", "flags", "options"
        }

        def flush_section(heading: str, h_line: int, lines_accum: List[str]):
            if not lines_accum:
                return
            sec_text = "\n".join(lines_accum)
            code_blocks = self._extract_code_blocks(sec_text)
            params, defaults = self._extract_parameters_and_defaults(sec_text)
            cli_flags = self._extract_cli_flags(sec_text)
            symbols = self._extract_mentioned_symbols(sec_text, params)

            sections.append(
                DocSection(
                    file_path=file_path,
                    heading=heading,
                    line_number=h_line,
                    content=sec_text,
                    code_blocks=code_blocks,
                    documented_params=params,
                    documented_defaults=defaults,
                    mentioned_symbols=symbols,
                    mentioned_cli_flags=cli_flags,
                )
            )

        for line_idx, line in enumerate(lines, 1):
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                new_heading = heading_match.group(2).strip()
                clean_name = re.sub(r"[`()]", "", new_heading).strip().lower()

                # If this is a minor subheading (like ### Parameters) under a function doc, merge with current section
                if clean_name in subheading_names and current_lines:
                    current_lines.append(line)
                    continue

                flush_section(current_heading, current_heading_line, current_lines)
                current_heading = new_heading
                current_heading_line = line_idx
                current_lines = [line]
            else:
                current_lines.append(line)

        flush_section(current_heading, current_heading_line, current_lines)
        return sections

    def scan_file(self, file_path: Union[str, Path]) -> List[DocSection]:
        """Scan a single markdown file."""
        p = Path(file_path)
        if not p.is_file() or p.suffix.lower() not in (".md", ".markdown"):
            return []

        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            return self.scan_content(content, file_path=str(p))
        except Exception:
            return []

    def scan_directory(self, dir_path: Union[str, Path]) -> List[DocSection]:
        """Scan all markdown files in a directory or single file."""
        p = Path(dir_path)
        sections: List[DocSection] = []

        if p.is_file():
            return self.scan_file(p)

        for md_file in p.rglob("*.md"):
            parts = md_file.parts
            if any(part in (".venv", "node_modules", ".git") for part in parts):
                continue
            sections.extend(self.scan_file(md_file))

        return sections

    def _extract_code_blocks(self, text: str) -> List[str]:
        """Extract fenced code block contents."""
        blocks = re.findall(r"```[a-zA-Z0-9_-]*\n(.*?)```", text, re.DOTALL)
        return [b.strip() for b in blocks if b.strip()]

    def _extract_parameters_and_defaults(self, text: str) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Extract parameter names, descriptions, and documented default values."""
        params: Dict[str, str] = {}
        defaults: Dict[str, str] = {}

        # 1. Match Markdown table rows: | `param` | description | or | param | type | desc |
        table_rows = re.findall(r"^\|?\s*`?([a-zA-Z_][a-zA-Z0-9_]*)`?\s*\|([^|\n]+)\|?(.*)$", text, re.MULTILINE)
        for row in table_rows:
            p_name = row[0].strip()
            if p_name.lower() in ("parameter", "param", "argument", "arg", "field", "name", "variable"):
                continue
            desc = (row[1] + " " + row[2]).strip(" |")
            params[p_name] = desc

            # Check for default in description (e.g. default: 30, defaults to 30, default=None)
            def_match = re.search(r"(?:default(?:s to|\s*[:=]))\s*`?([a-zA-Z0-9_.-]+)`?", desc, re.IGNORECASE)
            if def_match:
                defaults[p_name] = def_match.group(1).strip()

        # 2. Match Bullet points: - `param_name`: description or * `param_name` (type): description
        bullet_matches = re.findall(
            r"^\s*[-*]\s+`([a-zA-Z_][a-zA-Z0-9_]*)`\s*(?:\([^)]*\))?\s*[:\-]\s*(.+)$",
            text,
            re.MULTILINE,
        )
        for p_name, desc in bullet_matches:
            params[p_name] = desc.strip()
            def_match = re.search(r"(?:default(?:s to|\s*[:=]))\s*`?([a-zA-Z0-9_.-]+)`?", desc, re.IGNORECASE)
            if def_match:
                defaults[p_name] = def_match.group(1).strip()

        return params, defaults

    def _extract_cli_flags(self, text: str) -> List[str]:
        """Extract CLI flags like --timeout, --deadline from documentation (excluding markdown rules ---)."""
        flags = re.findall(r"(`--[a-zA-Z][a-zA-Z0-9_-]*`|--[a-zA-Z][a-zA-Z0-9_-]*)", text)
        clean_flags = [f.strip("`") for f in flags]
        return list(set(clean_flags))

    def _extract_mentioned_symbols(self, text: str, params: Dict[str, str]) -> List[str]:
        """Find functions or methods mentioned in text or code snippets."""
        explicit_funcs = re.findall(r"`([a-zA-Z_][a-zA-Z0-9_]*)\(\)`", text)
        def_funcs = re.findall(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", text)
        func_calls = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", text)

        all_symbols = set(explicit_funcs + def_funcs + func_calls)

        # Also check headings like ### `connect_to_database()`
        heading_matches = re.findall(r"#{1,6}\s*`?([a-zA-Z_][a-zA-Z0-9_]*)(?:\(\))?`?", text)
        all_symbols.update(heading_matches)

        all_symbols -= set(params.keys())

        ignored = {
            "def", "class", "import", "return", "from", "if", "for", "while",
            "true", "false", "none", "print", "str", "int", "bool", "dict",
            "list", "parameters", "arguments", "example", "usage", "overview",
            "scenario", "documentation"
        }
        return [s for s in all_symbols if s.lower() not in ignored and len(s) > 1]
