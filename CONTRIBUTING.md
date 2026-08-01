# Contributing

Thanks for considering a contribution to Revolt BLE Toolkit.

## Before you start

- **Bug fix or small improvement:** open a PR directly.
- **New feature or protocol claim:** open an issue first. This project's core rule is that every decoded field is labeled Confirmed / Likely / Unknown with evidence (see [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md)) — if your change adds new protocol interpretation, we'll want to talk about the evidence before the code.

## Setup, conventions, and the verification gate

All of this lives in [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — environment setup, the required `ruff`/`black`/`mypy`/`pytest` gate every PR must pass, module conventions, and how to add a new module. Read it before opening a PR; this file won't repeat it.

## Pull requests

1. Fork, branch, make your change.
2. Run the full verification gate locally (`ruff check .`, `black --check .`, `mypy`, `pytest`) — it must be clean.
3. Add or update tests for anything you change (see DEVELOPER_GUIDE.md's testing conventions).
4. Open the PR against `main` with a clear description of what changed and why.

## Reporting a security issue

Do **not** open a public issue for a security vulnerability — see [SECURITY.md](SECURITY.md).

## Code of conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).
