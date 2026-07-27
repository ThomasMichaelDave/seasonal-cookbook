# Seizoenskookboek — a seasonal cookbook for Belgium

Scrape Belgian recipe sites, map their ingredients onto the **Velt** seasonal
produce calendar, then generate a seasonal week of main dishes + a grocery list,
delivered as a single standalone `cookbook.html`.

Personal, non-commercial, single-household project. Developed on **Windows**.
For context and design rationale, read `CLAUDE.md` and `docs/`.

---

## Sources

v1 is Belgian (Dutch) only. Recipe pages are fetched politely (robots.txt,
~1 req/sec per domain) and cached; only facts are parsed out.

| Website | Lang | Parser route | Notes |
|---|---|---|---|
| **15gram.be** | NL | native `recipe-scrapers` | ~6,000 recipes, cleanest |
| **dagelijksekost.vrt.be** | NL | native `recipe-scrapers` | Jeroen Meus / VRT, authentic Flemish |
| **delhaize.be** | NL | `wild` → JSON-LD → `__NEXT_DATA__` | no native scraper |

Seasonal backbone: **Velt *Groente- en fruitkalender*** (2019) — 421 rows, 70
crops, all 12 months. See `docs/velt.md`. A v2 winter-coverage survey (Indian /
Korean / N-Chinese / Greek) is in `docs/vegan_sources.md`.

### Vetting a new source

Before adding a site to `config.SOURCES`, check whether this pipeline can parse
it — recon only, one polite fetch per URL:

```bat
py check_source.py https://some-site.com/a-recipe/
```

It reports native `recipe-scrapers` support, robots.txt, and — for each recipe
URL — which parser route wins (`recipe_scrapers` / `wild` / `jsonld` /
`nextdata`) plus the ingredients/servings/instructions it extracted. `route:
None` means it would need a dedicated parser.

---

## Setup (Windows, behind a corporate proxy such as Zscaler)

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt          :: truststore makes TLS trust the OS/Zscaler CA
set PYTHONUTF8=1                          :: not optional -- else cp1252 mangles crème/maïs
setx COOKBOOK_CONTACT "you@example.be"    :: your email, via env (not the tracked config.py)
```

`PYTHONUTF8=1` and `COOKBOOK_CONTACT` are read every run; `setx` makes them
permanent (reopen the shell afterwards).

## Building the database

`cookbook.db` (gitignored) is built in these steps. Only steps 2–3 touch the
network, and they are rate-limited by design.

```bat
py load_velt.py                           :: 1. load the Velt calendar (offline)
py crawl.py --list-only                   :: 2. sizes + ETA (reads sitemaps only)
py crawl.py --source 15gram --limit 500   :: 3. crawl -> parse -> store (facts + method)
py crawl.py --source dagelijksekost --limit 500
py crawl.py --source delhaize --limit 200
py report.py                              :: 4. coverage: hero %, staple/course mix, per-month
py export.py                              :: 5. -> cookbook.html (standalone, offline)
```

- Resumable: pages are cached, so re-running a crawl re-fetches nothing already
  fetched. Idempotent: re-parsing never duplicates rows.
- `py crawl.py --reparse` re-parses every cached page **offline** — use it after
  a parser/lexicon change, or to backfill fields into an existing db.
- `py export.py --no-instructions` writes a shareable, facts-only file.

## Using it (offline, reads `cookbook.db`)

```bat
py planner.py --month 9 --diet vegetarian   :: a seasonal week of 7 mains
py grocery.py --month 9 --diet vegetarian   :: that week's grocery list, by aisle
py export.py                                :: the interactive standalone app
```

`cookbook.html` runs entirely in the browser: month picker, diet toggle,
household size, per-dish lock/reroll, a "restjesdag" (leftovers) mode, and the
full recipe per dish.

---

## The modules

**Pipeline**
| File | Role |
|---|---|
| `config.py` | sources, politeness knobs, household/week size; `COOKBOOK_CONTACT` |
| `db.py` | SQLite schema + connection + migrations |
| `fetch.py` | polite fetching (robots, throttle, backoff), HTML cache, OS-trust-store TLS, gzip sitemaps |
| `parse.py` | 4 parser routes, best-first; normalises instructions |
| `persist.py` | idempotent recipe storage (shared by crawl + spike) |
| `crawl.py` | wider crawl: discover, fetch, parse, store; `--list-only`/`--limit`/`--reparse` |
| `spike.py` | the original Phase-0 probe (20/5/5) → `dumps/ingredients.txt` |
| `check_source.py` | vet a candidate site: native support, robots, which route wins (recon, not a crawl) |
| `runlog.py` | tee logging to timestamped `logs/` |

**Classification** (all offline, dump-reviewable)
| File | Role |
|---|---|
| `matching.py` | shared Dutch-compound token matcher (`matches`/`hit`/`strip_false_friends`) |
| `lexicon/animal.py` | meat/fish/dairy/egg lexicon + compound traps (the veg/vegan switch) |
| `lexicon/seasonal.py` | ~77 canonical produce items, NL/FR/EN aliases |
| `classify.py` | ingredient parsing, diet verdict, seasonal match, hero detection, `season_score` |
| `staples.py` | staple-base classifier: potato / rice / grain / pasta / bread |
| `courses.py` | course filter: main vs dessert/side |

**Seasonal data**
| File | Role |
|---|---|
| `transcribe_velt.py` | Velt calendar → auditable CSV |
| `load_velt.py` | CSV → `seasonality` table (+ reconciliation report) |

**Planning & output**
| File | Role |
|---|---|
| `season.py` | DB-backed season scoring (which mains have a hero in season this month) |
| `planner.py` | `plan_week(month, diet, strictness, seed)` → 7 varied, in-season mains, scaled |
| `grocery.py` | aggregate a week, scale, merge duplicates, group by aisle |
| `report.py` | corpus coverage incl. the honest per-month in-season-mains figure |
| `export.py` | build the standalone `cookbook.html` (data + logic inlined) |
| `diagnose_fetch.py` | one-off TLS/sitemap diagnostic (not part of the pipeline) |

---

## Tests

```bat
py -m pytest        :: 280 tests, no network
```

Parser routes run against hand-written fixtures in `tests/fixtures/` (no
third-party content committed). Each classifier also writes a human-readable
dump (`dumps/staples.txt`, `courses.txt`, …) for eyeballing.

## What is and isn't stored

Ingredients, quantities, servings, timings and the **source link** are facts and
always stored. Method prose is copyrightable: for this private household it *is*
stored and shown, but only in the **gitignored** `cookbook.db` / `cookbook.html`
— never committed, never published. `export.py --no-instructions` gives a
facts-only file. See `docs/decisions.md` #8 and `docs/research.md`.
