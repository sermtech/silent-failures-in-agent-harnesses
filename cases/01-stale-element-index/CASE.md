# Case 01: the click that succeeded on the wrong element

## What happened
The smart-crawler headed Chrome bridge lets an agent read a page as a numbered list of interactive elements (`get_state`) and then act on one by number. The number it first offered, `index`, is the element's position in traversal order. Anything that renders above the element renumbers it. If the agent reads the page, does something else, and then clicks a remembered `index`, the click lands on whatever now holds that number. The bridge's own documentation records this outcome: the remembered index "hit the WRONG element and returned `ok: true`" (SKILL-HEADED-CHROME.md, section "`index` vs `ref`").

The fix was an identity-stable `ref`: a number stamped on each element the first time it is seen and never reused during that page load. `click-ref` and `type-ref` act on a ref. A ref whose element is gone returns a classified error, `SC_STALE_REF`, marked `transient`, with guidance to re-read the page.

## Why it is dangerous for agents
Nothing in the failing path looks like a failure. The click is dispatched, the tool returns success, and the agent's next reasoning step assumes the intended element was clicked. The error shows up later and elsewhere (a wrong form submitted, a wrong item deleted), far from its cause. Retrying cannot help, because the agent does not know anything went wrong. An agent that sees a loud, classified error can re-read and recover; an agent that sees success cannot.

## Evidence
| Claim | Source |
|---|---|
| Index is positional; a ref is a WeakMap-stamped identity "reused forever after"; measured on a fixture: alpha index 1 -> 6, ref 2 -> 2 | commit `541d81f` (2026-08-17) message |
| Same commit, other site: "one scroll moved 632 of 650 indices" on amazon.com search | `541d81f` message; SKILL-HEADED-CHROME.md line 1028 |
| Fixture showing the wrong click: old index 1 now held "new4"; clicking the remembered index returned `ok: true` | SKILL-HEADED-CHROME.md, "`index` vs `ref`" section (~lines 930-945) |
| Fixture page for the test | `tests/fixtures/refs_shift.html`, added in `5af9ec7` (2026-08-17) |
| `click-ref` / `type-ref` | commit `bcfcbc5` (2026-08-17) |
| Hacker News measurement: index 121 -> 6 after one scroll, ref 122 unchanged, `click-ref 122` opened the right item | docs/plans/regression-20260818.md lines ~215-260, added in `b2f1a81` (2026-08-18) |
| `SC_STALE_REF` introduced with stable SC_* codes and model-directed guidance | commit `3f250e2` (2026-08-17); table in `assets/chrome_extension/sc_errors.js` line 20 |
| Classified `transient`; `permanent` and `hard_stop` kinds exist | `e14d43d` (2026-08-17); SKILL-HEADED-CHROME.md lines 548-567 |
| Dead ref returns the error in a test | `tests/test_bridge_ports.py` line 248 (`test_dead_ref_returns_stale_ref_code`) |

## The fix and the general principle
Give the agent a handle that can go stale but cannot silently repoint. The ref is resolved against a registry of stamped elements: it finds the same element or finds nothing (`background.js` comment, "same element or resolves to nothing (SC_STALE_REF). It cannot lie"). Failure then becomes explicit, and the `error_kind` and `agent_guidance` fields tell the agent what to do next ("Do not guess an adjacent number").

General principle: any handle an agent holds across a delay should identify a thing, not a position. If identity is not available, the handle should be checked and rejected loudly rather than resolved to whatever is nearby.

## How to reproduce
`demo/` is standalone and does not use the bridge. It needs Python, `playwright`, and an installed Chrome (it launches with `channel="chrome"`; Playwright's own downloaded browser was not present on the machine used).

    python -X utf8 demo.py

The fixture prepends two items on the first scroll. The demo shows (a) a click by remembered index returning without error while clicking `alpha` instead of `delete-account`, (b) a click by stamped ref clicking the correct element, and (b2) a click on a removed element raising `StaleRef`. Captured output is in `demo/OUTPUT.txt`.

## Limitations
- The Hacker News measurement does not show a wrong click. In that run the old index 121 "is not present in read 2 at all", and the churn came from viewport filtering (`viewport_only: true`), not from the page rewriting itself. The report says so. The wrong-click-with-`ok: true` result comes from the local fixture.
- Whether a stale index always returns `ok` depends on the code path: `background.js` (lines ~2649-2673) returns `SC_STALE_REF` only if the index is absent from the last read or the element left the document. A reused index that still maps to a connected element succeeds silently.
- Infinite-scroll insertion on a real site is untested, per the same report.
- The demo reimplements the idea in about 50 lines; it does not exercise the bridge's code.
