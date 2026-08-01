# Release Checklist — Open-Source Readiness

Verified item by item against the actual repository, not assumed. `src/` protocol/parsing logic was not touched in this pass — everything below is packaging, docs, and release infrastructure.

## 1. README — verified from scratch

Read the whole file top to bottom against the real repo. Found and fixed:
- The "Project layout" tree didn't list the new root files this pass added (`LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/workflows/`) — added.
- No badges, no License section, no Contributing section — all added (see §5, §6).
- Everything else (Architecture, Configuration, Logging, Modules, Roadmap sections) still matches the real source — this was already cross-checked by an independent pass in the prior turn and nothing has drifted since.

## 2. Installation instructions — verified

Both documented paths checked:
- **`pip` path** (`python -m venv .venv`, `pip install -r requirements-dev.txt`, `pip install -e ".[gui,live]"`) — this is exactly how this session's own working environment was set up and used for every verification in this whole effort; confirmed working.
- **`uv` path** (`uv sync --all-extras`) — **not runnable in this environment** (`uv` isn't installed here: `uv --version` → command not found). Structurally correct (mirrors the same `pyproject.toml` extras/scripts already confirmed working via `pip`), but not independently executed. Flagging honestly rather than claiming a check that didn't happen.

## 3. CLI examples — verified live, not just read

Ran directly against this environment's venv:
- `revolt-ble-toolkit --version` → `revolt-ble-toolkit 1.0.0` ✓
- `revolt-ble-toolkit --help` → lists `parse|analyze|export|compare` exactly as documented ✓
- `revolt-ble-toolkit export --help` → `--out-dir` flag exists as documented ✓
- `revolt-ble-toolkit compare --help` → `capture1 capture2` positional args match ✓
- `revolt-ble-gui [path]` → `gui/app.py`'s `main()` reads `sys.argv[1]` and calls `load_capture()` exactly as the README's `revolt-ble-gui btsnoop_hci.log` example claims ✓
- `revolt-ble-live --pair TOKEN123` → `live/cli.py`'s argparse has `--address`/`--name`/`--pair`/`--save` exactly matching the README/module docstring ✓

## 4. Screenshots — attempted, honestly not shipped

No screenshots existed. Attempted to generate a real one: rendered `MainWindow` off-screen (`QT_QPA_PLATFORM=offscreen`, the same technique this project's own GUI tests use) with a synthetic capture loaded, then `.grab()`'d a PNG. **Result: all text rendered as tofu/missing-glyph boxes** — this sandboxed Linux/Windows-hybrid environment's offscreen Qt platform has no working font backend, a known class of headless-Qt limitation, not a bug in the app itself. Shipping a screenshot with every label as a box would look worse than no screenshot. Deleted the broken attempt rather than ship it.

**Not resolved — needs a real display environment** (a dev machine, or a CI job with `xvfb-run` instead of the offscreen plugin) to actually produce usable screenshots. Left as a follow-up, not faked.

## 5. Badges — none existed, added 3

```
[![CI](...)](...)                          — live, points at the new .github/workflows/ci.yml
[![License: MIT](...)](LICENSE)            — static, now backed by a real LICENSE file
[![Python 3.12+](...)](pyproject.toml)     — static, matches requires-python = ">=3.12"
```

**Not added:** a PyPI version badge — the package isn't published to PyPI yet (see §13), so that badge would 404. Add it once `release.yml`'s PyPI-publish step (currently a documented no-op) is actually wired up.

## 6. License — was missing entirely, added

`pyproject.toml` declared `license = { text = "MIT" }` and the MIT classifier, but there was **no `LICENSE` file at the repo root** — a real gap; GitHub wouldn't have detected a license at all, and a `pip`-installed sdist/wheel wouldn't have bundled one. Added `LICENSE` (MIT, standard text, copyright holder matching `pyproject.toml`'s `authors` field). Added a License section to `README.md` linking to it.

**Known gap outside this pass's scope:** `flutter_sdk/LICENSE` is a literal, unfilled `TODO: Add your license here.` placeholder from the Flutter project template. Not touched — `flutter_sdk/` is explicitly out of scope for modification in this project's standing convention — but worth flagging to the repo owner before that package is treated as release-ready on its own.

## 7. CONTRIBUTING.md — was missing, added

Kept deliberately short: points to the already-thorough `DEVELOPER_GUIDE.md` for setup/conventions/the verification gate instead of duplicating it, states the PR process, and cross-links `SECURITY.md`/`CODE_OF_CONDUCT.md`.

## 8. SECURITY.md — was missing, added

Standard vulnerability-reporting policy (private email report, not a public issue; supported version 1.0.x; scope includes the Flutter SDK). Deliberately does **not** reference the git-history PII incident tracked in `HISTORY_SANITIZATION.md` — whether/how to publicly disclose that is the repo owner's call to make deliberately, not something a new public-facing policy doc should preempt.

## 9. CODE_OF_CONDUCT.md — was missing, added

Contributor Covenant v2.1 (the current standard), enforcement contact set to the same maintainer email used in `SECURITY.md`.

## 10. `pyproject.toml` metadata — verified, one real bug fixed

- `[project.urls]` had **`Repository = "https://example.com/revolt-ble-toolkit"`** — a placeholder that was never updated to the real repo. Fixed to the actual GitHub URL, and added `Issues` and `Changelog` links.
- `name`, `version`, `description`, `readme`, `requires-python`, `license`, `authors`, `keywords`, `classifiers`, `dependencies`, `optional-dependencies`, `scripts` — all read and cross-checked against the real package structure and console-script targets; all correct, nothing else to fix.
- Confirmed `pyproject.toml` still parses as valid TOML after edits (`tomllib.load` succeeded).

## 11. Package version — verified consistent across every source

| Source | Value |
|---|---|
| `VERSION` | `1.0.0` |
| `pyproject.toml` `version` | `1.0.0` |
| `src/revolt_ble_toolkit/__init__.py` `__version__` | `1.0.0` |
| `revolt-ble-toolkit --version` (live run) | `revolt-ble-toolkit 1.0.0` |

All four agree. No action needed.

## 12. GitHub Actions — none existed, added `.github/workflows/ci.yml`

Runs on every push/PR to `main`: installs the package with the `dev`/`gui`/`live` extras on Python 3.12, then `ruff check .` → `black --check .` → `mypy` → `pytest` (with `QT_QPA_PLATFORM=offscreen` for the GUI tests), matching this project's own documented verification gate exactly.

**Includes a real, non-obvious fix attempt, not independently confirmed:** a bare `ubuntu-latest` runner is missing the shared libraries PySide6's offscreen platform plugin needs (`libegl1`, `libgl1`, `libxkbcommon0`, `libxkbcommon-x11-0`, `libdbus-1-3`) even for headless-only rendering — a well-known class of CI failure for Qt-based Python projects. Added an `apt-get install` step for these. **This workflow has not actually been run on GitHub Actions from this environment** (no network access to trigger/observe a real Actions run here) — treat the first real push as the actual test of this file, and be ready to add another missing `apt` package if that first run still fails on an import error.

## 13. Releases workflow — none existed, added `.github/workflows/release.yml`

Triggers on pushing a `v*.*.*` tag: builds the sdist/wheel (`python -m build`) and attaches them to a GitHub Release (`softprops/action-gh-release`).

**Deliberately does not publish to PyPI.** That requires either a PyPI API token stored as a repo secret or PyPI Trusted Publishing configured on PyPI's side for this exact repo — neither exists, and setting up a publish step against an untrusted/unconfigured target could silently fail or, worse, publish under the wrong identity. Left as a clearly-commented no-op for the repo owner to wire up once one of those two prerequisites is actually in place.

## Verification after all changes

```
150 passed
ruff check src/ tests/     → All checks passed!
black --check src/ tests/  → All done! 62 files would be left unchanged.
mypy (bare, src/+tests/)   → Success: no issues found in 62 source files
pyproject.toml             → parses as valid TOML
```

No `src/` protocol/parsing logic was modified in this pass — every change above is packaging metadata, documentation, or release infrastructure.

## Still open before a public release (carried over from prior passes, not re-litigated here)

- The git-history PII exposure — see `HISTORY_SANITIZATION.md` / `SECURITY_RELEASE_CHECKLIST.md`. **This remains the actual blocker**, independent of anything in this checklist.
- Real screenshots (§4).
- `flutter_sdk/LICENSE` placeholder (§6).
- The CI workflow's first real run is unverified (§12).
