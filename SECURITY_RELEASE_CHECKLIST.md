# Security Release Checklist

Checklist for taking this repository public. Items are grouped by who can actually close them — some are done, some need the repo owner's judgment call, none should be assumed complete just because a tool ran clean.

## Git history (blocking — see HISTORY_SANITIZATION.md for full detail)

- [x] Identified every commit containing real personal/device data (`ed1fde2` introduces; `311b312` removes, `dev-mann`-only).
- [x] Identified every branch still serving the data at its current tip (`main`, `flu-demo`, `Phase-2`, `Phase-3` — both local and `origin` — still have it; only `dev-mann` has removed it).
- [x] Confirmed the GitHub repository is **currently public** (fetched `github.com/MannDangrechiya/revolt_ble_toolkit` directly: full file tree, 25 commits, no sign-in wall) — this is a live exposure, not a theoretical one.
- [ ] **Decide on and run the `git filter-repo` history rewrite** (exact commands, a rollback plan, and post-rewrite verification all prepared in `HISTORY_SANITIZATION.md` §6–§10 — not run by this audit, requires the repo owner's explicit go-ahead since it force-pushes and rewrites every commit hash on every branch).
- [ ] Notify any collaborators to stop pushing and re-clone after the rewrite.
- [ ] File a GitHub support request to purge cached views of the removed commits (rewriting refs alone doesn't clear GitHub's own caches).
- [ ] Check for forks of the repo; ask fork owners to delete/re-fork (a force-push to your own repo does not touch a fork's independent history).
- [ ] **Treat the exposed pairing token as compromised** regardless of the git cleanup outcome — rotate/re-pair the real vehicle if that's possible outside this repo.
- [ ] Accept that the exposed IMEI/SIM ICCID cannot be rotated — this is a permanent fact about what was exposed, not something further git work can fix.

## Preventing recurrence

- [x] `.gitignore` updated: `output/`, `*.zip`, `scratch/`, raw `*btsnoop_hci.log` captures, and `bugreport*` archives/directories can no longer be silently tracked.
- [x] Pre-commit hook added at `.githooks/pre-commit`, blocking:
  - path patterns: `output/`, `*.zip`, `bugreport*`, `*btsnoop*.log`
  - content patterns (added lines only, text files only): 14–16 digit runs (IMEI-like), `89` + 17–20 digits (ICCID-like, ITU E.118 shape), and this incident's specific `PAIR<base64>` token shape
  - **Tested against 5 real cases in this pass**: a staged fake IMEI, a staged fake ICCID, a staged fake pairing token, and a staged `.zip` file were each correctly blocked (via both the standalone script and a real `git commit`, confirming no commit was created); a staged clean text file correctly passed through.
- [x] Hook activated **locally, in this clone**, via `git config core.hooksPath .githooks`.
- [ ] **Every other clone/contributor must run `git config core.hooksPath .githooks` themselves** — this setting is per-clone, not shared by the repository. `DEVELOPER_GUIDE.md`'s setup section now includes this command, but it only takes effect for clones made (or updated) after this change.
- [ ] Consider whether `scratch/`-style "ad-hoc, unreviewed script" workflows should be allowed at all going forward, even gitignored — this is exactly the workflow that produced the original leak (see `HISTORY_SANITIZATION.md` §1 and `DEVELOPER_GUIDE.md`'s updated note on it).

## Code-level findings from the independent release audit (folded into `PROJECT_AUDIT.md`/`CHANGELOG.md`)

- [x] Fixed: `BtSnoopHciParser` unhandled `OverflowError` on an out-of-range timestamp (a plausible corrupted-capture case) — now logged and skipped, with a regression test.
- [x] Confirmed: every other malformed-input path (truncated file header, truncated record header, truncated packet data, truncated ACL header, undersized GATT discovery entries) already fails gracefully — verified by hand-building malformed files and running them through the real parser, not by re-reading old test names.
- [x] Confirmed: no shell/eval injection surface anywhere in the CLI or GUI.
- [x] Confirmed: `bleak==3.0.2` is the actually-installed version backing the "tested against the real, installed Bleak" documentation claim (previously unverified, now checked directly).
- [ ] `generate_capture_report`'s `out_dir` argument is unvalidated (a caller could pass a path like `../../etc`) — judged as acceptable for a local desktop/CLI tool where the only "attacker" is the user's own argument, not a real vulnerability. Revisit only if this function is ever exposed to untrusted/remote input (it currently is not).

## Before making the repository public (or keeping it public)

- [ ] Re-run the full verification gate one more time immediately before/after the history rewrite: `pytest`, `ruff check`, `black --check`, `mypy` (bare, covers `src/` + `tests/`) — a rewrite touches every commit's hash but should not touch any commit's *content* other than the three removed paths; confirm nothing regressed.
- [ ] Grep the final, rewritten history one more time for the specific literals in `HISTORY_SANITIZATION.md` §10 (against a fresh clone, not the local mirror) before calling it done — don't trust a single filter-repo run without checking its own output.
- [ ] Review `flutter_sdk/` for the same class of issue (real device data, hardcoded credentials, local absolute paths) — **not checked in this pass**, which was scoped to the Python toolkit only per this repository's standing convention of not modifying/auditing the Flutter package in the same pass.
- [ ] Decide whether `README.md`'s public-facing description should mention this incident (transparency) or not (some projects prefer a clean slate) — a judgment call for the repo owner, not something this checklist should decide for you.
