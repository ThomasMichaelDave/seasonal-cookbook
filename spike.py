"""Phase 0 spike.

Run:  py spike.py

What it does, in order:
  1. seeds canonical produce + aliases from the Velt-shaped lexicon
  2. reads each source's robots.txt, reports what it allows and which
     sitemaps it declares
  3. walks sitemaps and REPORTS THE MOST COMMON PATH PREFIXES so you can
     tighten config.SOURCES[*]['url_patterns'] from evidence
  4. fetches a small sample per source into the cache
  5. runs every parser route and reports which one won, per source
  6. dumps every raw ingredient string to dumps/ingredients.txt, annotated
     with seasonal match and diet verdict

Step 6 is the point of the whole exercise. Read that file before you write
another line of parser code.
"""
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlparse
from xml.etree import ElementTree

import config
import db
import fetch
import persist
import runlog
from classify import classify_ingredient
from lexicon.seasonal import rows as seasonal_rows
from parse import parse_recipe
from runlog import log

SM_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
def seed_lexicon(conn):
    for nl, kind, en, pairs in seasonal_rows():
        conn.execute(
            "INSERT OR IGNORE INTO canonical(name_nl, name_en, kind) VALUES (?,?,?)",
            (nl, en, kind),
        )
        cid = conn.execute(
            "SELECT id FROM canonical WHERE name_nl=?", (nl,)
        ).fetchone()["id"]
        for alias, lang in pairs:
            conn.execute(
                "INSERT OR IGNORE INTO aliases(alias, lang, canonical_id) VALUES (?,?,?)",
                (alias.lower(), lang, cid),
            )
    conn.commit()
    n = conn.execute("SELECT COUNT(*) c FROM canonical").fetchone()["c"]
    a = conn.execute("SELECT COUNT(*) c FROM aliases").fetchone()["c"]
    log(f"  seeded {n} canonical produce items, {a} aliases")


# ---------------------------------------------------------------------------
def read_sitemap(url, depth=0, budget=None):
    """Return URLs from a sitemap or sitemap index (one level of nesting)."""
    if budget is not None and budget["n"] <= 0:
        return []
    status, xml = fetch.get(url)
    if status != 200 or not xml:
        log(f"     sitemap fetch failed: {url} -> status={status}")
        return []
    try:
        root = ElementTree.fromstring(xml.encode("utf-8"))
    except ElementTree.ParseError as e:
        log(f"     sitemap parse failed: {url} -> {e}")
        return []

    if root.tag.endswith("sitemapindex"):
        if depth >= 2:
            return []
        out = []
        children = [loc.text.strip() for loc in root.findall(".//sm:loc", SM_NS) if loc.text]
        for child in children[:12]:
            out += read_sitemap(child, depth + 1, budget)
            if budget is not None and budget["n"] <= 0:
                break
        return out

    urls = [loc.text.strip() for loc in root.findall(".//sm:loc", SM_NS) if loc.text]
    if budget is not None:
        budget["n"] -= 1
    return urls


def report_prefixes(name, urls):
    """The evidence you tune url_patterns from."""
    counter = Counter()
    for u in urls:
        parts = [p for p in urlparse(u).path.split("/") if p]
        if parts:
            counter["/" + "/".join(parts[:2])] += 1
    log(f"  most common path prefixes in {name} sitemaps:")
    for prefix, count in counter.most_common(12):
        log(f"     {count:>7,}  {prefix}")


def discover(conn, name, cfg, source_id):
    log(f"\n[{name}] {cfg['base_url']}")
    base = cfg["base_url"]

    log(f"  robots.txt: root allowed = {fetch.allowed(base + '/')}")
    sitemaps = fetch.sitemaps_for(base + "/")
    if sitemaps:
        log(f"  declares {len(sitemaps)} sitemap(s): {sitemaps[0]}")
    else:
        guesses = [f"{base}/sitemap.xml", f"{base}/sitemap_index.xml"]
        log(f"  no Sitemap: directive -- trying {guesses}")
        sitemaps = guesses

    urls = []
    for sm in sitemaps[:4]:
        urls += read_sitemap(sm, budget={"n": 25})
    urls = list(dict.fromkeys(urls))
    log(f"  discovered {len(urls):,} urls from sitemaps")
    if not urls:
        log("  !! nothing found. Inspect the sitemap by hand before continuing.")
        return []
    report_prefixes(name, urls)

    pats = [re.compile(p, re.I) for p in cfg["url_patterns"]]
    excl = [re.compile(p, re.I) for p in cfg.get("url_excludes", [])]
    matched = [
        u for u in urls
        if any(p.search(u) for p in pats) and not any(e.search(u) for e in excl)
    ]
    log(f"  {len(matched):,} match url_patterns {cfg['url_patterns']}")

    sample = matched[: config.SPIKE_SAMPLE[name]]
    for u in sample:
        conn.execute(
            "INSERT OR IGNORE INTO frontier(url, source_id, status, discovered_at) "
            "VALUES (?,?,'new',?)",
            (u, source_id, now()),
        )
    conn.commit()
    return sample


# ---------------------------------------------------------------------------
def probe(conn, name, urls, source_id, lang, dump):
    if not urls:
        log(f"  [{name}] no urls to probe")
        return Counter()

    results = Counter()
    log(f"  fetching + parsing {len(urls)} pages...")
    for url in urls:
        html = fetch.fetch_into_cache(conn, url)
        if not html:
            results["fetch_failed"] += 1
            continue

        rec = parse_recipe(html, url)
        if not rec:
            results["parse_failed"] += 1
            log(f"     PARSE FAIL  {url}")
            continue

        results[rec["parser"]] += 1

        # analyse + store go through persist so the probe and the wider crawl
        # (crawl.py) use exactly the same idempotent storage. Keep the dump
        # writing here -- that is the probe's whole reason for existing.
        diet, evidence, parsed = persist.analyse(rec)
        persist.store_recipe(conn, url, source_id, lang, rec, diet, evidence, parsed)

        heroes = [p["canonical"] for p in parsed if p.get("is_hero") and p["canonical"]]
        dump.write(f"\n{'='*78}\n{name} | {rec.get('title')}\n{url}\n")
        dump.write(f"diet={diet}  seasonal_heroes={heroes or '-'}\n{'-'*78}\n")
        for p in parsed:
            v, _ = classify_ingredient(p["raw"])
            tag = f"[{p['canonical']}{'*' if p.get('is_hero') else ''}]" if p["canonical"] else ""
            qty = f"{p['qty']:g}" if p["qty"] is not None else "?"
            dump.write(f"  {qty:>6} {str(p['unit'] or ''):<7} {str(p['ingredient_text'])[:44]:<46}"
                       f" {v:<11} {tag}\n")
            dump.write(f"         raw: {p['raw']}\n")
    conn.commit()
    return results


# ---------------------------------------------------------------------------
def selftest():
    """Fast pre-crawl smoke check on the diet lexicon.

    Cases live in tests/diet_cases.py so the pytest suite and this check can
    never drift apart. Run `python -m pytest` for the full suite.
    """
    try:
        from tests.diet_cases import DIET_CASES as cases
    except ImportError:
        log("  (tests/ not present -- skipping smoke check)")
        return True

    fails = []
    for text, expected in cases:
        got, ev = classify_ingredient(text)
        if got != expected:
            fails.append(f"    {text!r}: expected {expected}, got {got} {sorted(ev)}")
    log(f"\nself-test: {len(cases)-len(fails)}/{len(cases)} passed")
    for f in fails:
        log(f)
    return not fails


# ---------------------------------------------------------------------------
def main():
    config.DUMP_DIR.mkdir(exist_ok=True)
    conn = db.connect()
    db.init(conn)

    logfile = runlog.start("spike")
    try:
        _run(conn, logfile)
    finally:
        log(f"\nfull log: {logfile}")
        runlog.stop()


def _run(conn, logfile):
    log("=" * 78)
    log("PHASE 0 SPIKE")
    log("=" * 78)
    log(f"logging to {logfile}")

    log("\n[1] seeding seasonal lexicon")
    seed_lexicon(conn)
    n_seas = conn.execute("SELECT COUNT(*) c FROM seasonality").fetchone()["c"]
    if n_seas:
        log(f"  seasonality: {n_seas} rows loaded")
    else:
        log("  seasonality: EMPTY -- run `python load_velt.py` to load the calendar")

    log("\n[2] self-test on diet classification")
    ok = selftest()
    if not ok:
        log("  !! fix the lexicon before trusting the veg/vegan switch")

    if "--offline" in sys.argv:
        log("\n--offline: stopping before any network access.")
        return

    if config.CONTACT_IS_PLACEHOLDER:
        log("\n!! CONTACT is still the placeholder. Set COOKBOOK_CONTACT to your "
            "email before fetching (politeness). See config.py.")

    log("\n[3] discovery")
    plan = {}
    for name, cfg in config.SOURCES.items():
        sid = db.upsert_source(conn, name, cfg["base_url"], cfg["lang"])
        plan[name] = (discover(conn, name, cfg, sid), sid, cfg["lang"])

    log("\n[4] fetch + parse probes")
    dump_path = config.DUMP_DIR / "ingredients.txt"
    summary = {}
    with open(dump_path, "w", encoding="utf-8") as dump:
        for name, (urls, sid, lang) in plan.items():
            log(f"\n  [{name}]")
            summary[name] = probe(conn, name, urls, sid, lang, dump)

    log("\n" + "=" * 78)
    log("RESULT: which parser route won, per source")
    log("=" * 78)
    for name, counts in summary.items():
        detail = ", ".join(f"{k}={v}" for k, v in counts.most_common()) or "nothing parsed"
        log(f"  {name:<16} {detail}")

    n_recipes = conn.execute("SELECT COUNT(*) c FROM recipes").fetchone()["c"]
    n_ing = conn.execute("SELECT COUNT(*) c FROM recipe_ingredients").fetchone()["c"]
    n_matched = conn.execute(
        "SELECT COUNT(*) c FROM recipe_ingredients WHERE canonical_id IS NOT NULL"
    ).fetchone()["c"]
    log(f"\n  recipes={n_recipes}  ingredient lines={n_ing}  "
        f"seasonal matches={n_matched} "
        f"({100*n_matched/n_ing:.0f}%)" if n_ing else "")

    log("\n  diet breakdown:")
    for row in conn.execute(
        "SELECT diet, COUNT(*) c FROM recipes GROUP BY diet ORDER BY c DESC"
    ):
        log(f"     {row['diet']:<12} {row['c']}")

    log(f"\n  >> now READ {dump_path}")
    log("     Every ingredient string, with what the parser made of it.")
    log("     That file tells you what to fix next.")


if __name__ == "__main__":
    main()
