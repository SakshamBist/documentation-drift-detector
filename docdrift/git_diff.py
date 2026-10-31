"""Git diff parser for analyzing Pull Request changes and isolating modified symbols."""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class DiffHunk:
    """Represents a single unified diff hunk (@@ -l,s +l,s @@)."""
    old_start: int
    old_length: int
    new_start: int
    new_length: int
    lines: List[str] = field(default_factory=list)

    @property
    def new_range(self) -> Tuple[int, int]:
        return self.new_start, self.new_start + max(1, self.new_length) - 1


@dataclass
class FileDiff:
    """Represents diff modifications for a specific file."""
    old_path: str
    new_path: str
    hunks: List[DiffHunk] = field(default_factory=list)
    added_lines: Set[int] = field(default_factory=set)
    deleted_lines: List[str] = field(default_factory=list)
    raw_diff: str = ""

    def touches_range(self, start_line: int, end_line: Optional[int] = None) -> bool:
        """Check if symbol line range [start_line, end_line] overlaps any modified hunk."""
        end = end_line if end_line is not None else start_line
        for hunk in self.hunks:
            h_start, h_end = hunk.new_range
            # Overlap condition: max(start_line, h_start) <= min(end, h_end)
            if max(start_line, h_start) <= min(end, h_end):
                return True
        return False

    def touches_line(self, line: int) -> bool:
        """Check if line is modified in diff."""
        return self.touches_range(line, line)

    def get_hunk_for_range(self, start_line: int, end_line: Optional[int] = None) -> Optional[DiffHunk]:
        """Find the hunk that spans the given line range."""
        end = end_line if end_line is not None else start_line
        for hunk in self.hunks:
            h_start, h_end = hunk.new_range
            if max(start_line, h_start) <= min(end, h_end):
                return hunk
        return None


@dataclass
class GitDiffSummary:
    """Aggregated summary of changes extracted from a Git diff."""
    files: Dict[str, FileDiff] = field(default_factory=dict)
    raw_diff: str = ""

    @property
    def changed_files(self) -> List[str]:
        return list(self.files.keys())

    def is_line_modified(self, file_path: str, start_line: int, end_line: Optional[int] = None) -> bool:
        """Check if a file and line range was modified in the diff."""
        clean_path = str(Path(file_path).as_posix())
        for path_key, fdiff in self.files.items():
            if path_key in clean_path or clean_path.endswith(path_key):
                if fdiff.touches_range(start_line, end_line):
                    return True
        return False

    def get_diff_snippet_for_line(self, file_path: str, start_line: int, end_line: Optional[int] = None) -> Optional[str]:
        """Extract the exact diff snippet (+ / - lines) touching the given line range."""
        clean_path = str(Path(file_path).as_posix())
        for path_key, fdiff in self.files.items():
            if path_key in clean_path or clean_path.endswith(path_key):
                hunk = fdiff.get_hunk_for_range(start_line, end_line)
                if hunk:
                    modified_lines = [l for l in hunk.lines if l.startswith("+") or l.startswith("-")]
                    return "\n".join(modified_lines[:6])
        return None


class GitDiffParser:
    """Parses git unified diff output into structured file and line modifications."""

    @staticmethod
    def parse(diff_text: str) -> GitDiffSummary:
        """Parse raw unified git diff into GitDiffSummary."""
        summary = GitDiffSummary(raw_diff=diff_text)
        current_file: Optional[FileDiff] = None
        current_hunk: Optional[DiffHunk] = None

        file_header_re = re.compile(r"^diff --git a/(.+?) b/(.+)$")
        hunk_header_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

        for line in diff_text.splitlines():
            file_match = file_header_re.match(line)
            if file_match:
                old_p, new_p = file_match.group(1), file_match.group(2)
                current_file = FileDiff(old_path=old_p, new_path=new_p)
                summary.files[new_p] = current_file
                current_hunk = None
                continue

            if current_file is None:
                continue

            hunk_match = hunk_header_re.match(line)
            if hunk_match:
                old_start = int(hunk_match.group(1))
                old_len = int(hunk_match.group(2) or 1)
                new_start = int(hunk_match.group(3))
                new_len = int(hunk_match.group(4) or 1)
                current_hunk = DiffHunk(
                    old_start=old_start,
                    old_length=old_len,
                    new_start=new_start,
                    new_length=new_len,
                )
                current_file.hunks.append(current_hunk)
                continue

            if current_hunk is not None:
                current_hunk.lines.append(line)
                if line.startswith("+") and not line.startswith("+++"):
                    line_offset = len([l for l in current_hunk.lines if l.startswith("+") or not l.startswith("-")]) - 1
                    current_file.added_lines.add(current_hunk.new_start + max(0, line_offset))
                elif line.startswith("-") and not line.startswith("---"):
                    current_file.deleted_lines.append(line[1:].strip())

        return summary

    @staticmethod
    def from_git(
        repo_path: str = ".",
        base_ref: Optional[str] = None,
        head_ref: Optional[str] = None,
        diff_args: Optional[str] = None,
    ) -> GitDiffSummary:
        """Run `git diff` in the repository and parse output."""
        cmd = ["git", "-C", repo_path, "diff"]
        if diff_args:
            cmd.extend(diff_args.split())
        elif base_ref and head_ref:
            cmd.append(f"{base_ref}...{head_ref}")
        elif base_ref:
            cmd.append(base_ref)
        else:
            cmd.append("HEAD~1")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return GitDiffParser.parse(result.stdout)
        except Exception:
            return GitDiffSummary()
