# Architecture

## The one rule everything else follows

No module asserts protocol meaning it hasn't verified. A parser exposes raw bytes; an analyzer that guesses at meaning always attaches a confidence score and a reason string. This shows up everywhere: Module 2's ATT parser doesn't decode L2CAP payloads, Module 3's GATT analyzer doesn't interpret characteristic values, Modules 4 and 6's classifiers never return a bare label without `(confidence, reason)`, and the live client (Module 10) exposes every notification's raw bytes rather than trying to parse telemetry.

## No generic interface layer — and why

An early foundation pass built a classic "ports and adapters" layer: `core.interfaces.LogParser`/`PacketAnalyzer`/`ResultExporter` (structural `Protocol`s) and `BaseLogParser`/`BaseAnalyzer`/`BaseExporter` (ABCs), meant to let every concrete parser/analyzer/exporter conform to one shared shape (`CaptureFile` → `ParsedRecord` → `AnalysisResult`).

Six concrete modules were built after that foundation (BTSnoop parsing, ATT decoding, GATT discovery, protocol classification, cross-capture comparison, capture-report export), and **none of them used it.** Each one's actual data didn't fit the generic envelope well — an `HciPacket` has ACL-specific fields, a `Service` has a characteristic tree, a `ClassifiedPacket` has a confidence score — so each module defined its own frozen dataclasses instead, and the generic layer sat unused.

A v1.0 audit confirmed this by grepping for actual usages, not just definitions, before deciding: zero real call sites anywhere outside the layer's own definition and its own tests. It was removed. `core` is now just the exception hierarchy (`ToolkitError` and four subclasses). If a future module genuinely needs a shared abstraction across parsers, add it *then*, once two real implementations actually want the same shape — not speculatively.

## Module map

```
parsers.btsnoop   →  HciPacket            (raw HCI framing: timestamp, direction, ACL header)
parsers.att       →  AttPacket            (ATT PDU: opcode, attribute handle, value bytes)
analyzers.gatt    →  Service/Characteristic/Descriptor   (GATT hierarchy from discovery PDUs)
analyzers.protocol→  ClassifiedPacket     (heuristic role: battery/auth/telemetry/... + confidence)
analyzers.compare →  HandleDiff           (cross-capture diff + heuristic correlation)
exporters.capture_report → commands.csv / notifications.csv / statistics.json / summary.md
pipeline.py       →  orchestrates the four stages above end to end
gui / live / cli  →  three different front ends onto pipeline.py
```

Dependency direction is strictly left-to-right / top-to-bottom in that list — `parsers` never imports `analyzers`; `analyzers.protocol` and `analyzers.compare` both depend on `analyzers.gatt` (for `handle_uuid_map`) but not on each other; `pipeline.py` depends on all four analysis stages; `gui`/`live`/`cli` depend on `pipeline.py` and the analyzers/exporters directly, never on each other.

One real near-cycle exists and is deliberately broken: `analyzers.compare` needs to run the full pipeline (to compare two captures), but `pipeline.py` itself imports `analyzers.gatt`/`analyzers.protocol`. Importing `pipeline.PipelineResult`/`run_pipeline` at module level from inside `analyzers.compare` would create a cycle the moment `analyzers/__init__.py` eagerly imports the `compare` subpackage. This is resolved with a `TYPE_CHECKING`-only import for the type hint and a function-local import inside `compare_captures()` — a standard, narrow way to break an import cycle without restructuring the package layout. Verified by importing every one of `exporters`, `analyzers`, `pipeline`, `analyzers.compare`, and `gui.main_window` as the *first* import in five separate fresh Python processes.

## Configuration

`config.settings.get_settings()` returns a cached, immutable `AppSettings`, layered:

1. Dataclass defaults
2. `config/default.toml` (or a path you pass explicitly)
3. `REVOLT_*` environment variables (highest priority)

Malformed TOML raises `ConfigurationError` (not a raw `tomllib.TOMLDecodeError`) with the offending file path in the message. Nothing else in the codebase reads a config file or environment variable directly — every consumer goes through `get_settings()`.

## Logging

One package-root logger (`config.logging_config.configure_logging`), console + rotating file handler. Every module gets its logger via `get_logger(__name__)` — never `logging.getLogger` directly, and never `print()` for anything other than CLI user-facing output.

## Error handling

Every toolkit-specific failure is a `ToolkitError` subclass: `ParsingError` (capture file structurally broken), `ConfigurationError` (bad config), `ExportError` (report write failed), `LiveClientError` (BLE connection/pairing failed). Malformed *data within* an otherwise-valid file (a truncated ACL header, a too-short GATT discovery entry) is not an exception at all — it's a logged warning and a skipped record, so one bad packet doesn't abort analysis of the rest of a real-world capture that's mostly fine.

See PIPELINE.md for the data flow in detail, MODULE_REFERENCE.md / API_REFERENCE.md for per-module and per-symbol reference, and KNOWN_LIMITATIONS.md for what this architecture deliberately does not attempt.
