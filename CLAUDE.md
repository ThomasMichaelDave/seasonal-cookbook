# CLAUDE.md

Context for Claude Code sessions on this repo. Read this first.

## What this is

A season-based cookbook for Belgium. Scrape Belgian recipe sites, map their
ingredients onto the Belgian seasonal produce calendar, then generate a week
of menus and a grocery list from it.

Personal, non-commercial project. Owner is in Belgium, develops on **Windows**.

## Current state

Phase 0 spike is complete and tested. Nothing has been crawled at scale yet.

| Component | State |
|---|---|
| SQLite schema (`db.py`) | done |
| Polite fetcher + HTML cache (`fetch.py`) | done, untested against live sites |
| Parser routes (`parse.py`) | done, tested against fixtures only |
| Diet classification (`classify.py`) | done, 26 cases passing |
| Seasonal lexicon  (62 items) | done, seeded |
| Hero detection + season scoring | done, tested |
| **Velt calendar** | **loaded — 421 rows, 70 crops, all 12 months** |
| Menu planner / grocery list | not started |
| UI | not started, form undecided |

Nothing is blocked. The next step is running the spike against live sites.

## The Velt data — read `docs/velt.md` before touching seasonality

Short version, because it contradicts what the research survey said:

- The printed calendar is **binary** (listed / not listed) with **no
  cultivation split and no supply gradient**. The earlier claim that Velt
  distinguishes open field from unheated greenhouse was wrong.
- Rows load as `cultivation='velt'`, accepted by all three strictness levels,
  so **the strictness dial is currently inert**. Don't "fix" this by retagging
  Velt rows as `field` — add real field/greenhouse/storage rows from another
  source instead.
- **Lexicon keys track Velt spelling.** Nine were renamed; old spellings are
  aliases. `witloof` is the one sanctioned deviation from Velt's `witlof`, and
  a test enforces that it stays the only one.
- Seven crops are listed all 12 months (`aardappel`, `groene selderij`,
  `paddenstoelen`, `prei`, `rode biet`, `ui`, `wortel`). They carry no
  discriminating signal but are deliberately still scored.

## Commands

```bash
python -m pytest              # full suite (129 tests), no network
python transcribe_velt.py     # regenerate the Velt CSV from the transcription
python load_velt.py --report  # reconciliation report, no writes
python load_velt.py           # load Velt into the seasonality table
python spike.py --offline     # lexicon seeding + self-checks, no network
python spike.py               # THE ONLY COMMAND THAT TOUCHES THE NETWORK
```

Windows setup:

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set PYTHONUTF8=1
```

## Rules for working in this repo

**Never crawl during development.** `spike.py` without `--offline` is the only
thing that hits the network, and it is rate-limited to ~1 req/sec per domain.
Develop parsers against `tests/fixtures/` and against `pages.html` already in
the local cache. If you need new fixtures, ask — don't fetch them.

**Never remove the politeness machinery** in `fetch.py`: robots.txt checks,
per-domain throttle, backoff, retry cap. It is not optional and not slow by
accident.

**Store facts, not prose.** Ingredients, quantities, timings, servings, source
URL. Do NOT persist recipe instruction text, headnotes, or images — those are
the copyrightable parts. `recipes` has no instructions column on purpose.

**Don't commit `cookbook.db`.** It's gitignored. It contains cached third-party
HTML and is regenerable.

**Sitemap URL patterns in `config.py` are guesses.** `spike.py` step 3 prints
the real path prefixes it finds. Tighten from that output; don't assume.

## Design decisions worth not re-litigating

See `docs/decisions.md` for the full log, `docs/velt.md` for the seasonal
data. The short version:

1. **Fetch and parse are permanently separate.** Raw HTML is cached in
   `pages`; parsing always reads from cache. The parser will be rewritten many
   times and must never re-hit a server to do it.

2. **Only ~60 produce items get canonical IDs.** Salt has no season and needs
   no identity. Everything else is fuzzy-grouped at grocery-list time.

3. **Dutch compounds break matching in both directions.** `SAFE_COMPOUNDS`
   strips fakes (`vleestomaat` = tomato, `eierzwam` = chanterelle) and runs
   *first*; prefix matching then catches hides (`kippenbouten` → kip,
   `roomijs` → room). The order is load-bearing. Adding a prefix without
   checking the safe-list is how you get "beefsteak tomato is not vegan".

4. **Heroes decide seasonality, not ingredient presence.** Aromatics
   (ui/sjalot/knoflook) are never heroes. Title match wins; then bulk; then
   largest produce item. Ingredient *position* is deliberately unused — sites
   order by use, not importance, and it promoted every onion.

5. **`uncertain` outranks `vegetarian`** in diet ranking. An unidentified
   bouillon cube is a worse failure than a known knob of butter.

6. **Season scores are derived, never authoritative.** Delete and recompute
   `recipe_season_score` whenever the lexicon or Velt data changes.

7. **Recipes with no seasonal produce are season-NEUTRAL, not out of season.**
   The planner must not filter them out; pasta carbonara is a valid Tuesday.

## Sources

v1 is Belgian only.

| Source | Lang | Parser route | Notes |
|---|---|---|---|
| 15gram.be | NL | native `FifteenGram` | ~6,000 recipes, server-rendered, easiest |
| dagelijksekost.vrt.be | NL | native `DagelijkseKost` | ~2,700, authentic Flemish, JS listing pages — use sitemap |
| delhaize.be | NL | wild → JSON-LD → `__NEXT_DATA__` | no native scraper; robots.txt is permissive but blocks `*/search/*` |

Deferred to v2: Marmiton (FR, native scraper exists), BBC Good Food (EN,
native scraper exists). Adding them means a second-language lexicon, which is
why they're deferred.

## Next tasks, in order

1. Run `python spike.py` once, read `dumps/ingredients.txt`, tune
   `parse_ingredient()` against what real strings actually look like
2. Tighten `config.SOURCES[*]['url_patterns']` from the printed prefixes
3. Confirm which parser route catches Delhaize; write a dedicated one if all
   four routes miss
4. Full crawl of 15gram, then Dagelijkse Kost, then Delhaize
5. **Answer the first real question:** how many scraped recipes have a
   seasonal hero at all? That number decides whether the planner has enough
   to work with, or whether the lexicon needs to grow.
6. Menu planner: pick N recipes for a week given month + diet + strictness,
   with variety constraints
7. Grocery list: aggregate ingredients across the week, group by aisle

Optional, once there's real recipe data: layer VLAM's low/normal/high gradient
in as `field`/`greenhouse`/`storage` rows to make the strictness dial live.

## Open questions for the owner

- Final tool form: local Python + web UI, single-file browser app, or CLI?
- Does the planner need to balance courses (soup / main / dessert)?
- Household size — fixed servings, or scale per recipe?
