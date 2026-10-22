# taskminer-omp

Build RL environments from real web cases — rl-env-use's pipeline, mining
through **omp's browser relay** instead of Browser Use Cloud.

## Setup

On the machine whose Chrome will do the mining:

```bash
omp browser-relay install
# chrome://extensions -> Developer mode -> Load unpacked -> ~/.omp/browser-relay/extension
omp config set browser.relay true
# extension badge turns "on" once it reaches the relay
```

Then:

```bash
cd ~/workspace/taskminer-omp
pip install -e .
# rl-env-use checkout: clone https://github.com/browser-use/rl-env-use
# as a sibling directory named `taskminer`, or install it another way
python smoke.py   # 4 checks: relay -> CDP -> session -> capture -> agent step
```

`OMP_RELAY_URL` overrides the default `http://127.0.0.1:9224`.

## Use

Identical to rl-env-use — the adapter patches the browser seam, then hands
off to its CLI:

```bash
python -m taskminer_omp create "predict whether a completed trial met its primary endpoint from its registered protocol; ClinicalTrials.gov" --budget 40
python -m taskminer_omp build envs/<name>     # mine, review, build again for tasks
python -m taskminer_omp climb envs/<name> --model qwen-35b
```

No `BROWSER_USE_API_KEY` needed. Mining browser cost is $0; `--budget` now
means LLM inference only, so you can afford more/longer missions.

## How it works

See [ARCHITECTURE.md](ARCHITECTURE.md). One-line version: every browser
call in rl-env-use goes through `browse.browser()`; we return
`BrowserSession(cdp_url=<relay>)` there, and the relay's CDP impersonation
does the rest. Plan/mine/write/verify/panel/harden/climb/export are
untouched upstream code.
