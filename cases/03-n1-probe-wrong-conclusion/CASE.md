# Case 03: a single-trial probe against a drifting endpoint reached the wrong conclusion

Source project: ocbridge, a local OpenAI-compatible proxy in front of a free LLM tier (OpenCode Zen). All hashes below are from that repo; dates are commit dates.

## What happened

| Date | Commit | Event |
|---|---|---|
| 2026-08-13 | `649aa2e` | Drops the "dead Zen header machinery". Its stated evidence: free models "answer 200 with no x-opencode-* headers" (commit body). The script behind it, `diag_curl_no_headers.sh`, sends one request with `max_tokens` 4. |
| 2026-08-24 09:20 | `1892d39` | Blames `649aa2e` for 503s using a log split: 5xx 112/8323 (1.35%) before vs 61/233 (26.18%) after. Restores a stable process-wide session id and widens failover to 5xx. |
| 2026-08-24 10:33 | `2c21633` | Reverts the 5xx failover: "26 failovers, zero successes". |
| 2026-08-24 14:53 | `395d179` | Round-robin A/B finds the header itself is the trigger: 6/12 failed with it, 0/12 without. Header removed. |
| 2026-09-07 | `468f023` | Header restored: `MissingSessionID` now returned without it. |
| 2026-09-08 | `87c6dbd` | Four-arm round-robin, 12 rounds: real and bogus session 0/12 failed, no session and no `x-opencode-*` 12/12 failed (HTTP 400). Presence matters; value does not. |
| 2026-09-22 | `8c639b9` | A third regime: all ten arms return 403, including one with no Authorization header. Its commit message says the last two regime changes "were each misdiagnosed from an n=1 call". |

## Why it is a silent failure

Every wrong step passed its own check. `649aa2e` had a live 200 and 194 passing tests. `1892d39` had 247 passing tests and a measured 19x log difference. `2c21633` was itself a correct revert of a bad idea. Nothing errored; the endpoint simply failed about half the time, so "it works" and "it's broken" were both reproducible on demand (incident doc, "Symptom"). A single curl that happens to land in a good window looks like a verification. The doc records the same-day failure rate with the header at 80%, 75%, 60%, 50%, 38%, 20% depending on the hour, so one clean run is expected, not informative.

Both wrong theories also asked the wrong question ("what value should the header carry?") and never "should it be sent at all?" (incident doc, "Why the earlier theories looked right").

## Evidence

| Claim | Source |
|---|---|
| Original evidence was one request | `1892d39` body: "one request, max_tokens=4, body 'hi'"; script at `diag_curl_no_headers.sh` |
| August A/B: 6/12 vs 0/12 vs 0/12 | `395d179` body; incident doc, Evidence 1 |
| Streaming end to end: 8/10 vs 0/10; 60 consecutive successes without header | `395d179` body |
| Value irrelevant: five fixed ids and one fresh id failed 2/6 to 4/6 each, header omitted 0/6 | incident doc, Evidence 2 |
| 503 fails in about 0.5 s, success takes 2.5-5 s (edge reject, not timeout) | incident doc, "Symptom" (no raw timing log kept in repo) |
| September A/B: 0/12, 0/12, 12/12, 12/12 | `87c6dbd` body |
| Retry would fix it but costs about 2x quota (12/20 first attempts failed, 18/20 overall) | incident doc, "What was NOT the cause" |

## The method fix and general principle

`probe_session_header.py` runs its arms round-robin, one request per arm per round, 12 rounds. Drift hits every arm equally, so it cancels. Blocked runs confound drift with the arm. Add arms that separate hypotheses (real vs bogus id) rather than collapsing them. Treat the answer as a regime ("as of this date, presence is required"), not a permanent rule: the behavior flipped three times in two months. A clean 100%/0% split is strong evidence because drift moves a rate and does not create a partition; an "all arms fine" result is the one to re-run in another hour.

## Simulation

`method/roundrobin_ab.py` is a synthetic endpoint (not real data) whose failure probability drifts sinusoidally between 0.10 and 0.80. Output is in `method/OUTPUT.txt`, seed fixed, 2000 trials per cell:

- Truly identical arms: n=1 falsely declared a difference 39.0% of the time (19.9% + 19.1%), blocked 54.4%, interleaved 10.1%.
- Arm B truly worse by 0.30: the wrong arm was blamed in 7.2% (n=1), 5.7% (blocked) and 0.1% (interleaved) of trials.

## Limitations

- The simulation shows the mechanism, not the real Zen drift shape; its parameters (period, amplitude, threshold of 4) are my choices.
- Interleaved n=12 was not more powerful here (48.2% detection vs 49.5% blocked, with a threshold of 4) and still false-alarms 10% of the time; it removes the confound, not the sampling noise.
- `649aa2e`'s narrow claim (200 with no headers) was true in the August regime; what was wrong was the generalization to "dead machinery". `1892d39` criticized that n=1 evidence but its own cause was also wrong. The incident doc's phrase "a full day" is loose: by commit timestamps the wrong-cause work ran about 5.5 hours on 2026-08-24.
- The 8/8 alternating A/B cited for `468f023` appears only in that commit's code comments; the incident doc says the commit had no body and that the restore gate was not followed.
