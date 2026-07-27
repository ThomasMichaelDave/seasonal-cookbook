"""Polite fetching + raw HTML cache.

Rules this module enforces so you don't have to remember them:
  * robots.txt is checked once per domain and obeyed
  * one request per REQUEST_DELAY seconds PER DOMAIN, with jitter
  * exponential backoff on 429/5xx, capped by MAX_RETRIES
  * every response is cached; nothing is ever fetched twice
  * UTF-8 is forced on decode (Windows will otherwise mangle 'crème fraîche')
  * gzipped bodies (.xml.gz sitemaps) are transparently decompressed
  * TLS is verified against the OS trust store, not just certifi's bundle,
    so networks that do TLS interception (corporate proxies re-signing HTTPS
    with a private root CA) don't fail every request with
    CERTIFICATE_VERIFY_FAILED. urllib already uses the OS store; this brings
    requests to parity. See the truststore block below.
"""
import gzip
import hashlib
import random
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

# Use the operating system's trust store (which includes corporate/internal
# root CAs pushed by IT) instead of only certifi's Mozilla bundle. On a network
# that intercepts TLS, certifi rejects the re-signed certificate while the OS
# store trusts it -- that mismatch is why `requests` failed with
# CERTIFICATE_VERIFY_FAILED while `urllib` (which uses the OS store) succeeded.
# Guarded so a machine without truststore, or a non-Windows/limited install,
# simply falls back to certifi and keeps working on a normal network.
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:  # pragma: no cover - environment-dependent
    pass

from config import USER_AGENT, REQUEST_DELAY, JITTER, TIMEOUT, MAX_RETRIES, BACKOFF_BASE

_session = requests.Session()
_session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "nl-BE,nl;q=0.9,fr-BE;q=0.6,en;q=0.4",
})

_robots: dict[str, RobotFileParser] = {}
_robots_warned: set[str] = set()
_last_hit: dict[str, float] = {}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _domain(url: str) -> str:
    return urlparse(url).netloc


def _robots_from_response(robots_url: str, status, body) -> RobotFileParser:
    """Build a RobotFileParser from an already-fetched robots.txt response.

    Pure (no network) so the status-handling policy is unit-testable.

    Politeness is preserved: a real robots body (HTTP 200) is parsed and
    OBEYED -- a `Disallow: /` still blocks the whole site. What changes is only
    how a *blocked probe* is read. The stdlib `RobotFileParser.read()` turns a
    401/403 on the robots.txt fetch itself into disallow-all, silently banning
    an entire domain whenever a CDN/WAF (Cloudflare) or a corporate proxy
    (Zscaler) 403s the probe -- even though no Disallow rule was ever served,
    and even though the block often only targets the non-browser User-Agent the
    stdlib used rather than ours. RFC 9309 sec 2.3.1 instead classifies any 4xx
    as "Unavailable" -> no restrictions. We follow the RFC, but WARN once per
    host on 401/403 so an intentional site-level block is never bypassed in
    silence: the owner can still choose to drop the source by hand.
    """
    rp = RobotFileParser()
    rp.set_url(robots_url)
    if status == 200 and body:
        rp.parse(body.splitlines())
        return rp
    if status in (401, 403):
        dom = _domain(robots_url)
        if dom not in _robots_warned:
            _robots_warned.add(dom)
            print(f"  robots: {robots_url} -> HTTP {status}: probe blocked "
                  f"(CDN/WAF or proxy, not a Disallow rule). Treating the host "
                  f"as UNRESTRICTED per RFC 9309; verify by hand if unsure.",
                  flush=True)
    # 401/403/404/other 4xx, 5xx, or unreachable (status None): no robots rules
    # known -> assume allowed but stay slow (the per-domain throttle still runs).
    rp.parse(["User-agent: *", "Allow: /"])
    return rp


def robots_for(url: str) -> RobotFileParser:
    dom = _domain(url)
    if dom not in _robots:
        robots_url = f"{urlparse(url).scheme}://{dom}/robots.txt"
        # Fetch robots.txt through get() so it uses our real USER_AGENT and the
        # OS trust store (Zscaler-friendly) -- NOT bare urllib, whose default
        # UA and certifi-only TLS are exactly what get the probe 403'd.
        try:
            status, body = get(robots_url)
        except Exception:
            status, body = None, None
        _robots[dom] = _robots_from_response(robots_url, status, body)
    return _robots[dom]


def allowed(url: str) -> bool:
    try:
        return robots_for(url).can_fetch(USER_AGENT, url)
    except Exception:
        return True


def sitemaps_for(url: str) -> list[str]:
    """Sitemap: directives declared in robots.txt -- the polite way in."""
    rp = robots_for(url)
    try:
        sm = rp.site_maps()
        return list(sm) if sm else []
    except Exception:
        return []


def _throttle(dom: str):
    wait = REQUEST_DELAY + random.uniform(0, JITTER)
    last = _last_hit.get(dom)
    if last is not None:
        elapsed = time.monotonic() - last
        if elapsed < wait:
            time.sleep(wait - elapsed)
    _last_hit[dom] = time.monotonic()


def get(url: str) -> tuple[int | None, str | None]:
    """Fetch with retries. Returns (http_status, text). Text is UTF-8 decoded."""
    dom = _domain(url)
    for attempt in range(1, MAX_RETRIES + 1):
        _throttle(dom)
        try:
            r = _session.get(url, timeout=TIMEOUT)
        except requests.RequestException as e:
            if attempt == MAX_RETRIES:
                # Surface the reason instead of collapsing to a bare None. A
                # swallowed SSLError here is exactly what made discovery return
                # '0 urls' with no explanation.
                print(f"  fetch error: {url} -> {type(e).__name__}: {e}", flush=True)
                return None, None
            time.sleep(BACKOFF_BASE * (2 ** (attempt - 1)))
            continue

        if r.status_code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
            retry_after = r.headers.get("Retry-After")
            delay = float(retry_after) if (retry_after or "").isdigit() \
                else BACKOFF_BASE * (2 ** (attempt - 1))
            time.sleep(delay)
            continue

        # Decompress gzipped bodies. requests handles Content-Encoding: gzip
        # automatically, but a '.xml.gz' sitemap is served as gzip *content*
        # (not transfer encoding), so we detect the gzip magic bytes ourselves.
        content = r.content
        if content[:2] == b"\x1f\x8b":
            try:
                content = gzip.decompress(content)
            except OSError:
                pass  # not actually gzip; fall through and decode as-is

        # Force UTF-8 rather than trusting requests' charset guess.
        text = content.decode("utf-8", errors="replace")
        return r.status_code, text
    return None, None


def fetch_into_cache(conn, url: str) -> str | None:
    """Fetch a URL unless cached. Returns HTML or None. Updates frontier."""
    row = conn.execute("SELECT html FROM pages WHERE url=?", (url,)).fetchone()
    if row:
        return row["html"]

    if not allowed(url):
        conn.execute(
            "UPDATE frontier SET status='skipped_robots', note='disallowed' WHERE url=?",
            (url,),
        )
        conn.commit()
        return None

    status, html = get(url)
    conn.execute(
        "UPDATE frontier SET attempts=attempts+1, fetched_at=?, http_status=? WHERE url=?",
        (_now(), status, url),
    )
    if status == 200 and html:
        conn.execute(
            "INSERT OR REPLACE INTO pages(url, fetched_at, content_hash, html) VALUES (?,?,?,?)",
            (url, _now(), hashlib.sha256(html.encode("utf-8")).hexdigest(), html),
        )
        conn.execute("UPDATE frontier SET status='fetched' WHERE url=?", (url,))
        conn.commit()
        return html

    conn.execute("UPDATE frontier SET status='failed' WHERE url=?", (url,))
    conn.commit()
    return None
