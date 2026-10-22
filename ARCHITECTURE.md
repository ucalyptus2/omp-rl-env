# taskminer-omp: architecture

A task miner like browser-use's [rl-env-use](https://github.com/browser-use/rl-env-use),
with the web-mining engine swapped from Browser Use Cloud to **omp's browser
relay** (`omp browser-relay`, default `http://127.0.0.1:9224`).

## The seam

rl-env-use's mining pipeline funnels every browser interaction through one
function, `rl_env_use.browse.browser()`:

| call site | what it does |
|---|---|
| `scout.py` (missions) | `Agent(..., browser_session=browser(headless=...))` — the miners |
| `verify.py` | re-checks evidence quotes against live pages |
| `vanilla.py` | the Claude-Code-vs-agents A/B baseline |
| `rollout.py`, `env.py` | serving the env (env.py imports it lazily) |

`page_text()`, `capture()`, `quote_in()` all operate on the `BrowserSession`
through CDP (`Runtime.evaluate`) — they are browser-agnostic. So the entire
adaptation is **one factory function**: return a `BrowserSession` attached to
the relay instead of the cloud.

## Why CDP attach works

omp's relay "impersonates Chrome's CDP discovery endpoint, so beyond kind
resolution the entire connected-browser machinery applies unchanged"
(`packages/coding-agent/src/tools/browser/relay/kind.ts`). browser-use's
`BrowserSession(cdp_url=...)` is the documented attach pattern (TestingBot's
official integration uses exactly this). The relay multiplexes downstream
connections over Chrome's single debugger attachment per tab, so parallel
missions are fine.

`taskminer_omp.patch()` re-points `browser` in `rl_env_use.browse` plus the
four modules that bound it at import time (scout, rollout, vanilla, verify).
`python -m taskminer_omp` patches, then delegates to rl-env-use's own CLI —
plan/mine/write/verify/panel/harden/climb/export run untouched.

## What changes vs Browser Use Cloud

- **Cost.** Missions were $0.15–0.40 each on the cloud (~$17 of the $72
  trial-forecast example). On the relay the browser is free; `--budget` now
  covers LLM inference only. Optimal strategy shifts: more missions, longer
  missions, cheaper iteration.
- **Identity.** The relay drives *your own Chrome* via the companion
  extension — real fingerprint, real IP, your logged-in sessions. rl-env-use
  explicitly supports login profiles for mining gated communities; the relay
  is that feature for free. There is no `proxy_country` (warns once, no-op).
- **Placement.** Mining runs on the machine whose Chrome has the extension,
  not a cloud fleet. Concurrency is bounded by that machine.
- **`headless` is vestigial.** Kept in the signature so call sites don't
  change; the relay is headed by nature.

## What stays identical

The evidence bar that makes the whole thing work: facts are only accepted if
their quote is literally present in live page text (checked via CDP at record
time), materials are sliced verbatim from pages, gold answers come from
outcome quotes, the frontier panel re-hardens saturated tasks, forecasts must
move with the materials. None of that touches the browser backend.

## Risks

1. **CDP surface gaps.** The relay's impersonation is built for puppeteer;
   browser-use drives CDP directly. The smoke test (`python smoke.py`)
   walks relay → discovery → session → capture → one agent step; if step 3
   or 4 fails, the gap is identified before any mining budget is spent.
2. **Extension not connected.** `check_browser_attached()` fails loud with
   the three setup commands instead of mining against an empty target list.
3. **Upstream drift.** We don't fork rl-env-use; the adapter is ~150 lines
   against a one-function seam. If upstream renames the seam, `patch()`
   needs one new module name.

## Layout

```
taskminer_omp/
  relay.py        resolve/adopt/start the relay; CDP probe; attached-browser check
  browser_omp.py  browser() factory (the seam) + patch()
  __main__.py     patch, then run rl-env-use's CLI
smoke.py          4-stage verification, run where Chrome+extension live
```
