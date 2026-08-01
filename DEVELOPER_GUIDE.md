# Developer Guide

## Setup

```bash
uv sync --all-extras          # preferred
# or
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev,gui,live]"

git config core.hooksPath .githooks   # activate the sensitive-data pre-commit hook (see below) — per-clone, not shared automatically
```

Install [gitleaks](https://github.com/gitleaks/gitleaks) too if you want the secret scan to actually run locally (the hook above skips it with a warning if it's missing) — see [SECRETS_POLICY.md](SECRETS_POLICY.md).

## The verification gate

Every change, no matter how small, must pass all four before it's considered done:

```bash
ruff check .
black --check .
mypy
pytest
```

`ruff`/`black`/`mypy` scope to `src/` and `tests/` only. `pytest` runs with coverage on by default (`--cov=revolt_ble_toolkit --cov-report=term-missing` in `pyproject.toml`); GUI tests need `QT_QPA_PLATFORM=offscreen` set if you're running headless (no real display).

Don't commit ad-hoc/one-off scripts or their generated output at the repo root — a prior `scratch/`+`output/` pair that did this leaked a real device's IMEI/SIM serial/pairing token into git history before being removed in the v1.0 audit. Use an untracked local directory (or this repo's `reports/`, which is `.gitignore`d) for anything you don't want reviewed and shipped.

If `black` or `ruff --fix` changes files, re-run the full gate afterward — don't assume a fix didn't introduce a new issue.

## Conventions (read the existing modules before adding a new one)

- **One package per concern**, under `src/revolt_ble_toolkit/`. Each has its own `models.py` (frozen, `slots=True` dataclasses) and `analyzer.py`/`parser.py` (a class or function with one job). `__init__.py` re-exports the public surface; internals are prefixed `_`.
- **No generic interface layer.** Don't reach for `Protocol`/ABC abstractions for a new parser/analyzer/exporter unless *two* real implementations already want the same shape — see ARCHITECTURE.md for why the last attempt at this was removed.
- **Dataclasses over dicts.** Every domain object (`HciPacket`, `AttPacket`, `Service`, `ClassifiedPacket`, `HandleDiff`, `RawPacket`, ...) is a `@dataclass(frozen=True, slots=True)`. Enums for closed sets of values (`HciPacketType`, `AttOpcode`, `PacketCategory`, ...).
- **Logging, never print, in library code.** `from revolt_ble_toolkit.config.logging_config import get_logger; logger = get_logger(__name__)`. CLI/GUI code prints/renders for the user — that's the one place `print()`/Qt widgets are correct.
- **Exceptions.** Structural failures (bad file, bad config, failed export, failed BLE connection) raise a `ToolkitError` subclass from `core.exceptions` — check whether an existing one fits before adding a new one. Malformed *data within* an otherwise-valid input (a truncated record, a too-short discovery entry) is a logged warning + skip, not an exception — match this pattern, don't abort a whole capture's analysis over one bad packet.
- **Never assert unverified protocol meaning.** If you're tempted to hardcode "this handle means X," check: is it confirmed from a real capture (cite which one, like the RV400 UUID constants do), confirmed by the Bluetooth Core Spec itself (like a CCCD's standard bit meanings would be), or a guess? Guesses get a confidence score and a reason string, never a bare assertion. See KNOWN_LIMITATIONS.md's "Protocol Confidence Levels."
- **Mark deliberate shortcuts.** A real simplification (a fixed retry delay with no backoff cap, a one-fragment-per-ACL-packet assumption) gets a comment naming the ceiling and the upgrade path, not silence.

## Adding a new module

1. New subpackage under `src/revolt_ble_toolkit/<area>/<name>/` with `__init__.py`, `models.py`, and the logic file.
2. Re-export the public surface from your new `__init__.py`, then from the parent area's `__init__.py` (e.g. `analyzers/__init__.py`).
3. Tests under `tests/test_<area>/test_<name>.py` — build synthetic input with the existing fixture helpers (`tests/test_parsers/fixtures.py` for BTSnoop-level bytes) rather than depending on a real capture file.
4. Run the full verification gate. Don't call it done on "tests pass" alone — check coverage output for branches you didn't actually exercise.
5. If your module needs a new dependency, make it an optional extra in `pyproject.toml` (see how `gui` and `live` are structured) unless it's genuinely required for the core pipeline to function at all.

## Testing conventions

- Build synthetic capture bytes with `tests/test_parsers/fixtures.py`'s helpers rather than depending on a real `.log` file in the repo.
- For Qt (GUI) and Bleak (live client) code, don't try to run the real backend in tests — GUI tests run headless via `QT_QPA_PLATFORM=offscreen`; live-client tests use a hand-written fake of Bleak's actual API (verified against the real installed library first, not assumed — see `tests/test_live/test_client.py`'s `_FakeClient`).
- Test private helpers directly (e.g. `GattAnalyzer._parse_services`, `CaptureComparator._correlate`) when they contain real branching logic that the public API can't reach every path of — this is established practice in this codebase, not a workaround.

## Repository layout reference

See ARCHITECTURE.md for the module dependency map, MODULE_REFERENCE.md for what each module does, API_REFERENCE.md for the public symbol list.
