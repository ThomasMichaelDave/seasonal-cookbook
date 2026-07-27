"""Polite fetching + raw HTML cache.

Rules this module enforces so you don't have to remember them:
  * robots.txt is checked once per domain and obeyed
  * one request per REQUEST_DELAY seconds PER DOMAIN, with jitter
  * exponential backoff on 429/5xx, capped by MAX_RETRIES
  * every response is cached; nothing is ever fetched twice
  * UTF-8 is forced on decode (Windows will otherwise mangle 'crème fraîche')
"""
import hashlib
import random
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from config import USER_AGENT, REQUEST_DELAY, JITTER, TIMEOUT, MAX_RETRIES, BACKOFF_BASE

_session = requests.Session()
_session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "nl-BE,nl;q=0.9,fr-BE;q=0.6,en;q=0.4",
})

_robots: dict[str, RobotFileParser] = {}
_last_hit: dict[str, float] = {}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _domain(url: str) -> str:
    return urlparse(url).netloc


def robots_for(url: str) -> RobotFileParser:
    dom = _domain(url)
    if dom not in _robots:
        rp = RobotFileParser()
        rp.set_url(f"{urlparse(url).scheme}://{dom}/robots.txt")
        try:
            rp.read()
        except Exception:
            # Unreachable robots.txt: assume allowed but stay slow.
            rp.parse(["User-agent: *", "Allow: /"])
        _robots[dom] = rp
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
        except requests.RequestException:
            if attempt == MAX_RETRIES:
                return None, None
            time.sleep(BACKOFF_BASE * (2 ** (attempt - 1)))
            continue

        if r.status_code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
            retry_after = r.headers.get("Retry-After")
            delay = float(retry_after) if (retry_after or "").isdigit() \
                else BACKOFF_BASE * (2 ** (attempt - 1))
            time.sleep(delay)
            continue

        # Force UTF-8 rather than trusting requests' charset guess.
        text = r.content.decode("utf-8", errors="replace")
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
