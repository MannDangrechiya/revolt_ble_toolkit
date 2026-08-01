# Roadmap

For the concrete, estimated, dependency-tracked backlog, see REMAINING_TASKS.md. This file is the higher-level direction.

## Near-term (real evidence, not more guessing)

The toolkit's classification accuracy (Modules 4 and 6) improves with more real captures of the RV400 in more states — charging, different ride modes, GPS actually moving — not with more code. This is the single highest-value thing to do next, and it's data collection, not development.

## Medium-term

- **PCAP/PCAPNG export**, so a capture can be opened directly in Wireshark alongside this toolkit's own CSV/JSON/Markdown output.
- **GUI parity with the CLI**: export and compare, currently CLI-only, wired into the desktop app as menu actions.
- **GUI polish**: recent-files list, keyboard shortcuts — both cheap, both named directly in the original "professional UI" ask.
- **Standard-defined GATT value semantics**: things the Bluetooth Core Spec itself defines generically (e.g. a CCCD's two bytes), as distinct from device-specific meaning that needs a real capture to confirm.

## Long-term / conditional

- **Streaming pipeline for very large captures.** Not worth building speculatively — the current fully-materialized-in-memory pipeline handles every real capture tested (thousands of packets, sub-second) without strain. Revisit only once a real capture is actually large enough to need it, and profile that specific capture before redesigning around a guessed bottleneck.
- **Device-specific GATT value interpretation** (what a specific characteristic's bytes actually mean beyond the standard spec) — strictly gated on new real captures providing the evidence. This project's one non-negotiable rule is that this never gets guessed at.
- **Support for a second physical device**, if one becomes available — would validate whether the empirically-derived UUIDs and heuristic thresholds generalize past the single unit this was built against, or are specific to it.

## What's explicitly not planned

- A generic parser/analyzer/exporter plugin interface. Tried once, never adopted by six real modules, removed — see ARCHITECTURE.md. Don't rebuild it speculatively; if two real future modules genuinely want to share a shape, extract it *then*.
- Guessing at protocol meaning ahead of evidence, anywhere, ever. This is the project's core value, not a temporary constraint waiting to be relaxed.
