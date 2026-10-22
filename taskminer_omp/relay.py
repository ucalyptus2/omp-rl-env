"""omp browser-relay lifecycle: resolve the relay's CDP endpoint, adopt a running
server or start one, and check that a real browser is attached behind it.

The relay impersonates Chrome's CDP discovery endpoint
(packages/coding-agent/src/tools/browser/relay/kind.ts: "so beyond kind
resolution the entire connected-browser machinery applies unchanged"), which
is why browser-use's BrowserSession(cdp_url=...) can attach to it directly.

Default endpoint: http://127.0.0.1:9224 (omp's DEFAULT_RELAY_URL).
Override with OMP_RELAY_URL.
"""

import os
import shutil
import subprocess
import time

import httpx

DEFAULT_RELAY_URL = "http://127.0.0.1:9224"


def relay_url() -> str:
    return os.environ.get("OMP_RELAY_URL", DEFAULT_RELAY_URL).rstrip("/")


def _port(url: str) -> int:
    return int(url.rsplit(":", 1)[-1].split("/")[0])


def probe(url: str, timeout: float = 3.0) -> dict | None:
    """CDP discovery: /json/version answers like Chrome when the relay is up."""
    try:
        r = httpx.get(url + "/json/version", timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def targets(url: str, timeout: float = 5.0) -> list:
    """Tabs the relay currently exposes. Empty = server up, no browser attached."""
    try:
        r = httpx.get(url + "/json/list", timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


def ensure_relay(url: str | None = None, start: bool = True, wait_s: float = 30.0) -> str:
    """Return a live relay URL. Adopts an already-running relay (the CLI itself
    treats EADDRINUSE + a live probe as success); otherwise starts
    `omp browser-relay serve` and waits for the CDP endpoint to answer."""
    url = (url or relay_url()).rstrip("/")
    if probe(url):
        return url
    if not start:
        raise RuntimeError(
            f"no omp browser relay at {url} "
            "(set OMP_RELAY_URL or run `omp browser-relay serve`)"
        )
    omp = shutil.which("omp")
    if not omp:
        raise RuntimeError(
            f"no relay at {url} and `omp` is not on PATH "
            "(install oh-my-pi: https://github.com/can1357/oh-my-pi)"
        )
    subprocess.Popen(
        [omp, "browser-relay", "serve", "--port", str(_port(url))],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + wait_s
    while time.time() < deadline:
        if probe(url):
            return url
        time.sleep(0.5)
    raise RuntimeError(f"`omp browser-relay serve` did not come up at {url}")


def check_browser_attached(url: str | None = None) -> list:
    """Raise a helpful error when the relay is up but no browser is behind it
    (the companion extension is not installed/connected)."""
    url = (url or relay_url()).rstrip("/")
    ts = targets(url)
    if not ts:
        raise RuntimeError(
            "relay is up but no browser is attached behind it.\n"
            "  1. omp browser-relay install   # writes the extension to ~/.omp/browser-relay/extension\n"
            "  2. load it in Chrome: chrome://extensions -> Developer mode -> Load unpacked\n"
            "  3. omp config set browser.relay true\n"
            "The extension badge turns 'on' once it reaches the relay; then re-run."
        )
    return ts
