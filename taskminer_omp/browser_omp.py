"""Drop-in replacement for rl_env_use.browse.browser: sessions attach to omp's
browser relay over CDP instead of Browser Use cloud / browser-use's own
Chromium.

Every browser touchpoint in rl-env-use goes through browse.browser():
scout (mining missions), verify (evidence re-checks), vanilla (the A/B
baseline), rollout and env (serving). page_text/capture/quote_in operate on
the BrowserSession via CDP and are browser-agnostic, so swapping this one
factory re-points the entire pipeline at the relay.
"""

import importlib

from .relay import ensure_relay

# modules that did `from .browse import browser` at module level: their bound
# name must be re-pointed. env.py imports it lazily inside the function, so
# patching rl_env_use.browse covers it.
_CONSUMERS = (
    "rl_env_use.scout",
    "rl_env_use.rollout",
    "rl_env_use.vanilla",
    "rl_env_use.verify",
)


def browser(
    allowed_domains: list[str] | None = None,
    headless: bool = True,
    profile_id: str | None = None,
    proxy_country: str | None = None,
):
    """Same signature as rl_env_use.browse.browser; every call site works
    unchanged. Notes on the params that don't survive the move:

    - headless: meaningless here, the relay drives the user's own (headed)
      Chrome. Kept for signature compatibility.
    - profile_id: the relay IS a profile (the user's logged-in Chrome); the
      cloud profile concept doesn't apply.
    - proxy_country: Browser Use cloud's residential proxies don't exist here;
      mining goes out over the machine's own IP. Warns once.
    """
    from browser_use import BrowserSession

    if proxy_country and not getattr(browser, "_proxy_warned", False):
        browser._proxy_warned = True  # noqa: SLF001
        print(
            "taskminer-omp: proxy_country is a Browser Use cloud feature; "
            "the relay browses from this machine's IP. Continuing."
        )
    kw = {"allowed_domains": allowed_domains} if allowed_domains else {}
    return BrowserSession(cdp_url=ensure_relay(), **kw)


def patch() -> None:
    """Install the relay-backed browser() everywhere rl-env-use looks for it.
    Call once before importing (or running) rl_env_use pipeline code."""
    import rl_env_use.browse as bmod

    bmod.browser = browser
    for name in _CONSUMERS:
        try:
            mod = importlib.import_module(name)
        except ImportError:
            continue
        if getattr(mod, "browser", None) is not bmod.browser:
            mod.browser = browser
