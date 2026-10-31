"""Open-source model evaluation engine (Gemma 2 / Llama 3 via Ollama or local API)."""

import json
import os
from typing import Dict, Optional
import requests

from docdrift.models import CodeSymbol, DocSection, DriftIssue, DriftSeverity, DriftType


class LLMEvaluator:
    """Evaluates semantic documentation drift using open-source models (Gemma 2 / Llama 3)."""

    def __init__(
        self,
        model_name: str = "gemma2",
        ollama_host: Optional[str] = None,
        timeout_seconds: int = 5,
    ):
        self.model_name = os.getenv("DOCDRIFT_MODEL", model_name)
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.timeout = timeout_seconds

    def evaluate_drift(
        self,
        symbol: CodeSymbol,
        doc_section: DocSection,
        param_diff: Dict[str, str],
    ) -> Optional[DriftIssue]:
        """Evaluate if documentation drifts from code using open-source LLM or heuristic fallback."""
        # Try local open-source model inference first (Ollama / vLLM)
        llm_response = self._query_open_source_model(symbol, doc_section, param_diff)
        if llm_response:
            return llm_response

        # Deterministic heuristic fallback (ensures CI & tests are 100% reliable offline)
        return self._heuristic_fallback(symbol, doc_section, param_diff)

    def _query_open_source_model(
        self,
        symbol: CodeSymbol,
        doc_section: DocSection,
        param_diff: Dict[str, str],
    ) -> Optional[DriftIssue]:
        """Query local Ollama endpoint running Gemma 2 or Llama 3."""
        prompt = self._build_prompt(symbol, doc_section, param_diff)
        url = f"{self.ollama_host}/api/generate"

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                parsed = json.loads(data.get("response", "{}"))
                if parsed.get("has_drift"):
                    severity_str = parsed.get("severity", "WARNING").upper()
                    severity = DriftSeverity.BREAKING if severity_str == "BREAKING" else DriftSeverity.WARNING
                    return DriftIssue(
                        symbol_name=symbol.name,
                        file_code=symbol.file_path,
                        file_doc=doc_section.file_path,
                        severity=severity,
                        drift_type=DriftType(parsed.get("drift_type", "PARAM_MISMATCH")),
                        description=parsed.get("description", "Documentation drift detected by Gemma/Llama."),
                        suggested_fix=parsed.get("suggested_fix"),
                    )
        except Exception:
            # Server not running or timed out; fall back to deterministic heuristic
            pass

        return None

    def _heuristic_fallback(
        self,
        symbol: CodeSymbol,
        doc_section: DocSection,
        param_diff: Dict[str, str],
    ) -> Optional[DriftIssue]:
        """Deterministic evaluation of documentation drift when LLM server is offline."""
        code_params = set(symbol.param_names())
        doc_params = set(doc_section.documented_params.keys())

        # Check for documented parameters that no longer exist in code
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

            return DriftIssue(
                symbol_name=symbol.name,
                file_code=symbol.file_path,
                file_doc=doc_section.file_path,
                severity=DriftSeverity.BREAKING,
                drift_type=DriftType.PARAM_MISMATCH,
                description=f"Documentation lists parameter(s) {stale_list} which do not exist in code.",
                code_snippet=f"def {symbol.name}({', '.join(symbol.param_names())})",
                doc_snippet=doc_section.content[:300],
                suggested_fix="\n".join(fix_lines),
            )

        if missing_in_doc and len(doc_params) > 0:
            # Doc explicitly lists parameters, but forgot new required ones
            new_list = ", ".join(f"`{p}`" for p in sorted(missing_in_doc))
            return DriftIssue(
                symbol_name=symbol.name,
                file_code=symbol.file_path,
                file_doc=doc_section.file_path,
                severity=DriftSeverity.WARNING,
                drift_type=DriftType.PARAM_MISMATCH,
                description=f"New code parameter(s) {new_list} are not documented in {doc_section.heading}.",
                code_snippet=f"def {symbol.name}({', '.join(symbol.param_names())})",
                doc_snippet=doc_section.content[:300],
                suggested_fix=f"Add parameter descriptions for {new_list} in {doc_section.file_path}.",
            )

        return None

    def _build_prompt(
        self,
        symbol: CodeSymbol,
        doc_section: DocSection,
        param_diff: Dict[str, str],
    ) -> str:
        """Construct structured prompt for open-source model evaluation."""
        return f"""You are an automated Documentation Drift Detector expert.
Analyze if the documentation accurately reflects the Python code signature below.

CODE SYMBOL:
- Name: {symbol.name}
- Parameters: {[p.model_dump() for p in symbol.parameters]}
- Return Type: {symbol.return_type}

DOCUMENTATION SECTION ({doc_section.heading} in {doc_section.file_path}):
{doc_section.content}

DOCUMENTED PARAMETERS:
{json.dumps(doc_section.documented_params)}

TASK:
Determine if there is a documentation drift (e.g., parameter renamed, removed, type mismatch).
Respond ONLY in valid JSON matching this schema:
{{
  "has_drift": true/false,
  "severity": "BREAKING" | "WARNING" | "COSMETIC",
  "drift_type": "PARAM_MISMATCH" | "RETURN_TYPE_MISMATCH",
  "description": "Clear explanation of the mismatch",
  "suggested_fix": "Markdown snippet to update the documentation"
}}
"""
