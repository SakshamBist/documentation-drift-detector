# 📊 DocDrift Historical Benchmark & False-Alarm Report

Empirical evaluation of DocDrift on historical commits from major open-source projects.

### 🎯 Summary Metrics
- **Recall (Drift Catch Rate):** 100.0% (4/4)
- **Precision:** 100.0%
- **False Alarm Rate:** 0.0% (0/4)

### 🔬 Detailed Scenario Breakdown
| ID | Project | Target | Expected | Detected | Outcome | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `REQ-01` | **psf/requests** | `DRIFT_POSITIVE` | ≥1 Drift | 1 issues | ✅ CAUGHT (True Positive) | Historical PR added session-level timeout parameter, but README table still omitted it. |
| `FLASK-01` | **pallets/flask** | `DRIFT_POSITIVE` | ≥1 Drift | 1 issues | ✅ CAUGHT (True Positive) | CLI argument --app added in code, but README still documents obsolete --application. |
| `FAST-01` | **tiangolo/fastapi** | `DRIFT_POSITIVE` | ≥1 Drift | 1 issues | ✅ CAUGHT (True Positive) | Endpoint return type changed to bool, but API docs claim it returns dict. |
| `MED-01` | **rudras2048-arch/medicoool** | `DRIFT_POSITIVE` | ≥1 Drift | 1 issues | ✅ CAUGHT (True Positive) | Real teammate PR adding get_substitutes() documentation with ghost parameter max_results. |
| `CTRL-01` | **psf/requests (Control)** | `CLEAN_NEGATIVE` | 0 (Clean) | 0 issues | ✅ CLEAN (True Negative) | Bug fix inside private connection pool; public API signatures unchanged. |
| `CTRL-02` | **pallets/flask (Control)** | `CLEAN_NEGATIVE` | 0 (Clean) | 0 issues | ✅ CLEAN (True Negative) | Markdown copy editing without modifying function signatures. |
| `CTRL-03` | **tiangolo/fastapi (Control)** | `CLEAN_NEGATIVE` | 0 (Clean) | 0 issues | ✅ CLEAN (True Negative) | Parameter renamed in code AND updated in docs within the same PR. |
| `CTRL-04` | **rudras2048-arch/medicoool (Control)** | `CLEAN_NEGATIVE` | 0 (Clean) | 0 issues | ✅ CLEAN (True Negative) | Comment addition mentioning variable names; zero signature changes. |