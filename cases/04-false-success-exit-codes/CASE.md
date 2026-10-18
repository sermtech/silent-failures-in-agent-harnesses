# Case 04: false-success exit codes

## Pattern

A tool exits 0 or prints a success line, but the thing it was asked to do did not happen. A human often notices the missing result later. An agent reads "exit 0" or "refreshed" as the answer and moves on, so the false success becomes the base for every following step.

## Sub-cases

Sources are the author's private repositories and notes; paths are given relative to each project. Dates are commit dates or note dates.

| # | Tool | Claimed | Actual | How detected | Source |
|---|------|---------|--------|--------------|--------|
| a | `pi update --models` (pi 0.87.1 today; earlier version when first measured) | "Model catalogs refreshed", exit 0 (author's note) | models.json unchanged, same rows from `pi --offline --list-models` | SHA256 of models.json before and after | Author's global notes, 2026-09-17 (second-hand). Re-run 2026-10-18, see below |
| b | `winget install Microsoft.DotNet.SDK.8` | exit 0 | MSI fails, Error 1714 / System Error 1612, bundle rolls back with 1603 | Reading the installer log, not winget's status | media project, `docs/frontends.md` lines 99-103 (added in commit a85ff86, 2026-09-20) |
| c | iTunes installer with `/quiet` | exit 0 | Apple Mobile Device Support was skipped, so no USB driver | Checking that the "Apple Mobile Device Service" runs and port 27015 listens | `iphone/README.md` lines 112-117 (commit 23bef53, 2026-10-05) |
| d | `curl -sL` on Hugging Face model files | exit 0 | download cut short (the author's note says 1.4 of 3.8 GB) | SHA-256 vs the HF `lfs.oid`; fix is `curl -fL -C -` | media project, `docs/measured-results.md` line 2026 ("CUT SHORT with curl exit 0", commit 046cf76, 2026-10-11); `bench/sdcpp/README.md` lines 26-27 |
| e | an n8n workflow (author's description) | green runs | failed model calls swallowed; 218 requests for a removed model reached upstream, 10-14 to 10-17 | Hub `usage` table, status <> 200 | ocbridge commits d3b6b8a (2026-10-17) and f09ff48 (2026-10-08); author's task notes |
| f | Second listener on a port already in use (Windows) | no error from either side | `python -m http.server 8765` took over the proxy's port | Noticed later as timeouts elsewhere (author's note) | a client website project's `AGENTS.md` ("hijacked it twice") |

### Notes on evidence quality

- **a.** I re-ran `pi update --models` after copying models.json to a temp dir. It did not print "Model catalogs refreshed" and did not exit 0: it exited 1 with "Could not refresh model catalogs: openai-codex: OpenAI Codex token refresh failed (401)". models.json stayed byte-identical (SHA256 cf8659e7...6fa6d3 before and after, confirmed with `cmp`), and `--list-models` output hash was unchanged. So the original success-string claim is **not reproduced today** and rests on the author's earlier measurement with an older pi. The related stale-declaration risk is visible now: `pi --offline --list-models` warns `No models match pattern "hub/<provider>/deepseek-v4-flash"`, a configured model pattern that no longer resolves.
- **b.** The log itself is not on disk; the doc records the measurement and the cause (cached MSI for the installed .NET Host missing). Winget's exit 0 is the author's report, not re-run (re-running would be an install).
- **c, f.** Single-author notes; not re-run.
- **d.** The "1.4 of 3.8 GB" figure appears only in the author's notes. The repo docs confirm the cut-short downloads with exit 0 but give no sizes.
- **e.** The workflow itself is not in any repo I could read. The hub commit confirms the hub-side evidence (218 upstream calls for a dead id, and that failures used to leave no usage row, f09ff48). That the workflow swallowed those errors comes from the author's TODO line.

## Why this matters for agents

Humans skim a log, see a missing file, and get suspicious. An agent has a narrower channel: the exit status and a few lines of output. It treats them as ground truth, because checking everything costs tokens and nothing in the prompt says the tool might lie. The failure then compounds: the next step builds on a driver that is not installed, a model file that is truncated, or a model id that no longer exists. Several of these also fail in a way that looks fine for hours (a green workflow run, a picker that lists a name).

## Principle

Verify the postcondition, not the exit code. After the command, check the thing you wanted: the file hash changed, the size or SHA-256 matches, the service answers, the usage table shows status 200. `checks/verify_or_fail.py` is a small helper that runs a command and raises if the exit code is 0 but the postcondition fails. Its self-test (`checks/OUTPUT.txt`) simulates a command that prints a success line, exits 0 and does nothing; the helper catches it, plus a truncated download and a wrong checksum.

## Limitations

- A postcondition is only as good as what it measures. A hash that changed proves the file changed, not that it is correct.
- You need to know the expected value (size, checksum, status) in advance; for some tools nobody publishes one.
- Cases a, e, f rely partly on the author's own notes; see the evidence notes above.
- The helper covers file and HTTP checks only. It cannot see a swallowed error inside a workflow engine; that needs a check at the downstream system (case e).
