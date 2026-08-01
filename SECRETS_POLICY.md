# Secrets Policy

This project scans for accidentally-committed secrets (API keys, tokens, private keys) with [Gitleaks](https://github.com/gitleaks/gitleaks). This exists because of a real incident — see [HISTORY_SANITIZATION.md](HISTORY_SANITIZATION.md) — not as a speculative precaution.

## Where it runs

| Layer | What | Blocking? |
|---|---|---|
| **CI** (`.github/workflows/ci.yml`, `gitleaks` job) | `gitleaks/gitleaks-action@v2` against every push/PR | **Yes** — fails the check, cannot be merged around |
| **Local pre-commit hook** (`.githooks/pre-commit`) | `gitleaks protect --staged` against your staged diff, if `gitleaks` is installed | Blocks the commit if installed and it finds something; otherwise prints a warning and lets the commit through (see below) |

The local hook is **not required to be installed** — a missing `gitleaks` binary only prints a note, it doesn't fail the commit. CI is the actual, unavoidable enforcement point; the local hook is a convenience that catches problems before you even push.

### Install gitleaks locally (optional, recommended)

- macOS: `brew install gitleaks`
- Windows: `scoop install gitleaks` or `winget install gitleaks`
- Linux / any OS with Go: see the [gitleaks releases page](https://github.com/gitleaks/gitleaks/releases) for a static binary

Then activate the hook once per clone (also needed for the sensitive-data hook already in this repo):

```bash
git config core.hooksPath .githooks
```

## What CI scans, and what it deliberately doesn't

The CI job checks out with the default shallow depth (one commit) — it scans **new commits as they're pushed, not the entire repository history.** This is deliberate: this repo's git history predates gitleaks and is already known to contain real leaked data (IMEI, SIM serial, a pairing token) that's tracked and being remediated separately in `HISTORY_SANITIZATION.md`. Re-flagging that same known issue on every single CI run wouldn't add information — it's already found, documented, and has a prepared fix. Gitleaks' job here is stopping the *next* leak, not re-litigating the last one.

If you want to check the full history yourself (e.g. before/after running the `HISTORY_SANITIZATION.md` procedure):

```bash
gitleaks detect --source . -v
```

## If Gitleaks flags something

1. **It's a real secret:** don't commit it. Rotate/revoke it if it was ever pushed anywhere, even briefly — assume it's compromised the moment `git add` touches it, per the same reasoning in `HISTORY_SANITIZATION.md`.
2. **It's a false positive** (e.g. a test fixture that happens to look like a key, or a doc quoting a known-past incident as evidence): add a scoped entry to [`.gitleaks.toml`](.gitleaks.toml)'s `[allowlist]` — by path (a whole file, like the incident-history docs already excluded there) or by a specific regex/commit SHA, whichever is narrower. Don't disable the rule globally for one false positive.
3. **Only as a last resort**, bypass the local hook with `git commit --no-verify` — this does **not** bypass CI, which is the real gate.

## Scope

Covers the Python package. `flutter_sdk/` is a separate package with its own release cycle, out of scope for this repo's CI — see `SECURITY.md` for where to report an issue found there.
