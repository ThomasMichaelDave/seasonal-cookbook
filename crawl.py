"""Wider crawl -- task 4 in CLAUDE.md.

Enumerate recipe URLs from each source's sitemaps, then fetch and parse them
into the cache + database. This is the step up from spike.py's fixed 20/5/5
probe: it takes ALL matching URLs (optionally capped with --limit).

POLITENESS IS REUSED UNCHANGED. Every fetch goes through fetch.py, which keeps
the robots.txt check, the ~1.5 s/domain throttle with jitter, exponential
backoff and the HTML cache. "Wider" therefore means MORE pages at the SAME
polite rate -- never faster. Do not add concurrency here; one request per
domain at a time is the point.

Resumable: every page is cached in `pages`, so re-running an interrupted crawl
costs no network for anything already fetched. Parsing is idempotent
(persist.store_recipe), so re-parsing never duplicates rows.

Stores FACTS ONLY (see persist.py / docs/research.md): never instruction text.

Usage:
    py crawl.py --list-only                 # discover + report sizes + ETA, no fetch
    py crawl.py --source 15gram --limit 500 # an explicit --limit needs no --yes
    py crawl.py --all --limit 300           # 300 from each source
    py crawl.py --source delhaize --yes     # whole (unbounded) source

An explicit --limit is your conscious choice about scale, so it runs without
--yes. Only an unbounded run (no --limit) over BIG_RUN new fetches asks for it.
"""
import argparse
import re
import time
from collections import Counter

import config
import db
import fetch
import persist
import runlog
from parse import parse_recipe
from runlog import log
from spike import read_sitemap, now

# Rough per-request wall time: REQUEST_DELAY + half the jitter. Only used to
# print an ETA so a multi-hour crawl is a conscious choice, never a surprise.
SECS_PER_FETCH = config.REQUEST_DELAY + config.JITTER / 2
BIG_RUN = 400                    # above this many *new* fetches, confirm first


def _needs_confirmation(limit, n_new, assume_yes):
    """The size gate guards UNBOUNDED runs only. An explicit --limit is itself
    the conscious choice about scale, so it never also requires --yes."""
    return limit is None and n_new > BIG_RUN and not assume_yes


def discover(name, cfg):
    """Return (all_urls, matched_urls) for one source, from its sitemaps."""
    base = cfg["base_url"] + "/"
    sitemaps = fetch.sitemaps_for(base) or [cfg["base_url"] + "/sitemap.xml"]
    urls = []
    for sm in sitemaps:
        urls += read_sitemap(sm, budget=None)
    urls = list(dict.fromkeys(urls))

    pats = [re.compile(p, re.I) for p in cfg["url_patterns"]]
    excl = [re.compile(p, re.I) for p in cfg.get("url_excludes", [])]
    matched = [
        u for u in urls
        if any(p.search(u) for p in pats) and not any(e.search(u) for e in excl)
    ]
    return urls, matched


def report_prefixes(name, urls):
    from urllib.parse import urlparse
    counter = Counter()
    for u in urls:
        parts = [p for p in urlparse(u).path.split("/") if p]
        if parts:
            counter["/" + "/".join(parts[:2])] += 1
    log(f"  most common path prefixes in {name}:")
    for prefix, count in counter.most_common(10):
        log(f"     {count:>7,}  {prefix}")


def already_cached(conn, urls):
    """Subset of `urls` already present in the pages cache (no refetch needed)."""
    cached = set()
    for i in range(0, len(urls), 500):
        chunk = urls[i:i + 500]
        q = "SELECT url FROM pages WHERE url IN (%s)" % ",".join("?" * len(chunk))
        cached.update(r["url"] for r in conn.execute(q, chunk))
    return cached


def fmt_eta(n_fetches):
    secs = n_fetches * SECS_PER_FETCH
    if secs < 90:
        return f"~{secs:.0f}s"
    if secs < 5400:
        return f"~{secs/60:.0f} min"
    return f"~{secs/3600:.1f} h"


def crawl_source(conn, name, cfg, limit, list_only, assume_yes):
    sid = db.upsert_source(conn, name, cfg["base_url"], cfg["lang"])
    log(f"\n[{name}] {cfg['base_url']}")
    log(f"  robots root allowed = {fetch.allowed(cfg['base_url'] + '/')}")

    all_urls, matched = discover(name, cfg)
    log(f"  {len(all_urls):,} sitemap urls -> {len(matched):,} match "
        f"{cfg['url_patterns']}")
    if not matched:
        log("  !! nothing matched. Check url_patterns / sitemap by hand.")
        return Counter()
    report_prefixes(name, matched)

    targets = matched[:limit] if limit else matched
    cached = already_cached(conn, targets)
    n_new = len(targets) - len(cached)
    log(f"  plan: {len(targets):,} recipes ({len(cached):,} already cached, "
        f"{n_new:,} new fetches, ETA {fmt_eta(n_new)})")

    if list_only:
        return Counter()
    if _needs_confirmation(limit, n_new, assume_yes):
        log(f"  this whole-source run is {n_new:,} live requests ({fmt_eta(n_new)}). "
            f"Add --limit N to bound it, or --yes to crawl the whole source.")
        return Counter()

    # enqueue into the frontier so status is tracked
    for u in targets:
        conn.execute(
            "INSERT OR IGNORE INTO frontier(url, source_id, status, discovered_at) "
            "VALUES (?,?,'new',?)", (u, sid, now()))
    conn.commit()

    results = Counter()
    t0 = time.monotonic()
    for i, url in enumerate(targets, 1):
        html = fetch.fetch_into_cache(conn, url)   # polite; cached -> no network
        if not html:
            results["fetch_failed"] += 1
        else:
            rec = parse_recipe(html, url)
            if not rec:
                results["parse_failed"] += 1
            else:
                diet, ev, parsed = persist.analyse(rec)
                persist.store_recipe(conn, url, sid, cfg["lang"], rec, diet, ev, parsed)
                results[rec["parser"]] += 1
        if i % 20 == 0:
            conn.commit()
            done = sum(results.values())
            rate = i / max(time.monotonic() - t0, 1e-6)
            log(f"    {i:,}/{len(targets):,}  ok={done - results['fetch_failed'] - results['parse_failed']:,}"
                f"  fail={results['fetch_failed'] + results['parse_failed']:,}"
                f"  ({rate:.2f}/s)")
    conn.commit()
    detail = ", ".join(f"{k}={v:,}" for k, v in results.most_common()) or "nothing"
    log(f"  [{name}] done: {detail}")
    return results


def main():
    ap = argparse.ArgumentParser(description="Wider recipe crawl (polite, resumable).")
    ap.add_argument("--source", action="append", choices=list(config.SOURCES),
                    help="crawl only this source (repeatable). Default: all.")
    ap.add_argument("--all", action="store_true", help="crawl every source.")
    ap.add_argument("--limit", type=int, default=None,
                    help="max recipes per source (default: no cap).")
    ap.add_argument("--list-only", action="store_true",
                    help="discover + report sizes and ETA, fetch nothing.")
    ap.add_argument("--yes", action="store_true",
                    help="crawl a whole (unbounded) source even if it is a large "
                         "run. Not needed when --limit is given.")
    args = ap.parse_args()

    names = args.source or (list(config.SOURCES) if (args.all or args.list_only) else None)
    if not names:
        ap.error("pick --source NAME, --all, or --list-only.")

    conn = db.connect()
    db.init(conn)

    logfile = runlog.start("crawl")
    try:
        n_seas = conn.execute("SELECT COUNT(*) c FROM seasonality").fetchone()["c"]
        if not n_seas:
            log("note: seasonality table is empty -- run `python load_velt.py` so "
                "season scoring has data. Crawling anyway.")

        log("=" * 78)
        log("WIDER CRAWL" + ("  (list-only)" if args.list_only else ""))
        log("=" * 78)
        log(f"logging to {logfile}")
        if config.CONTACT_IS_PLACEHOLDER and not args.list_only:
            log("!! CONTACT is still the placeholder. Set COOKBOOK_CONTACT to your "
                "email before crawling (politeness). See config.py.")

        for name in names:
            crawl_source(conn, name, config.SOURCES[name], args.limit,
                         args.list_only, args.yes)

        if not args.list_only:
            n_rec = conn.execute("SELECT COUNT(*) c FROM recipes").fetchone()["c"]
            n_ing = conn.execute("SELECT COUNT(*) c FROM recipe_ingredients").fetchone()["c"]
            log("\n" + "=" * 78)
            log(f"TOTAL in db: recipes={n_rec:,}  ingredient lines={n_ing:,}")
            for row in conn.execute(
                "SELECT diet, COUNT(*) c FROM recipes GROUP BY diet ORDER BY c DESC"
            ):
                log(f"   {row['diet']:<12} {row['c']:,}")
    finally:
        log(f"\nfull log saved to: {logfile}")
        runlog.stop()


if __name__ == "__main__":
    main()
