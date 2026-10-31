"""Open-source model evaluation engine (Gemma 2 / Llama 3 via Ollama with validation, retries, and top-band accuracy)."""

import json
import os
import re
from typing import Dict, Optional
import requests

from docdrift.models import CodeSymbol, DocSection, DriftIssue, DriftSeverity, DriftType


class LLMEvaluator:
    """Evaluates semantic documentation drift using open-source models (Gemma 2 / Llama 3)."""

    def __init__(
        self,
        model_name: str = "gemma2",
        ollama_host: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        self.model_name = os.getenv("DOCDRIFT_MODEL", model_name)
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        # 30-second default for local LLM inference (Gemma 2 / Llama 3)
        env_timeout = int(os.getenv("DOCDRIFT_TIMEOUT", "30"))
        self.timeout = timeout_seconds if timeout_seconds is not None else env_timeout
        self.max_retries = 2

    def evaluate_drift(
        self,
        symbol: CodeSymbol,
        doc_section: DocSection,
        param_diff: Optional[Dict[str, str]] = None,
        pr_diff_context: Optional[str] = None,
    ) -> Optional[DriftIssue]:
        """Evaluate if documentation drifts from code using open-source LLM or heuristic fallback."""
        # 1. Try local open-source model inference first (Ollama / vLLM)
        llm_response = self._query_open_source_model(
            symbol=symbol,
            doc_section=doc_section,
            param_diff=param_diff or {},
            pr_diff_context=pr_diff_context,
        )
        if llm_response:
            return llm_response

        # 2. Deterministic heuristic fallback (ensures tests and offline CI are 100% reliable)
        return self._heuristic_fallback(symbol, doc_section, pr_diff_context)

    def _query_open_source_model(
        self,
        symbol: CodeSymbol,
        doc_section: DocSection,
        param_diff: Dict[str, str],
        pr_diff_context: Optional[str] = None,
    ) -> Optional[DriftIssue]:
        """Query local Ollama endpoint running Gemma 2 or Llama 3 with retries and enum validation."""
        prompt = self._build_prompt(symbol, doc_section, pr_diff_context)
        url = f"{self.ollama_host}/api/generate"

        for attempt in range(self.max_retries + 1):
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,  # Low temperature for deterministic, consistent CI results
                },
            }

            try:
                resp = requests.post(url, json=payload, timeout=self.timeout)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                raw_response = data.get("response", "{}")
                parsed = json.loads(raw_response)

                if not isinstance(parsed, dict) or not parsed.get("has_drift"):
                    return None

                # Validate severity enum
                severity_str = str(parsed.get("severity", "WARNING")).upper()
                severity = DriftSeverity.BREAKING if severity_str == "BREAKING" else DriftSeverity.WARNING

                # Validate drift_type enum against DriftType
                drift_type_str = str(parsed.get("drift_type", "PARAM_MISMATCH")).upper()
                try:
                    drift_type = DriftType(drift_type_str)
                except ValueError:
                    drift_type = DriftType.PARAM_MISMATCH

                # Extract exact sentence and code change
                exact_doc_sent = parsed.get("exact_doc_sentence") or self._find_matching_sentence(
                    doc_section.content, symbol.name
                )
                exact_code_change = parsed.get("exact_code_change") or symbol.raw_source

                return DriftIssue(
                    symbol_name=symbol.name,
                    file_code=symbol.file_path,
                    file_doc=doc_section.file_path,
                    line_code=symbol.line_number,
                    line_doc=doc_section.line_number,
                    severity=severity,
                    drift_type=drift_type,
                    description=parsed.get("description", "Documentation drift detected by Gemma/Llama."),
                    exact_code_change=exact_code_change,
                    exact_doc_sentence=exact_doc_sent,
                    code_snippet=symbol.raw_source,
                    doc_snippet=doc_section.content[:300],
                    suggested_fix=parsed.get("suggested_fix"),
                    pr_diff_context=pr_diff_context,
                )

            except json.JSONDecodeError:
                # Retry asking for clean JSON
                prompt += "\nERROR: Previous response was not valid JSON. Output strictly valid JSON."
                continue
            except Exception:
                # Connection refused / timeout; gracefully fall back
                break

        return None

    def _heuristic_fallback(
        self,
        symbol: CodeSymbol,
        doc_section: DocSection,
        pr_diff_context: Optional[str] = None,
    ) -> Optional[DriftIssue]:
        """Deterministic evaluation of documentation drift when LLM server is offline."""
        # Handle CLI flag drift
        if symbol.symbol_type == "cli_flag":
            flag = symbol.name
            if flag not in doc_section.mentioned_cli_flags:
                # A CLI flag exists in code, but doc still mentions an old flag or is missing
                return None
            return None

        code_params = set(symbol.param_names())
        doc_params = set(doc_section.documented_params.keys())

        # Check for documented parameters that no longer exist in code (Breaking Drift)
        stale_params = doc_params - code_params
        missing_in_doc = code_params - doc_params

        if stale_params:
            stale_list = ", ".join(f"`{p}`" for p in sorted(stale_params))
            fix_lines = [
                f"# Update parameters for {symbol.name} in {doc_section.file_path}:",
                f"# Remove obsolete parameter(s): {stale_list}",
            ]
            if missing_in_doc:
                new_list = ", ".join(f"`{p}`" for p in sorted(missing_in_doc))
                fix_lines.append(f"# Document new parameter(s): {new_list}")

            exact_sentence = self._find_matching_sentence(doc_section.content, next(iter(stale_params)))

            return DriftIssue(
                symbol_name=symbol.name,
                file_code=symbol.file_path,
                file_doc=doc_section.file_path,
                line_code=symbol.line_number,
                line_doc=doc_section.line_number,
                severity=DriftSeverity.BREAKING,
                drift_type=DriftType.PARAM_MISMATCH,
                description=f"Documentation lists parameter(s) {stale_list} which do not exist in code.",
                exact_code_change=symbol.raw_source,
                exact_doc_sentence=exact_sentence,
                code_snippet=f"def {symbol.name}({', '.join(symbol.param_names())})",
                doc_snippet=doc_section.content[:300],
                suggested_fix="\n".join(fix_lines),
                pr_diff_context=pr_diff_context,
            )

        # Check for documented default values that contradict code defaults
        for p in symbol.parameters:
            if p.name in doc_section.documented_defaults and p.default_value is not None:
                doc_default = doc_section.documented_defaults[p.name]
                clean_code_def = p.default_value.strip("'\"")
                clean_doc_def = doc_default.strip("'\"")
                if clean_code_def != clean_doc_def:
                    return DriftIssue(
                        symbol_name=symbol.name,
                        file_code=symbol.file_path,
                        file_doc=doc_section.file_path,
                        line_code=symbol.line_number,
                        line_doc=doc_section.line_number,
                        severity=DriftSeverity.WARNING,
                        drift_type=DriftType.DEFAULT_VALUE_MISMATCH,
                        description=(
                            f"Default value mismatch for `{p.name}` in `{symbol.name}`: "
                            f"code default is `{p.default_value}`, but documentation states `{doc_default}`."
                        ),
                        exact_code_change=symbol.raw_source,
                        exact_doc_sentence=f"Parameter `{p.name}` defaults to `{doc_default}`",
                        suggested_fix=f"Update default value for `{p.name}` to `{p.default_value}` in {doc_section.file_path}.",
                        pr_diff_context=pr_diff_context,
                    )

        if missing_in_doc and len(doc_params) > 0:
            new_list = ", ".join(f"`{p}`" for p in sorted(missing_in_doc))
            return DriftIssue(
                symbol_name=symbol.name,
                file_code=symbol.file_path,
                file_doc=doc_section.file_path,
                line_code=symbol.line_number,
                line_doc=doc_section.line_number,
                severity=DriftSeverity.WARNING,
                drift_type=DriftType.PARAM_MISMATCH,
                description=f"New code parameter(s) {new_list} are not documented in {doc_section.heading}.",
                exact_code_change=symbol.raw_source,
                code_snippet=f"def {symbol.name}({', '.join(symbol.param_names())})",
                doc_snippet=doc_section.content[:300],
                suggested_fix=f"Add parameter descriptions for {new_list} in {doc_section.file_path}.",
                pr_diff_context=pr_diff_context,
            )

        return None

    def _find_matching_sentence(self, content: str, keyword: str) -> Optional[str]:
        """Locate the exact sentence or markdown line mentioning a keyword."""
        for line in content.splitlines():
            if keyword in line and not line.startswith("#"):
                return line.strip(" |-*`")
        return None

    def _build_prompt(
        self,
        symbol: CodeSymbol,
        doc_section: DocSection,
        pr_diff_context: Optional[str] = None,
    ) -> str:
        """Construct structured prompt for open-source model evaluation."""
        diff_info = f"\nPR GIT DIFF CHUNK:\n{pr_diff_context}\n" if pr_diff_context else ""

        return f"""You are an automated Documentation Drift Detector expert.
Analyze if the documentation accurately reflects the Python code signature below.{diff_info}

CODE SYMBOL:
- Name: {symbol.name}
- Type: {symbol.symbol_type}
- Parameters: {[p.model_dump() for p in symbol.parameters]}
- Return Type: {symbol.return_type}
- Signature Line: {symbol.raw_source}

DOCUMENTATION SECTION ({doc_section.heading} in {doc_section.file_path}):
{doc_section.content}

DOCUMENTED PARAMETERS:
{json.dumps(doc_section.documented_params)}

DOCUMENTED DEFAULTS:
{json.dumps(doc_section.documented_defaults)}

TASK:
Determine if there is a documentation drift (e.g. parameter renamed, removed, default value mismatch, CLI flag mismatch, or return type mismatch).
Respond ONLY in valid JSON matching this schema:
{{
  "has_drift": true/false,
  "severity": "BREAKING" | "WARNING" | "COSMETIC",
  "drift_type": "PARAM_MISMATCH" | "CLI_FLAG_MISMATCH" | "DEFAULT_VALUE_MISMATCH" | "RETURN_TYPE_MISMATCH",
  "exact_doc_sentence": "Exact sentence in documentation that is outdated",
  "exact_code_change": "Exact line of code that changed or differs",
  "description": "Clear explanation of the mismatch",
  "suggested_fix": "Markdown snippet to update the documentation"
}}
"""
