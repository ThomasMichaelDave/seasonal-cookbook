# Status report — Seasonal Cookbook

Point-in-time snapshot for review. Written to be scrutinised: it flags what is
tested, what is heuristic, and what is unbuilt.

- **Branch:** `claude/archive-upload-planning-4kcb54`
- **Head:** `b498ccc`
- **Tests:** 239 passing, no network required
- **Code:** ~2,700 LOC across 15 root modules + 14 test files
- **Corpus (owner's machine):** 604 recipes, 8,773 ingredient lines — see §4

---

## 1. What this is

A season-based cookbook for Belgium. It scrapes Belgian recipe sites, maps
ingredients onto the Velt seasonal produce calendar, and (not yet built)
generates a week of main dishes + a grocery list. Personal, non-commercial;
owner develops on Windows behind a Zscaler TLS-inspection proxy. v1 is Belgian
(Dutch) only.

## 2. Pipeline & architecture

```
sitemaps ─► fetch.py ─► pages cache (SQLite) ─► parse.py ─► persist.py ─► recipes / recipe_ingredients
            (robots,       (raw HTML,            (4 routes,   (idempotent      │
             throttle,      re-parse from         best-first)  upsert)          ▼
             backoff,       cache, never re-                          classify.py  (diet, seasonal
             TLS, gzip)     hit the network)                          match, hero, season score)
```

Load-bearing design decisions (`docs/decisions.md`):
- **Fetch and parse are permanently separate.** Raw HTML is cached; parsing
  always reads cache, so the parser can be rewritten without re-crawling.
- **Store facts only.** Ingredients, quantities, servings, timings, source URL.
  No instruction text / images (copyright — `recipes` has no such column, and a
  test asserts prose can't leak in).
- **Derived, never authoritative:** seasonal hero, season score, staple base,
  course. Recompute freely.
- **~60–80 produce items get canonical IDs**; everything else is fuzzy-grouped
  later. Aromatics (ui/sjalot/knoflook) are never seasonal heroes.

The per-recipe axes the planner needs now all exist:
**diet** · **seasonal hero (+ in-season by month, via `season_score`)** ·
**staple base** · **course**.

## 3. Component status

| Component | File | State | Guarded by |
|---|---|---|---|
| SQLite schema | `db.py` | done | — |
| Polite fetcher + cache | `fetch.py` | done, **live-tested**; OS trust store (Zscaler), gzip sitemaps, error surfacing | — |
| Parser routes | `parse.py` | done, **live-confirmed**: 15gram/DK native, Delhaize `wild` | `test_parse` |
| Shared persistence | `persist.py` | done — idempotent upsert (fixes a re-run FK crash) | `test_persist` |
| Diet classifier | `classify.py` | done, **39 wild cases** (steak/entrecote/sardienen/halloumi/gehakte added post-crawl) | `test_diet`, `diet_cases` |
| Seasonal lexicon (77 items) | `lexicon/` | done, seeded; vowel-shortening plurals fixed | `test_seasonal`, `test_plurals` |
| Hero detection + season score | `classify.py` | done, tested | `test_seasonal` |
| Velt calendar | `load_velt.py` | **loaded — 421 rows, 70 crops, 12 months** | `test_velt` |
| Wider crawler | `crawl.py` | done — polite, resumable, `--list-only`/`--limit`/`--all`, ETA, size gate | `test_crawl` |
| Staple-base classifier | `staples.py` | done — potato/rice/grain/pasta/bread, dump-reviewed twice | `test_staples` |
| Course filter | `courses.py` | done — main vs dessert/side | `test_courses` |
| Corpus report | `report.py` | done — coverage, hero, staple, course, planner pool | `test_report` |
| Tee logging | `runlog.py` | done — timestamped `logs/` | `test_runlog` |
| **Season filter by month** | — | **not started** — next step |  |
| **Menu planner** | — | **not started** |  |
| **Grocery list** | — | **not started** |  |
| **UI (single-file browser app)** | — | **not started** (form decided) |  |

## 4. Corpus snapshot

Measured on the owner's machine (crawl of 2026-07-27; 15gram 500, DK 99,
Delhaize 5 = **604 recipes**, 8,773 ingredient lines). `cookbook.db` is
gitignored, so these are reported numbers, not reproducible from the repo alone.

- **Diet:** omnivore 409 (68%), vegetarian 144 (24%), vegan 37 (6%), uncertain 14 (2%)
- **Seasonal hero coverage:** 558/604 = **92%** (the gating number — high enough
  that the lexicon does not need to grow before the planner)
- **Season-neutral:** 46 (8%) — kept, not filtered
- **Staple base:** potato 152, pasta 143, bread 98, rice 81, grain 52, none 78
- **Course:** not yet measured on the real corpus (filter added after the last
  `report.py` run) — expect ~25 of the 78 `none` to be desserts
- **Servings present:** 604/604 = **100%** (ideal for household scaling)
- **Parsed quantities:** 6,409/8,773 = **73%** (the missing 27% are unquantified
  seasonings — fine for scaling the mains)

**Caveat for review:** stored `canonical_id`/`is_hero` were written *before* the
vowel-shortening plural fix (`b498ccc`), which changes `match_seasonal` for
raap/bloemkool/pastinaak/koolraap/aardpeer. A re-run of `crawl.py` re-parses
from cache (no network) and refreshes them; the 92% figure may tick up slightly
after that.

## 5. Test & quality posture

- **239 tests, zero network.** Parser routes run against hand-written fixtures
  (no third-party content committed). `tests/diet_cases.py` is shared by the
  suite and `spike.py`'s pre-crawl smoke check so they can't drift.
- **Review-by-dump workflow.** Each classifier writes a human-readable dump
  (`dumps/ingredients.txt`, `staples.txt`, `courses.txt`) that the owner
  eyeballs; misclassifications become new test cases. Diet and staple
  classifiers have each been through this loop against the real 604-recipe
  corpus; course has not yet.
- **Two networked commands only** (`spike.py`, `crawl.py`), rate-limited ~1
  req/sec/domain, both tee to `logs/`.

## 6. Known limitations & risks

1. **Classifiers are Dutch string-matching heuristics**, not ML. They work well
   on this corpus but every improvement has so far come from reading real
   strings. Expect a long tail; the dump workflow is the mitigation.
2. **Corpus is narrow and 15gram-dominated** (500/604). 15gram is meal-kit-style
   (uniform servings, tidy strings), which flatters the parser. Dagelijkse Kost
   (99) is messier and Delhaize (5) is barely sampled — the `wild` route on
   Delhaize is under-tested at scale.
3. **The strictness dial is inert.** Velt is binary (listed / not), no
   field/greenhouse/storage split, so all three strictness levels return the
   same result until a graded source (VLAM) is layered in. This is honest, not a
   bug — see `docs/velt.md` — but the UI dial will do nothing on day one.
4. **Season scoring isn't wired to a month yet.** `season_score` exists and is
   tested, but nothing yet answers "give me July's in-season mains." That's the
   next build and the thing that makes the tool actually seasonal.
5. **No `cuisine` column.** Fine for v1 (all Belgian), required before the v2
   crawl or the weekly menu will mix a stoofpotje and a Sichuan stir-fry blindly.
6. **Quantity parsing is 73%** and unit-normalisation is partial (containers like
   "bussel"/"bol"/"potje" stay unnormalised). Grocery-list aggregation will need
   a fuzzy merge and will surface more gaps.
7. **`schema.recipes.course`** column exists but is unused; course is currently
   computed on the fly. Decide whether to persist derived axes or keep computing.

## 7. Open decisions (owner)

- **Course/derived axes:** persist `staple_base`/`course`/`cuisine` as columns
  (needs a small migration since `CREATE TABLE IF NOT EXISTS` won't alter), or
  keep computing at read time? (Currently computed.)
- **Planner shape:** balance courses? — decided **mains only**. Household — decided
  **scale to 2 adults + 2 kids** (kid portion fraction still to pick).
- **Lexicon judgment calls** (`docs/vegan_sources.md`): map bare `kool`
  (ambiguous) with a low-confidence default? map `daikon`→`rammenas`
  (approximation)? Currently unmapped, deliberately.

## 8. Roadmap

1. **Season filter by month** (small) — subset of mains whose hero is in season
   for month M at strictness S; verify against `docs/velt.md` cases (asparagus
   May–Jun, witloof Oct–Apr). Doubles as the yardstick for whether v2 is needed.
2. **Planner** — `plan_week(month, diet, strictness, servings)` → 7 mains, one
   per staple base for variety, hero in season, diet respected, no repeats.
3. **Grocery list** — aggregate + scale to household + group by aisle.
4. **Single-file browser app** — export facts-only JSON, run planner + grocery
   client-side; month picker, diet/strictness toggles, per-recipe reroll.
5. **v2 (later): incidentally-vegan winter crawl** — `docs/vegan_sources.md`.
   Prereqs first: `cuisine` column, transliterated-Hindi/romanised-Korean+
   Japanese alias pass, starter three (vegrecipesofindia, redhousespice,
   miakouppa), then re-measure per-month coverage.

## 9. How to run

```bat
:: Windows, behind Zscaler
py -m venv .venv & .venv\Scripts\activate
pip install -r requirements.txt        :: truststore makes requests trust the OS/Zscaler CA
set PYTHONUTF8=1
setx COOKBOOK_CONTACT "you@example.be"  :: contact via env, not tracked config.py

py load_velt.py                         :: offline: load the calendar
python -m pytest                        :: 239 tests, offline
py crawl.py --list-only                 :: discover sizes + ETA, no fetch
py crawl.py --source 15gram --limit 500 :: polite, resumable crawl
py report.py                            :: corpus coverage
py staples.py & py courses.py           :: classifier dumps to eyeball
```

`cookbook.db`, `dumps/`, `logs/` are gitignored — a `git pull` never touches
crawl data. Network is used only by `crawl.py` and `spike.py` (both throttled).
