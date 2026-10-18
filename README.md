# Silent failures in agent harnesses

Four case studies from tools I built and ran for AI agents in 2026. In each one, a tool or a test reported success while the wrong thing happened, and nothing downstream noticed. Each case has a cited evidence table (commit hashes, files, recorded measurements), a small runnable demo or simulation, and a limitations section.

An agent acts on what its tools tell it. When a tool says "ok" and is wrong, the agent cannot recover, because it does not know there is anything to recover from. That makes false success more dangerous for agents than loud failure, and it matters for AI control: oversight mechanisms such as approval gates and verification steps fail in the same silent way.

| Case | What reported success | What actually happened | Fix and principle |
|---|---|---|---|
| [01 Stale element index](cases/01-stale-element-index/CASE.md) | A browser bridge's click by element number returned `ok: true` | The page had re-rendered, so the number pointed at a different element | Identity-stable `ref` handles that resolve to the same element or fail with a classified `SC_STALE_REF` error. A handle held across a delay should name a thing, not a position. |
| [02 Approval gate per process](cases/02-approval-gate-per-process/CASE.md) | A human-approval gate for sending messages looked present and documented | Its "untrusted content was read" flag lived in process memory, so read and send in separate CLI calls skipped approval | Mark the flag on every send. A gate should be keyed to the action and fail closed when its state is lost. |
| [03 Single-trial probe](cases/03-n1-probe-wrong-conclusion/CASE.md) | One clean request, then passing test suites, "verified" each fix | The endpoint failed 20-80% of the time depending on the hour; several commits chased wrong causes | Round-robin A/B across arms in the same minutes, n of 12 or more, and report the answer as a dated regime. |
| [04 False-success exit codes](cases/04-false-success-exit-codes/CASE.md) | Installers, downloads and a workflow exited 0 or showed green | Rollbacks, truncated files, swallowed model errors | Verify the postcondition (hash, size, status), not the exit code. |

## Running the demos

Python 3.11+ on any OS. Case 01 also needs `playwright` and an installed Chrome.

```
python -X utf8 cases/01-stale-element-index/demo/demo.py
python -X utf8 cases/02-approval-gate-per-process/demo/gate_demo.py
python -X utf8 cases/03-n1-probe-wrong-conclusion/method/roundrobin_ab.py
python -X utf8 cases/04-false-success-exit-codes/checks/verify_or_fail.py
```

Each folder keeps the output I captured as `OUTPUT.txt`. The demos are small standalone reimplementations of each pattern; they do not run the original tools.

## How this was made

The original tools were built by me with AI coding assistants (mostly Claude Code). For this repo, AI agents extracted the evidence from my repositories under one rule: every number cites a commit, a file line or a recorded measurement, and anything without a source is marked UNVERIFIED. I re-ran every demo and checked the key citations by hand.

Checking the sources also corrected some of my own notes, and the cases say so. The wrong click with `ok: true` (case 01) is documented on a local test page, not on the live site I remembered. The wrong-cause chase in case 03 took about 5.5 hours, not a full day. One sub-case in case 04 did not reproduce on the current tool version.

## Third-party note

Case 02 describes a design gap in [SideTap](https://github.com/ucsandman/SideTap) (MIT). It behaves as intended for a single long-lived agent process. The case describes the pattern and a mitigation, not an exploit, and I plan to report it to the maintainer.

## License

MIT. See [LICENSE](LICENSE).
