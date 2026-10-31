"""Command line interface for DocDrift Documentation Drift Detector."""

import argparse
import json
import sys
from pathlib import Path

from docdrift import __version__
from docdrift.drift_detector import DriftDetector


def main():
    parser = argparse.ArgumentParser(
        prog="docdrift",
        description="DocDrift: Automated Documentation Drift Detector for Open Source Projects.",
    )
    parser.add_argument("--version", action="version", version=f"docdrift {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: check
    check_parser = subparsers.add_parser("check", help="Scan code and docs for drift")
    check_parser.add_argument(
        "--code",
        default=".",
        help="Path to Python codebase or file (default: current directory)",
    )
    check_parser.add_argument(
        "--docs",
        "--doc",
        dest="docs",
        default="README.md",
        help="Path to markdown documentation file or directory (default: README.md)",
    )
    check_parser.add_argument(
        "--format",
        choices=["text", "markdown", "json"],
        default="text",
        help="Output format (default: text)",
    )
    check_parser.add_argument(
        "--fail-on-breaking",
        action="store_true",
        default=True,
        help="Exit with code 1 if breaking drift is detected (default: True)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "check":
        detector = DriftDetector()
        report = detector.analyze(code_path=args.code, docs_path=args.docs)

        # Output formatting
        if args.format == "json":
            print(json.dumps(report.model_dump(), indent=2))
        elif args.format == "markdown":
            print(report.to_markdown())
        else:
            # Clean human-readable terminal format
            print(f"\n🔍 DocDrift Analysis Report (v{__version__})")
            print("=" * 65)
            print(f"Code Symbols Analyzed : {report.total_symbols_analyzed}")
            print(f"Doc Sections Analyzed : {report.total_docs_analyzed}")
            print(f"Total Drift Issues    : {len(report.issues)}")
            print("-" * 65)

            if report.is_clean:
                print("✅ All documentation is fully in sync with codebase!")
            else:
                for i, issue in enumerate(report.issues, 1):
                    badge = "🔴 BREAKING" if issue.severity.value == "BREAKING" else "🟡 WARNING"
                    code_loc = f"{issue.file_code}:{issue.line_code}" if issue.line_code else issue.file_code
                    doc_loc = f"{issue.file_doc}:{issue.line_doc}" if issue.line_doc else issue.file_doc
                    print(f"\n[{i}] {badge}: {issue.symbol_name} ({issue.drift_type.value})")
                    print(f"    Code Location : {code_loc}")
                    print(f"    Doc Location  : {doc_loc}")
                    print(f"    Details       : {issue.description}")
                    if issue.suggested_fix:
                        print("    Suggested Fix :")
                        for fix_line in issue.suggested_fix.splitlines():
                            print(f"      {fix_line}")

            print("=" * 65)

        if args.fail_on_breaking and report.breaking_count > 0:
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
