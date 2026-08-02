# PROJECT_STATUS.md

**Read-only audit. No files were modified, refactored, or cleaned as part of producing this report.**
Date of audit: 2026-08-01. Branch audited: `dev-mann` (HEAD `c3e7468`). Remote checked: `origin` (`https://github.com/MannDangrechiya/revolt_ble_toolkit.git`).

---

## 1. Executive Summary

- **Project purpose**: A Python 3.12 toolkit for reverse-engineering a proprietary BLE (Bluetooth Low Energy) vehicle-control protocol from Android BTSnoop HCI captures — parsing (BTSnoop/HCI/ATT), heuristic protocol classification with mandatory confidence scores, GATT/compare analysis, report export, a PySide6 GUI, and an optional live-BLE client (Bleak-backed).
- **Current maturity**: Late-stage / near-release. Code, tests, lint/type-checking, and packaging are all in good shape. One **unresolved critical security issue** blocks public release (see §4, §6).
- **Is it production ready?** **No.** Blocked specifically by an unresolved data-exposure issue in the public git history, not by code quality.
- **Overall completion percentage (evidence-based)**: **~90%** of the engineering work is done and verified (tests, lint, types, packaging, docs). The missing ~10% is a single but critical operational step (git-history remediation) plus release mechanics (no tag yet).

---

## 2. Repository Statistics

(Toolkit only — `flutter_sdk/` deliberately excluded, per project scope.)

| Metric | Value | Evidence |
|---|---|---|
| Total Python source files (`src/`) | 39 | `find src -name "*.py" \| wc -l` |
| Total lines of code (`src/`) | 2,955 | `find src -name "*.py" -exec cat {} + \| wc -l` |
| Total lines of code (`tests/`) | 2,421 | same method over `tests/` |
| Test files | 12 | `find tests -name "test_*.py" \| wc -l` |
| Total tests | 150 | `pytest --collect-only`, summed per file |
| Test result | **150 passed, 0 failed** | `pytest` exit code 0 |
| Test coverage | **93%** (1,477 statements, 101 missed) | `pytest` with `pytest-cov`, measured this session |
| Documentation files (root `*.md`) | 22 | `ls *.md \| wc -l` |
| Documentation files (`docs/`) | 2 (`att_parser.md`, `hci_parser.md`) | `ls docs/` |
| GitHub workflows | 2 (`ci.yml`, `release.yml`) | `ls .github/workflows/` |
| CLI entry points (`pyproject.toml` `[project.scripts]`) | 3 (`revolt-ble-toolkit`, `revolt-ble-gui`, `revolt-ble-live`) | `pyproject.toml` |
| CLI subcommands (main CLI) | 4 (`parse`, `analyze`, `export`, `compare`) | `cli/main.py` |
| GUI modules | 3 substantive + `__init__.py` (`app.py`, `main_window.py`, `widgets.py`) | `src/revolt_ble_toolkit/gui/` |
| Declared package version | `1.0.0` (consistent between `VERSION` and `pyproject.toml`) | direct read |
| Git tags | **None** | `git tag -l` |

---

## 3. Architecture Status

| Module | Status | Completion % | Notes |
|---|---|---|---|
| `parsers/btsnoop` | Complete | 100% | 100% test coverage; handles truncation, unknown packet types, and out-of-range timestamps (`OverflowError` skip-and-log) without crashing. |
| `parsers/att` | Complete | ~97% | 96–98% coverage; one uncovered branch each in `models.py`/`parser.py`. |
| `analyzers/gatt` | Complete | 100% | 100% coverage. |
| `analyzers/protocol` | Complete | ~99% | Heuristic classifier; every classification carries a confidence score + reason string (verified in code, not just docs). |
| `analyzers/compare` | Complete | 100% | Shared `format_diff_report()` used by both CLI and GUI. |
| `exporters/capture_report` | Complete | 100% | 100% coverage. |
| `cli/main.py` | Complete | ~99% | 4 subcommands wired to real analyzer/exporter logic; 1 line uncovered. |
| `live/client.py` | Mostly Complete | 99% | Tested only against a fake Bleak backend (`_FakeClient`/`_FakeScanner`) — no real-hardware validation exists in this repo. |
| `live/cli.py` | Incomplete (untested) | 0% coverage | Thin CLI entrypoint script; exists and is wired to `client.py`, but has no test exercising it. |
| `gui/main_window.py` | Complete | 95% | File menu, recent captures, export/compare actions, shortcuts all present and tested via Qt offscreen backend. |
| `gui/widgets.py` | Complete | 91% | Table/filter/timeline widgets; paint and mouse-click paths tested. |
| `gui/app.py` | Incomplete (untested) | 0% coverage | Thin GUI bootstrap entrypoint; not exercised by any test. |
| `config/settings.py` | Complete | 100% | Layered dataclass → TOML → env-var config, fully covered. |
| `pipeline.py` | Complete | 100% | End-to-end orchestration, fully covered. |
| Packaging (`pyproject.toml`) | Complete | 100% | `python -m build` produces a valid sdist + wheel; `twine check` **PASSED** on both artifacts this session. |
| CI/CD (`.github/workflows/`) | Mostly Complete | ~90% | `ci.yml` runs gitleaks + ruff/black/mypy/pytest; `release.yml` exists but has never been triggered (no tag pushed yet). |
| Git history hygiene | **Incomplete** | **0%** (of the planned remediation) | See §4/§6 — the documented remediation plan was never executed. |

---

## 4. Quality Gate

| Gate | Status | Evidence |
|---|---|---|
| Black | **PASS** | `black --check --diff .` → "All done! 62 files would be left unchanged." |
| Ruff | **PASS** | `ruff check .` → "All checks passed!" |
| MyPy | **PASS** | `mypy src` → "Success: no issues found in 39 source files" |
| Pytest | **PASS** | 150/150 passed, exit code 0 |
| Coverage | **PASS** (with caveats) | 93% overall; two files (`gui/app.py`, `live/cli.py`) are thin entrypoints at 0% coverage — acceptable for bootstrap scripts, but not literally "fully tested." |
| GitHub Actions | **PASS** (structurally) | `ci.yml` and `release.yml` present and internally consistent (correct permissions, correct env vars for headless Qt); **not verified against an actual GitHub Actions run** in this audit (read-only, no push performed). |
| Packaging | **PASS** | `python -m build` succeeds; `twine check` passes on sdist + wheel; version string consistent across `VERSION` and `pyproject.toml`. |
| Documentation | **WARNING** | Extensive (24 files) but includes a large amount of session/audit-trail material (`CLEANUP_REPORT.md`, `FINAL_STATUS.md`, `FINAL_RELEASE_VERIFICATION.md`, `PROJECT_AUDIT.md`, `RELEASE_CHECKLIST.md`, `RELEASE_NOTES.md`, `REMAINING_TASKS.md`, `ROADMAP.md`, `SECURITY_RELEASE_CHECKLIST.md`, `HISTORY_SANITIZATION.md`) alongside user-facing docs. Not incorrect, but noisy for a first-time visitor to the repo root. |
| Security | **FAIL** | See below. `gitleaks` binary is not installed locally (pre-commit hook falls back to a warning, not an enforced scan, on this machine); more importantly, the git-history PII incident documented in `HISTORY_SANITIZATION.md` was **never actually remediated** (see §6, Critical). |

**Security detail (verified this session):**
```
git log --all --oneline | grep -i output
ed1fde2 output folder done
```
This commit — which added `output.zip` and `output/*` files containing real IMEI, SIM ICCID, and a pairing token, per `HISTORY_SANITIZATION.md`'s own inventory — is confirmed present in `git log --all`, and is confirmed reachable from **both `origin/main` and `origin/dev-mann`** after `git fetch origin`. The `git filter-repo` rewrite and force-push described in `HISTORY_SANITIZATION.md` §7–§10 were **not executed**; the current git history matches the pre-remediation state on the public remote.

---

## 5. Release Readiness

| Dimension | Score /10 | Basis |
|---|---|---|
| Architecture | 8 | Clean module boundaries, frozen dataclasses, `TYPE_CHECKING`-guarded imports; a few thin entrypoints (`gui/app.py`, `live/cli.py`) drag it down slightly. |
| Code Quality | 8 | Ruff/Black/MyPy all clean across 39 files. |
| Documentation | 7 | Comprehensive but cluttered with process/audit artifacts rather than a lean user-facing set. |
| Testing | 8 | 150 tests, 93% coverage, GUI exercised via real Qt offscreen paint/mouse events, live client via fake-backend contract tests. |
| Performance | 6 | Per `KNOWN_LIMITATIONS.md`, benchmark numbers are synthetic (no real-device throughput/latency data exists in-repo). |
| Security | **2** | Confirmed live PII/token exposure in public git history; remediation plan exists but was never run. |
| Maintainability | 8 | CI-enforced lint/type/test gates; layered config; clear package structure. |
| Developer Experience | 8 | `DEVELOPER_GUIDE.md`, `CONTRIBUTING.md`, git hooks, and gitleaks docs all present. |
| Reverse Engineering Accuracy | 6 | Heuristics are honestly confidence-scored and never claim certainty they don't have — but accuracy against a real device is unverified in this repo (only fixture/synthetic captures used in tests). |
| Open Source Readiness | 3 | LICENSE/CONTRIBUTING/SECURITY/CODE_OF_CONDUCT all present and correct, but the unresolved PII exposure is a disqualifying blocker for actually publishing. |

**Overall score: 6.4/10** — pulled down almost entirely by the single Security dimension; every other dimension independently scores 6+.

---

## 6. Remaining Work

**Critical**
- Execute the git-history remediation that `HISTORY_SANITIZATION.md` already specifies (`git filter-repo --path output --path output.zip --path scratch/generate_all_outputs.py --invert-paths`) and force-push to `origin`. As of this audit, commit `ed1fde2` (real IMEI, SIM ICCID, pairing token) is still live on `origin/main` and `origin/dev-mann`.
- Treat the exposed pairing token as compromised and rotate/revoke it independent of the git cleanup (per `HISTORY_SANITIZATION.md`'s own advisory — not yet confirmed done).

**High**
- Tag `v1.0.0` and draft the GitHub Release — no tags exist yet (`git tag -l` is empty), so `release.yml` has never run.
- Install `gitleaks` on the local dev machine so the pre-commit hook enforces rather than warns (confirmed absent: `which gitleaks` found nothing on PATH).

**Medium**
- `gui/app.py` and `live/cli.py` are both at 0% test coverage — thin entrypoints, but currently the only two source files with zero test evidence at all.
- Root-level documentation set (10+ files) mixes user-facing docs with session/audit-trail artifacts; consider consolidating before public release for readability (not a correctness issue).

**Low**
- `docs/` has module-level deep-dive docs for only 2 of the parser/analyzer modules (`att_parser.md`, `hci_parser.md`); the others (`btsnoop`, `gatt`, `compare`, `protocol`) have no equivalent standalone doc, only `API_REFERENCE.md`/`MODULE_REFERENCE.md` coverage.

---

## 7. Known Limitations

(Only items that genuinely require new BLE captures, new protocol evidence, external hardware, or external APIs.)

- **Protocol semantics are heuristic, not confirmed**: opcode/category classifications carry confidence scores because the true meaning of the proprietary vehicle-control protocol has never been confirmed against vendor documentation — this requires either vendor cooperation or many more real-world captures to corroborate.
- **No real-hardware validation of the live BLE client**: `live/client.py`'s connect/pair/reconnect logic is tested only against a fake Bleak backend in this repo; validating it end-to-end requires a real RV400-class BLE device.
- **Performance numbers are synthetic**: current benchmarks run against a synthetic capture built from test fixtures, not a real captured session, because the original real-device benchmark data was PII-bearing and had to be discarded. Reproducing real-device performance numbers requires a new, clean capture from actual hardware.

---

## 8. Release Recommendation

**Needs More Development.**

Every technical quality gate that can be checked from the repository itself (tests, coverage, lint, types, packaging, CI/CD config, docs presence) passes. The blocker is not code quality — it is that this audit confirms the git-history PII remediation plan the project already wrote for itself was never carried out, and the exposed data is currently live on the public GitHub remote. That is a data-exposure issue, not a polish item, and it overrides an otherwise near-v1.0.0-ready codebase.

---

## 9. Final Verdict

**NO**

As an independent open-source maintainer, I would not approve merging/publishing this as v1.0.0 today. My reasoning:

- The codebase itself is genuinely strong: 150/150 tests passing, 93% coverage, clean Ruff/Black/MyPy, a package that builds and passes `twine check`, and reasonably honest engineering (heuristics are confidence-scored rather than asserted as fact; `KNOWN_LIMITATIONS.md` exists and is candid).
- But `git log --all` on this exact checkout, right now, shows commit `ed1fde2` — carrying real IMEI, SIM ICCID, and a pairing token — reachable from both `origin/main` and `origin/dev-mann` on a public GitHub remote. The project's own `HISTORY_SANITIZATION.md` correctly identifies this and lays out the exact fix, but that fix has not been run.
- Publishing a v1.0.0 tag or GitHub Release on top of this history would ship the real PII to anyone who clones the repository, regardless of what the working tree currently looks like. That is a disqualifying, not-yet-resolved issue independent of everything else measured above.
