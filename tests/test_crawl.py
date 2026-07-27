"""crawl.py: the offline logic -- discovery filtering, cache accounting, ETA.

The networked fetch loop is not exercised here (no crawling in tests); these
cover the parts that decide WHAT gets fetched and how the run is reported.
"""
import config
import crawl
import db


def test_discover_matches_patterns_and_excludes(monkeypatch):
    urls = [
        "https://www.delhaize.be/nl/recepten/receptDetails/A/r/1",
        "https://www.delhaize.be/nl/recepten/receptDetails/B/r/2",
        "https://www.delhaize.be/nl/search/tomaat",      # excluded by url_excludes
        "https://www.delhaize.be/nl/winkels/gent",        # doesn't match patterns
    ]
    monkeypatch.setattr(crawl.fetch, "sitemaps_for", lambda base: ["sm"])
    monkeypatch.setattr(crawl, "read_sitemap", lambda sm, budget=None: list(urls))

    all_urls, matched = crawl.discover("delhaize", config.SOURCES["delhaize"])
    assert len(all_urls) == 4
    assert len(matched) == 2
    assert all("/receptDetails/" in u for u in matched)


def test_discover_dedups(monkeypatch):
    urls = ["https://15gram.be/recepten/a", "https://15gram.be/recepten/a",
            "https://15gram.be/recepten/b"]
    monkeypatch.setattr(crawl.fetch, "sitemaps_for", lambda base: ["sm"])
    monkeypatch.setattr(crawl, "read_sitemap", lambda sm, budget=None: list(urls))
    all_urls, matched = crawl.discover("15gram", config.SOURCES["15gram"])
    assert len(matched) == 2


def test_already_cached_reports_only_cached_urls():
    conn = db.connect(":memory:")
    db.init(conn)
    sid = db.upsert_source(conn, "15gram", "https://15gram.be", "nl")
    cached_url = "https://15gram.be/recepten/a"
    conn.execute("INSERT INTO frontier(url, source_id, status, discovered_at) "
                 "VALUES (?,?,'fetched','now')", (cached_url, sid))
    conn.execute("INSERT INTO pages(url, fetched_at, content_hash, html) "
                 "VALUES (?,?,?,?)", (cached_url, "now", "h", "<html/>"))
    conn.commit()

    got = crawl.already_cached(conn, [cached_url, "https://15gram.be/recepten/b"])
    assert got == {cached_url}


def test_fmt_eta_scales():
    assert crawl.fmt_eta(1).endswith("s")
    assert "min" in crawl.fmt_eta(200)
    assert crawl.fmt_eta(20000).endswith("h")


def test_explicit_limit_never_needs_yes():
    big = crawl.BIG_RUN + 100
    # explicit --limit is consent: no --yes required, however big
    assert crawl._needs_confirmation(limit=500, n_new=big, assume_yes=False) is False
    # unbounded (no --limit) large run still asks for --yes
    assert crawl._needs_confirmation(limit=None, n_new=big, assume_yes=False) is True
    # ...unless --yes is given
    assert crawl._needs_confirmation(limit=None, n_new=big, assume_yes=True) is False
    # small unbounded run runs freely
    assert crawl._needs_confirmation(limit=None, n_new=10, assume_yes=False) is False
