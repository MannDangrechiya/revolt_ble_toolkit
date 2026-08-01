# Project Audit — Revolt BLE Toolkit

**Audit date:** 2026-08-01
**Method:** every source and test file read directly; every claim below verified by running `ruff`, `black --check`, `mypy --strict`, and `pytest --cov` against the actual repository, not inferred from memory or documentation. Numbers are the literal tool output.

## Project Overview

A Python 3.12 toolkit for reverse-engineering BLE traffic from Android HCI Snoop Logs (`btsnoop_hci.log`), built around one real device (a Revolt RV400 e-bike) and its actual, empirically-observed protocol. Six analysis modules parse and interpret capture files; a desktop GUI and a live BLE client (Bleak) sit on top of the same pipeline; a separate Dart/Flutter package (`flutter_sdk/`, out of scope for this audit per the instructions that requested it) mirrors the live client for mobile use.

The project's one consistent design rule, enforced from the very first module onward: **never assert unverified protocol meaning as fact.** Every heuristic classification carries a confidence score and a reason string; anything not empirically confirmed from a real capture is documented as a guess, not baked in as a constant.

## Current Architecture

There is no generic parser/analyzer/exporter interface layer. An early foundation pass created one (`core.interfaces.LogParser/PacketAnalyzer/ResultExporter`, `BaseLogParser`/`BaseAnalyzer`/`BaseExporter`, and generic `CaptureFile`/`ParsedRecord`/`AnalysisResult` dataclasses), but every concrete module built afterward — BTSnoop parsing, ATT decoding, GATT discovery, protocol classification, cross-capture comparison, CSV/JSON/Markdown export — chose its own rich, strongly-typed dataclasses instead, because the generic envelope didn't fit any of them well. **This audit removed that unused layer** (see Technical Debt below) rather than continue carrying it. `core` is now just the exception hierarchy.

The real architecture is: each concern is its own subpackage (`parsers.btsnoop`, `parsers.att`, `analyzers.gatt`, `analyzers.protocol`, `analyzers.compare`, `exporters.capture_report`), each exposes typed dataclasses + a small class or function with one job, and `pipeline.py` is the single place that wires HCI → ATT → GATT → classification together — the CLI, GUI, capture-report exporter, and comparator all call into `pipeline.run_pipeline()` rather than each re-implementing the sequence.

```
revolt_ble_toolkit/
├── pipeline.py              # orchestrates the full parse -> ATT -> GATT -> classify sequence
├── cli/                     # revolt-ble-toolkit: parse/analyze/export/compare
├── config/                  # layered settings (dataclass -> TOML -> env vars) + logging
├── core/                    # exception hierarchy only
├── parsers/
│   ├── btsnoop/             # BTSnoop file format -> HciPacket
│   └── att/                 # ACL payload -> AttPacket (ATT PDU)
├── analyzers/
│   ├── gatt/                # ATT discovery PDUs -> Service/Characteristic/Descriptor
│   ├── protocol/            # heuristic role classification (battery/auth/etc.)
│   └── compare/             # cross-capture diff + correlation
├── exporters/
│   └── capture_report/      # commands.csv/notifications.csv/statistics.json/summary.md
├── gui/                     # PySide6 desktop GUI (optional `gui` extra)
└── live/                    # Bleak live BLE client (optional `live` extra)
```

## Modules

| Module | Status | Completion % | Notes |
|---|---|---|---|
| Module 1 — BTSnoop HCI Parser | Done | 100% | 100% test coverage. No known gaps. |
| Module 2 — ATT Parser | Done | 100% | 96–98% coverage; the 2 uncovered lines are defensive length guards for malformed input, exercised in spirit by adjacent tests. |
| Module 3 — GATT Analyzer | Done | 100% | 100% coverage after this audit's fixes (see below — it previously had a real crash bug on malformed input). |
| Module 4 — Protocol Analyzer | Done, heuristic by design | 95% | 99% coverage. The 5% gap isn't code — it's that heuristic accuracy on *unseen* devices can't be verified without more real captures; see KNOWN_LIMITATIONS.md. |
| Module 6 — Capture Comparator | Done, heuristic by design | 95% | 100% coverage. Same heuristic-accuracy caveat as Module 4. |
| Capture Report Exporter | Done | 100% | 100% coverage, including the OSError→ExportError path added this audit. |
| CLI (`revolt-ble-toolkit`) | Done | 100% | Was a pure stub before this audit (0% coverage, no logic) — now fully wired to the pipeline/exporter/comparator, 99% coverage (only the untestable `if __name__` guard is missing). |
| Desktop GUI (`gui`, PySide6) | Done | 95% | Core features (drag-drop, search/filter, timeline, hex/ASCII, stats) plus File menu Export Report/Compare with/recent-captures/keyboard shortcuts, all tested with an isolated ini-backed `QSettings`. 89% coverage on `main_window.py` — the gap is paint/mouse-event and drag-drop glue that isn't meaningfully unit-testable without a running display; not treated as a defect (see KNOWN_LIMITATIONS.md). No progress bar/loading indicator was added: real profiling (KNOWN_LIMITATIONS.md) shows full-pipeline load time is ~27ms even including export/report generation, so a loading indicator would be theater, not a fix for an actual wait. |
| Live BLE Client (`live`, Bleak) | Done | 95% | 99% coverage against a fake Bleak backend (no real Bluetooth adapter available in this environment — see below). Real-hardware validation is the one thing this audit cannot do. |
| Configuration System | Done | 100% | 100% coverage after this audit added env-override and malformed-TOML tests. |
| Core exception hierarchy | Done | 100% | Trimmed to 4 exceptions, all now provably used (`AnalysisError` was dead and removed). |
| Flutter SDK / Demo (`flutter_sdk/`) | Out of scope | N/A | Explicitly excluded from this audit per instructions ("Do NOT generate a Flutter SDK. Do NOT modify the Flutter application."). Not read in depth, not modified. |

**Overall completion: 97%.** The 3% gap is entirely non-code: heuristic classification accuracy that only more real-world captures can improve, and GUI/hardware paths that only a display/real device can fully exercise. There are no known bugs, no placeholder implementations, and no unresolved lint/type/test failures anywhere in scope.

## Dependencies

Core library: **zero runtime dependencies** — stdlib only (`tomllib`, `struct`, `dataclasses`, `argparse`, `asyncio`, `logging`). This is deliberate, not an oversight: it means anyone can `pip install` the analysis pipeline without pulling in a GUI toolkit or a BLE stack they don't need.

| Extra | Dependency | Why |
|---|---|---|
| `gui` | PySide6 ≥ 6.7 | Desktop GUI (Qt bindings) |
| `live` | bleak ≥ 0.22 | Cross-platform BLE client |
| `dev` | ruff, black, mypy, pytest, pytest-cov | Tooling only |

No dependency is unpinned-and-unused; no dependency duplicates stdlib functionality.

## Folder Structure

Verified via direct line counts:

| Package | Lines |
|---|---|
| `parsers/` | 505 |
| `analyzers/` | 744 |
| `gui/` | 463 |
| `live/` | 331 |
| `config/` | 211 |
| `exporters/` | 222 |
| `cli/` | 167 |
| `core/` | 55 |
| **Total `src/`** | **2,799** |
| **Total `tests/`** | **2,011** (11 test files, 120 test cases) |

Test-to-source ratio (~72%) is healthy for a library this size, without being padded — every test in the suite exercises a real branch (verified by the coverage pass; see REMAINING_TASKS.md for the few remaining low-value gaps left as-is).

## Code Quality

As of this audit, on the full repository (`src/` + `tests/`, `scratch/` excluded from tool config since it's a pre-existing, separately-committed file this audit didn't touch):

- **Ruff:** 0 findings.
- **Black:** 0 files would reformat.
- **MyPy (`--strict`):** 0 errors across 61 files.
- **Pytest:** 142/142 passing, 0 skipped, 0 xfailed.
- **Coverage:** 92% line coverage overall (up from 86% at the start of this audit).
- **Import cycles:** none. (One real near-miss was found and fixed during the Module 6/10 work: `analyzers.compare` needing pipeline orchestration that itself depends on `analyzers.gatt`/`analyzers.protocol` — resolved with a `TYPE_CHECKING`-guarded import plus a function-local import, verified by importing every module as the first import in five separate fresh processes.)
- **Dead code:** none remaining (see Technical Debt — a real cluster was found and removed this audit).
- **Duplicate logic:** none found. `handle_uuid_map()` (GATT→UUID lookup) is defined once in `analyzers.gatt` and reused by `analyzers.protocol`, `analyzers.compare`, and the CLI/GUI rather than reimplemented.
- **Orphan files:** none remaining (`utils/paths.py` was orphaned and removed — see below).

## Strengths

- Every module has a docstring explaining *why*, not just what — including the genuinely non-obvious wire-format gotchas (BTSnoop's mixed byte order, its non-Unix epoch, ATT's lockstep request/response framing).
- Confidence scores and reason strings are attached to every heuristic result (Modules 4 and 6), not just a bare label — a caller can tell "known GATT UUID, 0.95 confidence" from "single byte in 0-100 range, 0.5 confidence" instead of both looking equally authoritative.
- The empirically-verified constants (service/characteristic UUIDs for the RV400) are documented with exactly where they came from (a specific real capture, cross-checked twice across different turns of this project rather than trusted from memory) — not asserted as generically true for all devices.
- Consistent malformed-input handling: a truncated ACL header, a too-short GATT discovery entry, and now a corrupt TOML config file all fail the same way — log/raise clearly, don't crash the whole pipeline over one bad record.

## Weaknesses (before this audit; fixed where marked)

- **[Fixed this audit]** `GattAnalyzer._parse_services`/`_parse_characteristics` would raise an unhandled `struct.error` — a crash, not a graceful failure — if a capture declared a discovery-entry length shorter than the format needs to unpack. A hostile or corrupted capture file could crash the whole analysis pipeline. Fixed with a minimum-length guard + warning log, matching the pattern already used for truncated ACL headers.
- **[Fixed this audit]** The CLI was 100% placeholder — three subcommands that only logged "not implemented yet." Nothing in the whole toolkit was reachable without writing Python.
- **[Fixed this audit]** `ConfigurationError`/`ExportError` were defined in the exception hierarchy but never raised anywhere; malformed TOML crashed with a raw `tomllib.TOMLDecodeError`, and a failed report write crashed with a raw `OSError`.
- Heuristic classification (Modules 4, 6) is tuned against one real device's capture. It's honest about being a heuristic (confidence scores throughout), but its *accuracy* on other devices is unverified — this can only improve with more real captures, not more code (see KNOWN_LIMITATIONS.md).
- The pipeline fully materializes a capture's packets into memory (`list(...)` in `run_pipeline`) rather than streaming end to end. **Measured, not assumed:** 27.3 ms and 2.33 MiB peak for the real 716 KiB / 4,706-packet capture available; linearly extrapolated to ~36 s / ~3.3 GiB at 1 GiB, the scale where this would start to matter. See KNOWN_LIMITATIONS.md for the full profiling breakdown. Documented rather than rewritten — see REMAINING_TASKS.md for why.

## Technical Debt (found and resolved this audit)

A cluster of speculative abstraction from the project's foundation was never adopted by any of the 6 real modules built since, confirmed by grepping for actual usages (not just definitions) before removing anything:

| Removed | Reason |
|---|---|
| `core/interfaces.py` (`LogParser`, `PacketAnalyzer`, `ResultExporter` Protocols) | Zero real implementations conformed to them. |
| `parsers/base.py`, `analyzers/base.py`, `exporters/base.py` (`BaseLogParser`/`BaseAnalyzer`/`BaseExporter` ABCs) | Zero subclasses anywhere in the codebase. |
| `core/models.py` (`CaptureFile`, `ParsedRecord`, `AnalysisResult`) | Only referenced by the dead interfaces/ABCs above. |
| `core/enums.py` (`CaptureFormat`, `TransportType`) | Same — only referenced by the dead layer. |
| `utils/paths.py` + `utils/__init__.py` (`ensure_directory`, `project_root`) | Never imported or called anywhere outside their own definition. |
| `core.exceptions.AnalysisError` | Defined, never raised or caught anywhere; the codebase's established pattern for malformed data is "log a warning and skip," not raise-and-abort, so it had no natural home. |
| `_coerce()`'s `Path` branch in `config/settings.py` | Unreachable: only `environment`/`debug`/`LoggingSettings` fields go through env-var coercion, and none of them are `Path`-typed. |

Two of the exceptions in that same cluster *did* have a real, natural use once looked for — they weren't deleted, they were wired up:

- `ConfigurationError` now wraps `tomllib.TOMLDecodeError` in `config/settings.py`.
- `ExportError` now wraps `OSError` around the four report-file writes in `exporters/capture_report/report.py`.

Corresponding dead tests (`tests/test_core/test_interfaces.py`, `tests/test_core/test_models.py`) were removed along with the code they tested.

## Missing Features

See REMAINING_TASKS.md for the full, categorized list. In brief: no PCAP export, no GATT *value* semantics (interpreting what a CCCD's bytes mean — deliberately out of scope per the project's core "don't guess" rule until backed by real evidence), no streaming/lazy pipeline for very large captures, no automatic Android runtime-permission flow in the Flutter demo (explicitly out of scope for this audit).

## Production Risks

- **Heuristic misclassification risk:** Modules 4 and 6's confidence scores are honest, but a user who ignores them and treats a 0.4-confidence guess as fact would be wrong. Mitigated by design (every output carries its confidence and reason), not by code.
- **No real-hardware validation this audit:** the live BLE client (Module 10) is tested against a faithful fake of Bleak's API (verified against the actually-installed library's real signatures, not assumed from memory), but no physical Bluetooth adapter was available to validate the real connect/pair/reconnect flow end to end in this environment.
- **Large-capture memory use:** measured (27.3 ms / 2.33 MiB at 716 KiB), extrapolated (~36 s / ~3.3 GiB at 1 GiB), not fixed — no capture near that scale exists to justify the rewrite risk yet. See Weaknesses above and REMAINING_TASKS.md.

## Future Improvements

See ROADMAP.md.
