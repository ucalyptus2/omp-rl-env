"""Smoke test: relay -> CDP discovery -> BrowserSession -> page capture.

Run on the machine whose Chrome has the relay extension installed:
    python smoke.py

Needs: `pip install -e .` (this package), rl-env-use importable
(sibling ../taskminer checkout), and browser-use installed.
"""

import asyncio
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
sys.path.insert(0, os.path.join(here, "taskminer"))  # sibling rl-env-use clone


async def main() -> int:
    from taskminer_omp.relay import check_browser_attached, ensure_relay, probe
    from taskminer_omp.browser_omp import browser

    try:
        url = ensure_relay()
    except RuntimeError as e:
        print(f"FAIL: {e}")
        return 1
    ver = probe(url) or {}
    print(f"1. relay up: {url}  ({ver.get('Browser', 'version unknown')})")

    try:
        ts = check_browser_attached(url)
    except RuntimeError as e:
        print(f"FAIL:\n{e}")
        return 1
    print(f"2. browser attached: {len(ts)} target(s) behind the relay")

    s = browser()
    try:
        # capture() is rl-env-use's own page reader: navigate + CDP
        # Runtime.evaluate + expand-clicks. If this works, the whole mining
        # pipeline's browser calls work.
        from rl_env_use.browse import capture

        page = await capture(s, "https://example.com", expand=False)
        assert page["text"].strip(), "empty page text"
        print(f"3. capture ok: {page['title']!r}, {len(page['text'])} chars via {page['via']}")
    except Exception as e:
        print(f"FAIL: BrowserSession drove the relay but capture broke: {type(e).__name__}: {e}")
        return 1
    finally:
        try:
            await s.close()
        except Exception:
            pass

    # one agent step through the relay, the way scout missions do it
    try:
        from browser_use import Agent
        from rl_env_use.llm import make_llm

        agent = Agent(
            task="Go to https://example.com and report its <h1> text. Then stop.",
            llm=make_llm(os.environ.get("TASKMINER_SMOKE_MODEL", "gpt-4o-mini")),
            browser_session=browser(),
        )
        h = await agent.run(max_steps=6)
        print(f"4. agent step ok: done={h.is_done()} steps={h.number_of_steps()}")
        await agent.close()
    except Exception as e:
        print(f"FAIL: agent loop broke on the relay: {type(e).__name__}: {e}")
        return 1

    print("OK: relay -> CDP -> BrowserSession -> capture -> agent all work.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
