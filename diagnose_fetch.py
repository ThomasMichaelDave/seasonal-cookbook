"""One-off diagnostic for the 'discovered 0 urls' problem.

Not part of the pipeline. It answers a single question: when spike.py's
discovery step gets 0 urls from every sitemap, WHY? read_sitemap() swallows
the reason, so this reproduces the sitemap fetch with the error handling
turned off, using BOTH http clients (requests, like fetch.py; and urllib,
like the robots.txt reader) so we can see which one the network lets through.

Run:  py diagnose_fetch.py

Prints, per declared sitemap:
  - proxies each client sees
  - requests: exception OR (status, content-type, content-encoding, length,
    gzip-magic?, first bytes)
  - urllib:   same, for comparison
  - if the body parses as a sitemap index, it drills into the first child
    (this is where gzipped '.xml.gz' children reveal themselves)

Nothing is written to the database. This makes a handful of requests, no more.
"""
import gzip
import urllib.request
from urllib.error import URLError, HTTPError
from urllib.request import getproxies
from xml.etree import ElementTree

import requests

import config
import fetch

SM_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
UA = config.USER_AGENT
TIMEOUT = 30


def looks_gzip(b: bytes) -> bool:
    return len(b) >= 2 and b[0] == 0x1F and b[1] == 0x8B


def maybe_gunzip(b: bytes) -> bytes:
    if looks_gzip(b):
        try:
            return gzip.decompress(b)
        except OSError:
            return b
    return b


def show_bytes(b: bytes, n: int = 220) -> str:
    body = maybe_gunzip(b)
    head = body[:n].decode("utf-8", errors="replace").replace("\n", " ").replace("\r", " ")
    return head


def parse_locs(b: bytes):
    """Return (kind, count) where kind is 'index' | 'urlset' | 'unknown'."""
    body = maybe_gunzip(b)
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as e:
        return ("unparseable: " + str(e), [])
    tag = root.tag.split("}")[-1]
    locs = [loc.text.strip() for loc in root.findall(".//sm:loc", SM_NS) if loc.text]
    if not locs:
        # namespace mismatch? try namespace-agnostic
        locs = [e.text.strip() for e in root.iter() if e.tag.split("}")[-1] == "loc" and e.text]
        if locs:
            tag += " (NON-STANDARD NAMESPACE -- this is the bug)"
    return (tag, locs)


def probe_requests(url):
    print(f"    [requests] proxies={requests.utils.get_environ_proxies(url) or '{}'}")
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    except requests.RequestException as e:
        print(f"    [requests] EXCEPTION  {type(e).__name__}: {e}")
        return None
    enc = r.headers.get("Content-Encoding", "-")
    ct = r.headers.get("Content-Type", "-")
    b = r.content
    print(f"    [requests] status={r.status_code}  content-type={ct}  "
          f"content-encoding={enc}  len={len(b)}  gzip-magic={looks_gzip(b)}")
    print(f"    [requests] head: {show_bytes(b)}")
    if r.status_code == 200 and b:
        kind, locs = parse_locs(b)
        print(f"    [requests] parsed as: {kind}  locs={len(locs)}")
        return locs
    return None


def probe_urllib(url):
    print(f"    [urllib]   proxies={getproxies() or '{}'}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            b = resp.read()
            ct = resp.headers.get("Content-Type", "-")
            enc = resp.headers.get("Content-Encoding", "-")
            print(f"    [urllib]   status={resp.status}  content-type={ct}  "
                  f"content-encoding={enc}  len={len(b)}  gzip-magic={looks_gzip(b)}")
            kind, locs = parse_locs(b)
            print(f"    [urllib]   parsed as: {kind}  locs={len(locs)}")
            return locs
    except HTTPError as e:
        print(f"    [urllib]   HTTPError  status={e.code}  {e.reason}")
    except URLError as e:
        print(f"    [urllib]   URLError   {e.reason}")
    except Exception as e:
        print(f"    [urllib]   EXCEPTION  {type(e).__name__}: {e}")
    return None


def main():
    print("=" * 78)
    print("SITEMAP FETCH DIAGNOSTIC")
    print("=" * 78)
    print(f"user-agent: {UA}")
    print(f"env proxies (getproxies): {getproxies() or '{} (none set)'}")

    for name, cfg in config.SOURCES.items():
        base = cfg["base_url"] + "/"
        print("\n" + "-" * 78)
        print(f"[{name}] {cfg['base_url']}")
        sitemaps = fetch.sitemaps_for(base)
        if not sitemaps:
            print("  robots.txt declared no Sitemap: directive")
            sitemaps = [cfg["base_url"] + "/sitemap.xml"]
            print(f"  falling back to guess: {sitemaps}")
        else:
            print(f"  robots.txt declares {len(sitemaps)} sitemap(s)")

        for sm in sitemaps[:1]:  # first declared sitemap is enough to diagnose
            print(f"\n  sitemap: {sm}")
            r_locs = probe_requests(sm)
            u_locs = probe_urllib(sm)

            # If it's an index, drill into the first child to expose gzipped kids.
            child = None
            for locs in (r_locs, u_locs):
                if locs and locs[0].endswith((".xml", ".xml.gz", ".gz")):
                    child = locs[0]
                    break
            if child:
                print(f"\n  -> first child of index: {child}")
                probe_requests(child)

    print("\n" + "=" * 78)
    print("HOW TO READ THIS")
    print("=" * 78)
    print("""  * requests EXCEPTION but urllib status=200  -> proxy: requests isn't
        using your corporate proxy. Fix: set HTTPS_PROXY / HTTP_PROXY env vars.
  * gzip-magic=True and 'unparseable'                -> gzipped sitemap; the
        fetcher must gunzip before parsing.
  * status=403 / 429                                 -> bot-blocked on the
        sitemap path; needs slower/aged headers or a different entry point.
  * parsed as 'index' with locs>0                    -> discovery SHOULD work;
        the child fetch line shows where it breaks.
  * 'NON-STANDARD NAMESPACE'                          -> the SM_NS filter misses
        this site's <loc> tags; fetcher must match namespace-agnostically.""")


if __name__ == "__main__":
    main()
