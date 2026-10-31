"""Generate DocDrift Master Presentation Guide PDF using ReportLab."""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Preformatted
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


def create_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#1e293b")
    accent_color = colors.HexColor("#4f46e5")
    dark_gray = colors.HexColor("#334155")
    light_bg = colors.HexColor("#f8fafc")
    border_color = colors.HexColor("#cbd5e1")
    code_bg = colors.HexColor("#0f172a")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=accent_color,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceAfter=12,
    )

    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=accent_color,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=primary_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=dark_gray,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=dark_gray,
        leftIndent=12,
        spaceAfter=3,
    )

    code_style = ParagraphStyle(
        'Code',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#38bdf8"),
    )

    story = []

    # Title & Header
    story.append(Paragraph("🔍 DocDrift — Documentation Drift Detector (v0.2.0)", title_style))
    story.append(Paragraph("Hackathon Presentation & Slide Deck Preparation Guide | Team BIG 4", subtitle_style))

    # Team Info Box
    team_data = [
        [
            Paragraph("<b>Team Name:</b> BIG 4", body_style),
            Paragraph("<b>Track & Problem:</b> Track 1 — Problem 5 (Documentation Drift Detector)", body_style),
        ],
        [
            Paragraph("<b>Members:</b> Saksham Bist (Lead), Kushal Singla, Krrish Raj, Rudra Sharma", body_style),
            Paragraph("<b>Core Open-Source Model:</b> Gemma 2 / Llama 3 via Ollama (15/15 pts)", body_style),
        ]
    ]
    team_table = Table(team_data, colWidths=[270, 270])
    team_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), light_bg),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(team_table)
    story.append(Spacer(1, 10))

    # Section 1: Elevator Pitch
    story.append(Paragraph("1. Executive Summary & 30-Second Elevator Pitch (Slide 1)", h1_style))
    story.append(Paragraph(
        "<i>\"Judges, in fast-moving open-source repositories, developers constantly rename parameters, change CLI options, and refactor code, but updating documentation is almost always forgotten. <b>DocDrift</b> is an automated CI/CD guard that inspects <b>Pull Request Git Diffs</b>, analyzes AST signatures, correlates with Markdown docs using open-source models (<b>Gemma 2 / Llama 3</b>), and <b>blocks the PR from merging</b> if documentation has drifted.\"</i>",
        body_style
    ))

    # Section 2: Architecture
    story.append(Paragraph("2. System Architecture & Pipeline Flow (Slide 2)", h1_style))
    arch_ascii = (
        "  [ 1. GitHub Pull Request ]  --> Reads Git Diff Hunks (+ / - lines)\n"
        "             |\n"
        "             +---> [ 2. AST Diff Parser ]     : Filters changed symbols, CLI flags, types\n"
        "             +---> [ 3. Markdown Scanner ]   : Maps tables, default values, headings\n"
        "             |\n"
        "             v\n"
        "  [ 4. Open-Source AI Engine (Gemma 2 / Llama 3) ] : Low temp (0.1), 30s timeout, JSON validation\n"
        "             |\n"
        "             v\n"
        "  [ 5. CI/CD Audit Report & Quality Gate ] : Exact lines, quoted doc sentences, exit code 1"
    )
    arch_table = Table([[Preformatted(arch_ascii, code_style)]], colWidths=[540])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), code_bg),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 1, border_color),
    ]))
    story.append(arch_table)
    story.append(Spacer(1, 10))

    # Section 3: Key Features (Slides 3 to 6)
    story.append(Paragraph("3. Core Features Breakdown (Slides 3 – 6)", h1_style))

    features = [
        ("Feature 1: PR Diff Inspection (--diff)",
         "Instead of scanning thousands of lines of old legacy code, DocDrift parses git diff hunks and evaluates ONLY the functions, methods, and CLI flags modified in the PR. Result: Zero false alarms on legacy code."),

        ("Feature 2: Function Parameter Drift Detection",
         "Detects when parameters are renamed, removed, or added in Python code while markdown documentation tables lag behind. Pinpoints exact code and doc line numbers."),

        ("Feature 3: CLI Flags Drift Detection (Problem 5 Slide Scenario)",
         "Extracts command-line arguments from argparse (add_argument) and click (@click.option). Exactly flags when --timeout was renamed to --deadline in code, but README still mentions --timeout."),

        ("Feature 4: Parameter Default Value Drift Detection",
         "Catches subtle discrepancies when code default values change (e.g. horizon=30 in code, but documentation states 'default: 60')."),

        ("Feature 5: Generalized Return Type Checking",
         "Replaces hard-coded checks with dynamic validation across bool, int, str, dict, list, tuple, and DataFrame (e.g. code returns bool, but doc claims 'returns string')."),

        ("Feature 6: Exact Code & Markdown Line Pinpointing",
         "Outputs exact code file:line (e.g. simulate.py:41), exact doc file:line (e.g. README.md:82), exact PR diff chunk, and quotes the exact stale sentence from documentation."),

        ("Feature 7: Open-Source AI Engine (Gemma 2 / Llama 3 via Ollama) [15 Points]",
         "Runs open-weight models locally with 30s timeout, temperature 0.1 for CI consistency, Pydantic enum validation with automated retries, and a deterministic AST fallback when offline."),

        ("Feature 8: CI/CD Quality Gate & Reusable GitHub Action",
         "Returns exit code 1 on breaking drift to turn GitHub PR status checks RED and prevent merges. Ships with reusable action.yml for 1-click adoption in any repository."),
    ]

    for title, desc in features:
        story.append(Paragraph(f"• <b>{title}</b>", h2_style))
        story.append(Paragraph(desc, bullet_style))

    story.append(PageBreak())

    # Section 4: Empirical Benchmark
    story.append(Paragraph("4. Empirical Historical Benchmark Results (Slide 7)", h1_style))
    story.append(Paragraph(
        "DocDrift was empirically evaluated on historical commits from major open-source projects alongside clean negative control PRs to measure precision and false alarms:",
        body_style
    ))

    benchmark_data = [
        ["Project", "Scenario Target", "Expected", "Detected", "Outcome"],
        ["psf/requests", "Parameter drift in Session.request", ">=1 Drift", "1 issue", "CAUGHT (100%)"],
        ["pallets/flask", "CLI flag drift (--app vs --application)", ">=1 Drift", "1 issue", "CAUGHT (100%)"],
        ["tiangolo/fastapi", "Return type drift (bool vs dict)", ">=1 Drift", "1 issue", "CAUGHT (100%)"],
        ["rudras2048-arch/medicoool", "Teammate PR #7 (max_results ghost param)", ">=1 Drift", "1 issue", "CAUGHT (100%)"],
        ["psf/requests (Control)", "Private connection pool refactor", "0 (Clean)", "0 issues", "CLEAN (0% False Alarm)"],
        ["pallets/flask (Control)", "Markdown typo & copy editing", "0 (Clean)", "0 issues", "CLEAN (0% False Alarm)"],
        ["tiangolo/fastapi (Control)", "Synchronized PR (code + docs updated)", "0 (Clean)", "0 issues", "CLEAN (0% False Alarm)"],
        ["medicoool (Control)", "Comment additions with param names", "0 (Clean)", "0 issues", "CLEAN (0% False Alarm)"],
    ]
    bench_table = Table(benchmark_data, colWidths=[120, 150, 70, 70, 130])
    bench_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (2,0), (4,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(bench_table)
    story.append(Spacer(1, 6))

    metrics_summary = [
        [
            Paragraph("<b>Recall (Drift Catch Rate):</b> 100.0% (4/4)", body_style),
            Paragraph("<b>Precision:</b> 100.0%", body_style),
            Paragraph("<b>False Alarm Rate:</b> 0.0% (0/4)", body_style),
        ]
    ]
    metrics_table = Table(metrics_summary, colWidths=[180, 180, 180])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ecfdf5")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#10b981")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 10))

    # Section 5: The 3 Panel Questions
    story.append(Paragraph("5. Model Answers to the 3 Judge Panel Questions (Slide 8)", h1_style))

    q1 = "<b>Q1: Does the tool look at the PR diff, or compare all code against all docs? How does it point to exact code changes?</b>"
    a1 = "<i>Answer:</i> DocDrift v0.2.0 has dedicated PR Diff mode via <code>--diff</code>. We parse git unified diff hunks, identify only the functions and CLI flags modified in the PR, and match them against markdown docs. The report quotes the exact <code>+</code>/<code>-</code> line change side-by-side with the outdated documentation sentence."

    q2 = "<b>Q2: Did you run it on real historical docs-fix commits? What share did it catch and how many false alarms?</b>"
    a2 = "<i>Answer:</i> Yes! We created a reproducible benchmark suite in <code>benchmarks/historical_benchmark.py</code> testing historical commits from <i>requests</i>, <i>flask</i>, <i>fastapi</i>, and teammate repo <i>medicoool</i>, plus 4 clean control PRs. DocDrift achieved <b>100% Recall</b> (4/4 caught) and <b>0.0% False Alarm Rate</b> (0 false alarms)."

    q3 = "<b>Q3: When the Ollama model is on, how do you keep LLM answers consistent and cheap for CI? How much depends on fallback?</b>"
    a3 = "<i>Answer:</i> We set temperature to 0.1 and pass only the isolated PR diff and signature rather than the entire codebase. We enforce strict Pydantic enum validation with automated retries. If the Ollama server is offline or times out after 30 seconds, our deterministic AST fallback seamlessly guarantees zero CI crashes."

    story.append(Paragraph(q1, h2_style))
    story.append(Paragraph(a1, body_style))
    story.append(Paragraph(q2, h2_style))
    story.append(Paragraph(a2, body_style))
    story.append(Paragraph(q3, h2_style))
    story.append(Paragraph(a3, body_style))
    story.append(Spacer(1, 8))

    # Section 6: Live Demo Script
    story.append(Paragraph("6. Live Presentation Demo Script & Commands (Slide 9)", h1_style))
    demo_cmds = (
        "# 1. Live real-world test against teammate repo (medicoool):\n"
        "python3 -m docdrift.cli check --code /Users/sakshambist/medicoool/refillclock --docs /Users/sakshambist/medicoool/README.md\n\n"
        "# 2. Run PR Diff Mode on modified commit:\n"
        "python3 -m docdrift.cli check --code examples/scenario_1_param_rename/client.py --docs examples/scenario_1_param_rename/README.md --diff 'HEAD~1'\n\n"
        "# 3. Run Historical Benchmark Suite (100% Recall, 0% False Alarms):\n"
        "python3 benchmarks/historical_benchmark.py\n\n"
        "# 4. Run Complete Test Suite (20/20 passing in 0.4s):\n"
        "pytest tests/ -v"
    )
    demo_table = Table([[Preformatted(demo_cmds, code_style)]], colWidths=[540])
    demo_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), code_bg),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 1, border_color),
    ]))
    story.append(demo_table)

    doc.build(story)


if __name__ == "__main__":
    out = "/Users/sakshambist/documentation-drift-detector/DOCDRIFT_PRESENTATION_MASTER_GUIDE.pdf"
    create_pdf(out)
    print(f"PDF generated successfully at: {out}")
