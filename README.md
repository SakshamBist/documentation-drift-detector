# 🔍 DocDrift — Documentation Drift Detector

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI Pipeline](https://img.shields.io/badge/CI-Automated%20Quality%20Check-blue.svg)](.github/workflows/ci.yml)
[![Models](https://img.shields.io/badge/Open--Source%20Models-Gemma%202%20%7C%20Llama%203-emerald.svg)](HACKATHON.md)
[![Problem 5](https://img.shields.io/badge/Hackathon-Problem%205-purple.svg)](HACKATHON.md)

> **Automated CI/CD agent that prevents documentation from falling behind code.**  
> Detects breaking changes, altered parameters, modified function signatures, and stale markdown guides across Pull Requests.

---

## 🎯 The Problem (Hackathon Problem 5)

In fast-moving open-source repositories, developers constantly refactor functions, rename CLI arguments, and resolve issues. However, **updating the documentation is almost always neglected**.

When code evolves but documentation remains static:
- ❌ **New contributors** follow outdated installation steps or function signatures and hit confusing errors.
- ❌ **Users & Maintainers** waste hours debugging code against stale docs.
- ❌ **API Drift** quietly accumulates until major breaking releases.

**DocDrift** solves this by continuously inspecting code changes against project documentation and flagging exact drift discrepancies before PRs are merged.

---

## 🏗️ System Architecture

```
  ┌──────────────────┐        ┌──────────────────┐
  │  Git Pull Request│        │  Markdown Docs   │
  │  Code Changes    │        │  (README / docs) │
  └─────────┬────────┘        └─────────┬────────┘
            │                           │
            ▼                           ▼
   [ AST Diff Parser ]        [ Section Extractor ]
   • Line Numbers             • Line Numbers
   • Modified Signatures      • Code Blocks
   • Parameter Changes        • Parameter Tables
            │                           │
            └─────────────┬─────────────┘
                          ▼
            ┌───────────────────────────┐
            │   Open-Source Model Engine │
            │   (Gemma 2 / Llama 3)     │
            │   • Semantic Alignment    │
            │   • Drift Classification  │
            │   • Diagnostic Insights   │
            └─────────────┬─────────────┘
                          ▼
            ┌───────────────────────────┐
            │   DocDrift Audit Report   │
            │   • Exact Code & Doc Lines│
            │   • Stale/Missing Params  │
            │   • CI/CD Exit Code Gating│
            └───────────────────────────┘
```

---

## ⚡ Core Capabilities

1. **AST-Level Signature Extraction**: Parses functions, parameters, return types, and CLI flags with exact line numbers.
2. **Markdown Semantic Locator**: Maps code symbols to their corresponding documentation sections, tables, and usage examples.
3. **Exact Mismatch Highlighting**: Pinpoints the exact code line, doc line, and parameter name causing documentation drift.
4. **Open-Source LLM Drift Analysis**: Leverages **Gemma 2** and **Llama 3** (local / open-weight inference) to evaluate whether documentation accurately reflects updated code behavior (securing the 15 open-source weightage points).
5. **CI/CD Quality Gate**: Returns exit code `1` on breaking drift to fail automated PR validation pipelines before merges occur.

---

## 🚀 Quickstart & Usage

### Prerequisites
- Python 3.10+
- Ollama or any OpenAI-compatible open-source model endpoint (Gemma 2 / Llama 3)

### Installation
```bash
git clone https://github.com/SakshamBist/documentation-drift-detector.git
cd documentation-drift-detector
pip3 install -r requirements.txt
```

### Run Locally (CLI)
```bash
# Scan code and documentation for drift
python3 -m docdrift.cli check --code examples/scenario_1_param_rename/client.py --docs examples/scenario_1_param_rename/README.md
```

**Example Output:**
```text
🔍 DocDrift Analysis Report (v0.1.0)
=================================================================
Code Symbols Analyzed : 1
Doc Sections Analyzed : 1
Total Drift Issues    : 1
-----------------------------------------------------------------

[1] 🔴 BREAKING: connect_to_database (PARAM_MISMATCH)
    Code Location : examples/scenario_1_param_rename/client.py:9
    Doc Location  : examples/scenario_1_param_rename/README.md:14
    Details       : Documentation lists parameter(s) `connection_timeout` which do not exist in code.
    Suggested Fix :
      # Update parameters for connect_to_database in examples/scenario_1_param_rename/README.md:
      # Remove obsolete parameter(s): `connection_timeout`
      # Document new parameter(s): `timeout_seconds`
=================================================================
```

### Use as a GitHub Action in Any Repository
Add `.github/workflows/docdrift.yml` to your repo:
```yaml
name: DocDrift Quality Gate
on: [pull_request]

jobs:
  check-drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: SakshamBist/documentation-drift-detector@main
        with:
          code-path: '.'
          docs-path: 'README.md'
          fail-on-breaking: 'true'
```

---

## 📂 Proof & Validation (`examples/`)

In compliance with hackathon evaluation standards, concrete reproducible drift scenarios are provided in [`examples/`](examples/):
- **Example 1**: Function signature change (parameter renamed) with stale doc table.
- **Example 2**: Return type refactored to dictionary with outdated doc string.
- **Example 3**: CLI argument deprecated with unchanged README usage guide.

---

## 👥 Team: BIG 4

| Member | Roll Number | Role |
| :--- | :--- | :--- |
| **SAKSHAM BIST** | `2601020043` | Team Lead & Pipeline Architect |
| **KUSHAL SINGLA** | `2601010197` | LLM & Semantic Engine |
| **KRRISH RAJ** | `2601010426` | AST Diff Parser & Test Engineer |
| **RUDRA SHARMA** | `2601020042` | CI/CD Integration & Example Proofs |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) — see the [`LICENSE`](LICENSE) file for details.
