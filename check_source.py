"""Vet a candidate recipe source: is it scrapable by THIS pipeline?

Reconnaissance, NOT a crawl -- one polite fetch per URL through fetch.py (robots
check, throttle, OS-trust-store TLS). Use it before adding a source to
config.SOURCES, especially the v2 candidates in docs/vegan_sources.md.

Reports, per host: native recipe-scrapers support + robots.txt (root, sitemaps);
per recipe URL: robots verdict, HTTP status, which parser route wins
(recipe_scrapers / wild / jsonld / nextdata) and what it extracted (title,
ingredient count, servings, instructions).

    py check_source.py https://plantyou.com/vegan-chili/
    py check_source.py URL1 URL2 ...
    py check_source.py --match https://www.vegrecipesofindia.com/aloo-gobi/
       (--match also prints diet + which ingredients resolve to a Velt canonical,
        the way to confirm the transliterated aliases fire on live text)
"""
import sys
from urllib.parse import urlparse

import fetch
import parse
import persist   # the real analyse pipeline: diet + seasonal canonical matches


def host_of(url: str) -> str:
    h = urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def assess(url: str, html: str | None) -> dict:
    """Pure: what would our pipeline make of this page? (no network)."""
    h = html or ""
    rec = parse.parse_recipe(html, url) if html else None
    return {
        "jsonld": "ld+json" in h,
        "nextdata": "__NEXT_DATA__" in h,
        "native": parse.has_native_scraper(url),
        "route": rec["parser"] if rec else None,
        "n_ingredients": len(rec["ingredients"]) if rec else 0,
        "title": rec.get("title") if rec else None,
        "servings": rec.get("servings") if rec else None,
        "total_min": rec.get("total_min") if rec else None,
        "instructions": bool(rec and rec.get("instructions")),
        "ok": bool(rec),
    }


def season_report(rec: dict):
    """(diet, [(raw, canonical, is_hero)...], n_ingredients) via the real pipeline.

    Uses persist.analyse so this is EXACTLY what a crawl would store -- the way
    to confirm a transliterated alias (gobi, baingan, hu luobo) actually resolves
    on a source's live ingredient strings before committing to a full crawl.
    """
    diet, _evidence, parsed = persist.analyse(rec)
    hits = [(p["raw"], p["canonical"], bool(p.get("is_hero")))
            for p in parsed if p["canonical"]]
    return diet, hits, len(parsed)


def check_host(url: str):
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    native = parse.has_native_scraper(url)
    print(f"host: {host_of(url)}")
    print(f"  native recipe-scrapers scraper: "
          f"{'YES' if native else 'no  (would use the wild/JSON-LD route)'}")
    print(f"  robots.txt root allowed: {fetch.allowed(base + '/')}")
    sms = fetch.sitemaps_for(base + "/")
    print(f"  sitemaps declared: {sms[:4] if sms else 'none in robots.txt'}")


def check_url(url: str, show_match: bool = False):
    print(f"\nrecipe: {url}")
    if not fetch.allowed(url):
        print("  robots.txt DISALLOWS this url -> do not crawl it.")
        return
    status, html = fetch.get(url)
    print(f"  http status: {status}   bytes: {len(html) if html else 0}")
    if not html:
        print("  no HTML (blocked / network error) -- can't assess.")
        return
    a = assess(url, html)
    print(f"  signals: JSON-LD~{'yes' if a['jsonld'] else 'no'}  "
          f"__NEXT_DATA__~{'yes' if a['nextdata'] else 'no'}")
    if not a["ok"]:
        print("  VERDICT: NOT parseable by our routes -> would need a dedicated parser.")
        return
    print(f"  VERDICT: SCRAPABLE via '{a['route']}'")
    print(f"     title:        {a['title']}")
    print(f"     ingredients:  {a['n_ingredients']}")
    print(f"     servings:     {a['servings']}   total_min: {a['total_min']}")
    print(f"     instructions: {'yes' if a['instructions'] else 'no'}")
    if show_match:
        diet, hits, n = season_report(parse.parse_recipe(html, url))
        print(f"     diet:         {diet}")
        print(f"     seasonal:     {len(hits)}/{n} ingredient(s) matched a Velt canonical")
        for raw, canon, hero in hits:
            print(f"        - {canon}{' (HERO)' if hero else ''}  <-  {raw}")


def main():
    urls = [u for u in sys.argv[1:] if u.startswith("http")]
    show_match = "--match" in sys.argv
    if not urls:
        print("usage: py check_source.py [--match] <recipe-url> [more-urls...]")
        print("  --match  also print diet + which ingredients resolve to a Velt")
        print("           canonical (use it to verify the transliterated aliases)")
        return
    print("recon only -- one polite fetch per url (robots-checked, throttled).")
    seen = set()
    for u in urls:
        h = host_of(u)
        if h not in seen:
            print()
            check_host(u)
            seen.add(h)
        check_url(u, show_match=show_match)


if __name__ == "__main__":
    main()
