# History Sanitization — Real Personal Data in Git History

**Status: NOT YET DONE. This document is preparation only — no history has been rewritten, and nothing has been force-pushed.** This is the complete, current procedure. Read it fully before running anything; execution is yours to trigger, not this document's.

**Severity: high, and no longer hypothetical.** `https://github.com/MannDangrechiya/revolt_ble_toolkit` is **publicly visible right now** — re-confirmed by fetching the repo page directly (full file listing, 25 commits, 0 stars, 0 forks, 0 watchers, no sign-in wall). The **0 forks is one piece of good news**: nobody else has an independent copy of this history to also worry about. The data below has been reachable from that public URL since the introducing commit was pushed.

---

## 1. What's exposed, and why each item is sensitive

All of it came from one committed script (`scratch/generate_all_outputs.py`) that read a real Android bugreport from the maintainer's own machine and wrote its output into `output/` and `output.zip`.

| Data | Where | Why it's sensitive |
|---|---|---|
| Real IMEI (`[REDACTED_IMEI]`) | `output/ascii_strings.txt`, `output/notifications.csv`, `output/packet_pairs.csv`, `output/telemetry_candidates.csv`, `output/protocol.md`, `scratch/generate_all_outputs.py` (as a worked example) | A device's IMEI is a permanent hardware identifier. Publishing it lets anyone associate this specific physical device with this GitHub account, and (with carrier cooperation or IMEI-tracking services) can be used to track or blocklist the device. |
| Real SIM ICCID/serial (`[REDACTED_ICCID]`) | Same files as above | Tied to a specific mobile subscription/account. Combined with the IMEI and pairing token below, it narrows down a real person's real, currently-active mobile line. |
| A real device pairing token (`[REDACTED_PAIRING_TOKEN]#`, base64-decodes to an 8-digit number — almost certainly a phone-number fragment used as the BLE pairing shared secret) | `output/write_requests.csv`, `output/packet_pairs.csv`, `output/protocol.md`, `output/summary.md`, `scratch/generate_all_outputs.py` | If still valid, this is a live credential — anyone who reads it can authenticate to the real vehicle over BLE within physical range. |
| Local Windows username in a file path (`C:\Users\[REDACTED_USER]\Downloads\bugreport-m52xqins-TP1A.220624.014-2026-08-01-10-40-19\...`) | `scratch/generate_all_outputs.py`, `output/statistics.json`, `output/summary.md` | Minor alone, but combined with the above further identifies the maintainer as the device owner. |
| Flat, unscored "fact" statements about decoded telemetry (e.g. "Battery Voltage: 18") | `output/protocol.md` | Not a privacy issue, but proof this script was never part of the reviewed, tested codebase — it directly violates the project's own confidence-scoring principle. |

## 2. Affected commits — re-verified fresh, unchanged since the last pass

Exactly two commits touch these paths, on the `dev-mann` line of history (confirmed again just now: `git log --all --oneline -- output output.zip scratch/generate_all_outputs.py` returns only these two):

| Commit | Reachable from | What it did |
|---|---|---|
| `ed1fde2232065c240507ee47e4b64ab53874eb92` "output folder done" | **every** branch below (ancestor of all of them) | **Introduced** `output.zip`, all 8 files under `output/`, and `scratch/generate_all_outputs.py` (945 insertions, 10 files). |
| `311b3128564e5a538a61d4380c73ace9b0542b35` "The independent release audit is done...(RELEASE_AUDIT.md)" | `dev-mann`/`origin/dev-mann` only | **Removed** all 10 files (made outside this assistant's tool calls — see §5). |

**Nuance for anyone running a path-filter tool:** removing a path in a later commit does **not** remove it from history — every commit between `ed1fde2` and the removal still has the file in its tree. A path-based filter rewrites **every commit from `ed1fde2` onward, on every branch that contains it**, because changing a blob changes every descendant tree/commit hash. Expect every commit hash on every affected branch, from `ed1fde2` forward, to change.

## 3. Affected branches and their exact current tips

This table is the baseline — record it before touching anything, since after a rewrite these hashes are exactly what "restored to the pre-rewrite state" means.

| Branch | Current tip SHA | Subject | Sensitive files at tip? | Commits from `ed1fde2` onward | On `origin`? |
|---|---|---|---|---|---|
| `main` / `origin/main` | `0b7d677ab6f9d2578f43c74f20fa6c8b6a66159d` | "workspace" | **Yes** | 17 | Yes |
| `flu-demo` / `origin/flu-demo` | `1d0286afadbeba3d4d49a0bd58c43f0ef0805faf` | "Demo done. flutter_sdk/example/" | **Yes** | 8 | Yes |
| `origin/Phase-2` | `b1ec120eb477f5344ca6aef47bcfe3cad8cec6cf` | "Phase 2 Done" | **Yes** | 3 | Yes |
| `origin/Phase-3` | `4e45dc8d18c76e0a178eb0e7fc81cbdd9d3321d9` | "Module 11 done. flutter_sdk/" | **Yes** | 5 | Yes |
| `dev-mann` / `origin/dev-mann` | `18d8c09a4e4d9c4b396cc055e1d143e6f4acd87f` | "Step 1 (Highest Priority) — Fix the Git history" | No — removed at `311b312`, still clean at current tip | 14 | Yes |

**Bottom line: 4 of 5 branches (`main`, `flu-demo`, `Phase-2`, `Phase-3`) still serve this data today from their current tip.** Only `dev-mann` has it removed at HEAD, and even there it's reachable via `ed1fde2`..`311b312` in that branch's own history.

## 4. Note on commits that happened outside this assistant's control

Two commits on `dev-mann` — `311b312` (removal) and `18d8c09` (the `.gitignore`/pre-commit-hook commit) — were made and pushed to `origin/dev-mann` by something other than this assistant's own tool calls; no `git commit` or `git push` has been run in any turn of this whole engagement. Noted here because it means `dev-mann`'s tip keeps moving between sessions — **re-verify §3's table immediately before executing anything below**, don't trust it blindly if time has passed.

## 5. Recommended tool: `git filter-repo`

`git filter-repo` is the currently git-project-recommended tool for path-based history rewriting (preferred over `git filter-branch`, and over BFG for anything beyond simple large-blob stripping). Not installed in this environment (`git filter-repo --version` and `pip show git-filter-repo` both come back empty) — installing it is step 1 below.

---

## 6. Rollback plan — prepared *before* any rewrite, not after

Two different rollback scenarios, depending on how far you got:

**A. Before force-pushing (§8 Step 8):** trivially safe. Nothing on `origin` has changed yet. If anything looks wrong at any point up to and including the local sanity checks, just delete the working mirror clone and stop:

```bash
cd ..
rm -rf revolt_ble_toolkit_sanitize.git
```

Origin is untouched. Nothing to undo.

**B. After force-pushing:** this is why the backup in §7 Step 2 must be a **separate, untouched mirror clone made straight from `origin`**, not the local working copy (the local copy is exactly what's about to be discarded, and cloning "from local" would just copy the same soon-to-be-rewritten history rather than an independent, verifiable snapshot of what's actually on the server today). To roll back:

```bash
cd ../revolt_ble_toolkit_BACKUP_BEFORE_SANITIZE.git

# Confirm this backup still has the exact pre-rewrite tips from §3 before using it:
git log -1 --format='%H' main        # expect 0b7d677ab6f9d2578f43c74f20fa6c8b6a66159d
git log -1 --format='%H' dev-mann    # expect 18d8c09a4e4d9c4b396cc055e1d143e6f4acd87f
git log -1 --format='%H' flu-demo    # expect 1d0286afadbeba3d4d49a0bd58c43f0ef0805faf
git log -1 --format='%H' Phase-2     # expect b1ec120eb477f5344ca6aef47bcfe3cad8cec6cf
git log -1 --format='%H' Phase-3     # expect 4e45dc8d18c76e0a178eb0e7fc81cbdd9d3321d9

# Then push the untouched originals back over the rewrite:
git push origin --force --all
git push origin --force --tags
```

This restores every branch on `origin` to exactly the state in §3's table — it does **not** undo the fact that the sensitive data was exposed while public (that's §10, not a git problem), and it does **not** reach anyone who already re-cloned the rewritten history in the gap between your force-push and the rollback — they'd need to be told to re-clone again. There is no partial/single-branch rollback needed beyond this: restoring all 5 refs at once with `--all` is simpler and just as safe as doing it one at a time, since the backup mirror is read-only and this only ever pushes, never deletes, anyone's own clone.

**GitHub-side safety net, independent of your own backup:** GitHub does not immediately garbage-collect commits that a force-push makes unreachable. For some period after a force-push (commonly weeks, not guaranteed, not something to rely on as a primary plan), the old commits may still be fetchable by exact SHA even though no branch points at them — e.g. `git fetch origin ed1fde2232065c240507ee47e4b64ab53874eb92`. Treat this as a fallback if the local backup mirror is somehow lost, not as a substitute for making it.

---

## 7. Preparation steps (non-destructive — safe to run now)

### Step 1 — Tell every collaborator to stop pushing, right now

A history rewrite invalidates every existing clone's ancestry. Pause all work on `main`, `flu-demo`, `Phase-2`, `Phase-3`, and `dev-mann` until the rewrite is done and everyone has re-cloned (§9).

### Step 2 — Make the golden backup: a mirror clone straight from `origin`, touched by nothing else

```bash
cd ..
git clone --mirror https://github.com/MannDangrechiya/revolt_ble_toolkit.git revolt_ble_toolkit_BACKUP_BEFORE_SANITIZE.git
```

Verify it against §3's table right after cloning (same commands as in §6 scenario B) before doing anything else. This clone is never touched again except to read from it or, if needed, to push it back (§6B).

### Step 3 — Make a second, separate mirror clone to actually operate on

```bash
cd ..
git clone --mirror https://github.com/MannDangrechiya/revolt_ble_toolkit.git revolt_ble_toolkit_sanitize.git
cd revolt_ble_toolkit_sanitize.git
```

### Step 4 — Install `git filter-repo`

```bash
pip install git-filter-repo
git filter-repo --version   # confirm it's found before proceeding
```

---

## 8. The rewrite — exact `git filter-repo` commands

### Step 5 — Remove the sensitive paths from every commit, on every branch/tag, in one pass

```bash
git filter-repo \
  --path output \
  --path output.zip \
  --path scratch/generate_all_outputs.py \
  --invert-paths
```

`--invert-paths` means "keep everything except these paths." This rewrites every commit from `ed1fde2` onward, across all 5 branches in the mirror, matching §2/§3's blast radius exactly.

### Step 6 — Verify locally, in the rewritten mirror, before it ever touches `origin`

```bash
# Paths gone entirely:
git log --all --oneline -- output output.zip scratch/generate_all_outputs.py
# expect: no output

# Content gone entirely — every literal from §1:
git log --all -S"[REDACTED_IMEI]" --oneline
git log --all -S"[REDACTED_ICCID]" --oneline
git log --all -S"PAIRODg2" --oneline
git log --all -S"dipak\\Downloads" --oneline
git log --all -S"bugreport-m52xqins" --oneline
# expect: no output for all five

# Every branch still present, nothing silently dropped:
git branch -a
# expect: main, dev-mann, flu-demo, Phase-2, Phase-3 all present
```

### Step 7 — Re-add the remote (filter-repo strips it as a safety measure so you can't push by accident)

```bash
git remote add origin https://github.com/MannDangrechiya/revolt_ble_toolkit.git
```

### Step 8 — Final sanity check before the point of no return

```bash
git log --oneline -20     # history still reads sensibly
git show HEAD --stat      # no output/output.zip/scratch in the current tree
```

If anything here looks wrong: stop, `cd .. && rm -rf revolt_ble_toolkit_sanitize.git`, and start over from Step 3. `origin` is still untouched (§6A).

---

## 9. Force-pushing — exact commands, all-at-once or one branch at a time

**All at once** (simplest; the backup in §6B/§7 Step 2 makes this safe to do in one shot):

```bash
git push origin --force --all
git push origin --force --tags
```

**One branch at a time**, if you'd rather verify each push before moving to the next (recommended if you want to spot-check `origin`'s state on GitHub between pushes):

```bash
git push origin --force refs/heads/main:main
git push origin --force refs/heads/dev-mann:dev-mann
git push origin --force refs/heads/flu-demo:flu-demo
git push origin --force refs/heads/Phase-2:Phase-2
git push origin --force refs/heads/Phase-3:Phase-3
git push origin --force --tags
```

### Step 10 — Everyone re-clones; nobody merges an old clone back in

Every collaborator, and this session's own working copy at `C:\Desktop\flutter_projects\revolt_ble_toolkit`, must delete their existing clone and re-clone fresh. Do **not** `git pull`/`git fetch` + merge an old clone against the rewritten remote — that resurrects the very history being removed.

---

## 10. Verify no sensitive data remains — from a genuinely fresh clone, not the mirror you just pushed

Re-running checks against the mirror you just pushed only proves the mirror is clean; it doesn't prove `origin` actually accepted the rewrite. Do this against a brand-new clone instead:

```bash
cd ..
git clone https://github.com/MannDangrechiya/revolt_ble_toolkit.git revolt_ble_toolkit_POST_REWRITE_CHECK
cd revolt_ble_toolkit_POST_REWRITE_CHECK
git fetch --all

# Repeat every check from Step 6, against this fresh clone this time:
git log --all --oneline -- output output.zip scratch/generate_all_outputs.py
git log --all -S"[REDACTED_IMEI]" --oneline
git log --all -S"[REDACTED_ICCID]" --oneline
git log --all -S"PAIRODg2" --oneline
# expect: no output for all four

# Confirm the new tip hashes actually differ from §3's table (proof the rewrite took effect):
for b in main dev-mann flu-demo; do git log -1 --format="$b -> %H" origin/$b; done
git log -1 --format='Phase-2 -> %H' origin/Phase-2
git log -1 --format='Phase-3 -> %H' origin/Phase-3
# expect: every hash different from §3's table
```

Then, separately, reload `https://github.com/MannDangrechiya/revolt_ble_toolkit` in a browser (or fetch it) and manually check the file browser at each branch no longer shows `output/`/`output.zip`/`scratch/` — GitHub's own UI is a second, independent confirmation beyond the CLI checks above.

## 11. This is not just a git problem — treat the exposed credential as compromised

Rewriting history reduces future exposure; it does not undo exposure that already happened on a public repository. Regardless of how §10 goes:

- **Treat the pairing token as already compromised.** Rotate/revoke/re-pair the real vehicle with a new token if that's possible, independent of this repository.
- **The IMEI and SIM ICCID cannot be "rotated."** Permanent hardware/subscription identifiers — no git-side fix undoes this exposure; it's a fact to be aware of, not a problem this procedure can solve.
- **GitHub-side follow-up** (open a support request to purge cached views/PR diffs of the old commits; there are 0 forks to worry about, per the visibility check at the top of this document, which simplifies this) and **assume third-party crawlers/the Wayback Machine may already have a copy**, independent of anything GitHub does on request.

## 12. Status

- ✅ §1–§3: every affected commit, branch, and sensitive item identified and re-verified fresh this pass.
- ✅ §6: rollback plan prepared, including exact pre-rewrite tip SHAs to verify a restore against.
- ✅ §7–§9: exact, copy-pasteable `git filter-repo` and force-push commands prepared (both all-at-once and per-branch).
- ✅ §10: post-rewrite verification procedure prepared, using an independent fresh clone rather than trusting the local mirror.
- ✅ Already done in an earlier pass, unaffected by whether the rewrite proceeds: `output/`, `output.zip`, `scratch/generate_all_outputs.py` removed from the working tree; `.gitignore` and a pre-commit hook (`.githooks/pre-commit`) now block this class of file from being reintroduced (see `SECURITY_RELEASE_CHECKLIST.md`).
- ❌ **Not executed, on purpose:** no `git filter-repo` run, no force-push, no rollback performed. Everything in §7–§10 is ready for your review and explicit go-ahead.
