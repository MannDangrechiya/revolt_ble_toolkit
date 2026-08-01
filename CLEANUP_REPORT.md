# Cleanup Report — Non-Production Artifact Removal

## Deleted

| Item | What it was | Why removed |
|---|---|---|
| `reports/*` (9 files: `ascii_strings.txt`, `commands.csv`, `notifications.csv`, `packet_pairs.csv`, `protocol.md`, `statistics.json`, `summary.md`, `telemetry_candidates.csv`, `write_requests.csv`) | Generated capture-report output, gitignored (never committed) | Disposable output of `exporters.capture_report`/the CLI's `export` command — recreated on demand. **Also worth knowing:** several of these files still contained the same real IMEI/SIM-serial/personal-path data described in `HISTORY_SANITIZATION.md` (confirmed by grep before deleting) — this was a local-disk-only copy that git never saw, but it's gone now too. |
| `logs/revolt_ble_toolkit.log` (450 KiB) | Generated runtime log | Disposable, gitignored, regenerated on next run. `logs/.gitkeep` kept so the directory still exists for the app to write into. |
| `src/**/__pycache__/`, `tests/**/__pycache__/` (10 directories) | Python bytecode caches | Regenerated automatically by the interpreter; never useful to keep around. |
| `RELEASE_AUDIT.md` | A one-off independent-audit snapshot from an earlier pass in this session | Its actionable findings are already folded into the docs that matter (`PROJECT_AUDIT.md`, `CHANGELOG.md`, `FINAL_STATUS.md`, `KNOWN_LIMITATIONS.md`); its one still-unresolved item (the git-history exposure) now has its own live, actively-tracked home in `HISTORY_SANITIZATION.md` and `SECURITY_RELEASE_CHECKLIST.md`. Keeping it around would just be a second, increasingly-stale copy of numbers that already drifted (it said "143/143 tests, 92%"; the real current numbers are 150/93%). Fixed the 3 dangling `RELEASE_AUDIT.md` cross-references left in `CHANGELOG.md`, `PROJECT_AUDIT.md`, and `SECURITY_RELEASE_CHECKLIST.md` after removing it. |
| `scratch/generate_all_outputs.py`, `output/`, `output.zip` | Ad-hoc script + its committed output containing real personal device data | Already removed in the previous pass (see `HISTORY_SANITIZATION.md`) — not re-listed as new work here, just confirmed still gone. |

## Kept — reviewed for "duplicate/obsolete" and judged not to be

- **`ARCHITECTURE.md` / `PIPELINE.md` / `DEVELOPER_GUIDE.md` / `MODULE_REFERENCE.md` / `API_REFERENCE.md`** — each covers a genuinely distinct angle (why the codebase is shaped this way / the data-flow / how to contribute / per-module summary / symbol list). No two of these say the same thing.
- **`PROJECT_AUDIT.md` / `FINAL_STATUS.md` / `RELEASE_NOTES.md` / `CHANGELOG.md` / `ROADMAP.md` / `REMAINING_TASKS.md` / `KNOWN_LIMITATIONS.md`** — these do share some facts (test count, coverage %, a couple of the same limitations), but each has a distinct purpose and audience: a full audit trail, a short status snapshot, a release announcement, a chronological change log, a forward-looking vision doc, an actionable categorized backlog with effort estimates, and a confirmed/heuristic/unknown protocol-fact ledger. Merging these would lose real structure for a marginal reduction in file count — not worth the risk of quietly dropping authored analysis. Left as-is.
- **`HISTORY_SANITIZATION.md` / `SECURITY_RELEASE_CHECKLIST.md`** — these are *not* old audit outputs; they document unresolved work (the git-history rewrite hasn't happened yet, several checklist items are still unchecked). Deleting these would destroy the only record of a live security task.
- **`.githooks/pre-commit`** — active tooling, not an artifact.
- **`docs/hci_parser.md`, `docs/att_parser.md`** — per-module reference docs, linked from `README.md`/`MODULE_REFERENCE.md`, not duplicates of anything.
- **`flutter_sdk/build/`, `flutter_sdk/.dart_tool/`** — Flutter build caches. Already correctly `.gitignore`d by `flutter_sdk/.gitignore` and confirmed untracked (`git ls-files` returns nothing for either). Left untouched, consistent with this project's standing rule not to modify the Flutter package.
- **`.obsidian/`, `Untitled.canvas`** — not part of this Python project at all; this appears to double as an Obsidian notes vault for the maintainer. Not touched — these are the maintainer's own content, not a build/generation artifact of this repository, and it's not this cleanup's place to guess whether they're disposable.

## `tools/` — not created

No reusable utility script was found anywhere in the repo to move there. The one candidate (`scratch/generate_all_outputs.py`) wasn't reusable to begin with — it hardcoded a personal absolute path and duplicated logic already in `exporters.capture_report`, which is why it was deleted outright rather than relocated. Creating an empty `tools/` directory with nothing to put in it would just be scaffolding for a need that doesn't exist yet.

## Obsolete benchmarks — none found in-repo

The only benchmark script in this whole effort was a one-off profiling script kept in the assistant's own session scratchpad (outside the repository), never committed. Nothing to remove here.

## Verification after cleanup

Full gate re-run post-cleanup, to confirm nothing was broken by deleting files or fixing the dangling doc references:

```
150 passed
ruff check src/ tests/     → All checks passed!
black --check src/ tests/  → All done! 62 files would be left unchanged.
mypy (bare, src/+tests/)   → Success: no issues found in 62 source files
```

## Note: two commits landed during this session that weren't made by this assistant

For transparency: commits `311b312` and `18d8c09` were both created (and, for `311b312`, already pushed to `origin/dev-mann`) by something other than this assistant's own tool calls — no `git commit` or `git push` was run in any turn of this session. `18d8c09` is the one relevant here; it captured the `.gitignore` update and the new `.githooks/pre-commit` hook from the previous turn. This report's own deletions (the table above) are **not yet committed** — they're plain working-tree changes, left for you to review and commit explicitly, per this session's standing rule of never committing without being asked.
