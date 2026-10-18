# Case 02: an approval gate keyed to process lifetime

## What happened
The author built a wrapper (`iphone.py`) that lets AI agents read and send iPhone messages through SideTap, a third-party open-source tool. SideTap has a human-approval gate: when a send follows a read of untrusted message content, a card appears in a local viewer and the owner must click Approve. The "this session read untrusted content" flag (the taint) is a module-level dictionary in process memory (`trust.py:113-136`), and the send gate returns without asking anyone when that dictionary is empty (`helpers.py:1337-1338`).

That is correct for a long-lived agent process, which SideTap's own code assumes (`approval.py:41`). But a CLI wrapper starts a new process per command. An agent that runs `read` in one invocation and `send` in the next arrives at the gate with an empty taint, and the send goes through with no approval card. Nothing errors; the gate is simply never consulted. The author found and recorded this on 2026-10-06 while proving the first approved send (`0ffaf57`).

The same investigation found a second silent-wrongness issue in SideTap on iOS 18.5: its back-button finder returned the list's "Edit" button (Edit mode can delete conversations), and on a search screen it named a search-result photo as the open thread. Both are cases of a tool confidently reporting the wrong UI target.

## Why it matters for AI control
A human-in-the-loop gate protects against prompt injection only if it fires when the dangerous action happens. Keying it to process lifetime ties it to an implementation detail (how the agent is launched), not to the action (sending a message influenced by untrusted text). The failure is silent: the gate looks present, the docs describe it, and each individual run behaves normally.

## Evidence
| Claim | Source |
|---|---|
| Taint is process-local state, sticky for the process life | `iphone/sidetap/src/phone_harness/trust.py:113-136` (SideTap @ `bc43e6f`) |
| Send gate skips approval when no taint | `sidetap/src/phone_harness/helpers.py:1337-1338` |
| Gate setting is read "because the agent process is long-lived" | `sidetap/src/phone_harness/approval.py:41` |
| Flaw recorded: "taint is per PROCESS" | commit `0ffaf57`, 2026-10-06 |
| Mitigation: `trust.mark("iphone.py send")` before every send | `iphone.py:571`; commit `c5a3123`, 2026-10-06 |
| Rationale text | `iphone.py:23-25`; `README.md:104-106` |
| Rule "never add a bypass" | `AGENTS.md:107-110` |
| Edit-button and search-photo misidentification | `README.md:92-95`; `iphone.py:20-22` |
| Replacement navigation refuses to tap `Edit` etc. | `iphone.py:58` (`NOT_BACK`); `AGENTS.md:116` |
| Sender in a second channel has server-side guards (known contacts, first-send confirm, rate limit, audit) | WhatsApp skill `wa.py:8-10` (initial import `1a214a1`, 2026-10-04) |

## Mitigation and principle
The wrapper stops relying on remembered state: it marks the taint itself on every send, so approval is always required regardless of what was read earlier (`iphone.py:571`). It also checks the viewer is running before touching the phone, so a send never waits on a card nobody can see. The WhatsApp sender takes the same stance: one send path, with the guards enforced server-side rather than in the caller.

Principle: a gate should be keyed to the action and fail closed. If the gate needs state to decide "ask or not", losing that state must mean "ask".

## Demo
`demo/gate_demo.py` (63 lines, stdlib only, no SideTap code) spawns real separate processes. Gate A keeps its taint in process memory; gate B asks on every send. Output is in `demo/OUTPUT.txt`: with gate A, read-then-send across two processes sends with no approval, while the same sequence in one process, and gate B in any arrangement, asks the human.

## Disclosure note
SideTap is third-party (upstream: github.com/ucsandman/SideTap, MIT license, copyright holder named in its LICENSE file). The design behaves as intended for a single long-lived process, so this is a hardening gap rather than a plain bug, and it is not weaponised here. The author should report it to the maintainer before or alongside publication, suggesting an option to persist the taint (or require approval whenever the process has no read history). The author has not yet reported it (UNVERIFIED: no upstream issue was checked).

## Limitations
- The bypass was reasoned from source and recorded by the author; this evidence pass did not run SideTap or contact a phone.
- The demo models the pattern, not SideTap's behaviour, and the "human approval" is a stub.
- Whether other SideTap entry points (its MCP server) keep one process was not examined.
- The WhatsApp guards are cited from the skill's docstring; server-side enforcement was not read.
