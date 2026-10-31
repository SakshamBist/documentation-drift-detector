# 🧪 DocDrift Proof of Functionality (`examples/`)

This directory provides concrete, reproducible evidence that **DocDrift** solves **Problem 5: Documentation Drift Detector**, complying with Hackathon Rule 4.

---

## 📋 Scenarios Included

### Scenario 1: Parameter Renamed (`scenario_1_param_rename/`)
- **Code Change**: `client.py` defines `connect_to_database(host, port, timeout_ms=3000)`.
- **Stale Documentation**: `README.md` documents `timeout_secs` in the parameter table.
- **Detector Result**: 🔴 **BREAKING: PARAM_MISMATCH**. Flags `timeout_secs` as obsolete and suggests adding `timeout_ms`.
- **Command to Reproduce**:
  ```bash
  python -m docdrift.cli check --code examples/scenario_1_param_rename/client.py --docs examples/scenario_1_param_rename/README.md
  ```

---

### Scenario 2: Return Type Drift (`scenario_2_return_type_drift/`)
- **Code Change**: `service.py` refactored `fetch_user_profile(user_id)` to return `Dict[str, Any]`.
- **Stale Documentation**: `README.md` still states *"returns string"*.
- **Detector Result**: 🟡 **WARNING: RETURN_TYPE_MISMATCH**. Highlights that documentation contradicts the type annotation.
- **Command to Reproduce**:
  ```bash
  python -m docdrift.cli check --code examples/scenario_2_return_type_drift/service.py --docs examples/scenario_2_return_type_drift/README.md
  ```

---

### Scenario 3: Obsolete / Removed Parameter (`scenario_3_removed_argument/`)
- **Code Change**: `auth.py` removed legacy `use_ssl` parameter from `authenticate_user()`.
- **Stale Documentation**: `README.md` parameter table still documents `use_ssl`.
- **Detector Result**: 🔴 **BREAKING: PARAM_MISMATCH**. Detects the ghost parameter in docs and outputs a patch.
- **Command to Reproduce**:
  ```bash
  python -m docdrift.cli check --code examples/scenario_3_removed_argument/auth.py --docs examples/scenario_3_removed_argument/README.md
  ```
