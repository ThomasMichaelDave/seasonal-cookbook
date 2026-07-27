# Seasonal cookbook — Phase 0 spike

Belgian sources only for v1: **15gram.be**, **Dagelijkse Kost**, **Delhaize**.
Seasonal backbone: **Velt seizoenskalender**.

## Setup (Windows)

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

set PYTHONUTF8=1

py load_velt.py    :: load the seasonal calendar (offline)
py spike.py        :: fetch + parse probe (the only networked step)
```

`PYTHONUTF8=1` is not optional. Without it Windows defaults to cp1252 and
silently mangles *crème fraîche*, *knolselder* and *maïs* — you find out
3,000 recipes later. To make it permanent: `setx PYTHONUTF8 1`.

Set `CONTACT` in `config.py` to a real address before your first crawl.

Run `py spike.py --offline` to exercise the lexicon and self-tests without
touching the network.

## What the spike does

1. Seeds 62 canonical produce items / 371 aliases from `lexicon/seasonal.py`
2. Self-tests the diet classifier (30 cases, all passing)
3. Reads each site's robots.txt and reports declared sitemaps
4. Walks the sitemaps and **reports the most common path prefixes**
5. Fetches a small sample (20 / 5 / 5) into the SQLite cache
6. Runs every parser route, reports which one won per source
7. Dumps every ingredient string to `dumps/ingredients.txt`

**Step 7 is the point.** Read that file before writing more parser code.

## Already established, so you don't have to discover it

`recipe-scrapers` 15.11.0 ships **native scrapers** for both Belgian cores:

| domain                  | scraper class   |
|-------------------------|-----------------|
| `15gram.be`             | `FifteenGram`   |
| `dagelijksekost.vrt.be` | `DagelijkseKost`|
| `marmiton.org`          | `Marmiton`      |
| `bbcgoodfood.com`       | `BBCGoodFood`   |

Delhaize has **no** native scraper — it's the only one that falls through to
`wild_mode` → JSON-LD → `__NEXT_DATA__`. That's the single real unknown left,
and the spike report tells you which route caught it.

Note the URL patterns in `config.py` are **guesses**. Step 4 prints the real
path prefixes; tighten them from that output before any full crawl.

## The two lexicon problems

Dutch compounds break naive matching in *both* directions:

**Fake positives** — `vleestomaat` is a tomato, `eierzwam` is a chanterelle,
`botersla` is lettuce, `pindakaas` is peanut butter. Handled by
`SAFE_COMPOUNDS`, checked first and stripped.

**Hidden positives** — `kippenbouten` hides *kip*, `roomijs` hides *room*,
`vissticks` hides *vis*. Handled by prefix matching, which is only safe
*because* the safe-list already ran.

Diet verdicts are `vegan | vegetarian | omnivore | uncertain`. `uncertain`
outranks `vegetarian` deliberately: an unidentified bouillon cube is a worse
failure than a known knob of butter. `diet_allows(..., allow_uncertain=False)`
is the switch your UI exposes.

## How seasonality is emphasised

A recipe is in season because of what it is **built on**, not because it
contains an onion.

- `AROMATICS` (ui, sjalot, knoflook) are never heroes
- Title match wins outright — if the title names produce, that's the hero set
- Otherwise bulk (≥250 g, ≥1 kg, ≥2 pieces)
- Otherwise the single largest produce item
- Position in the ingredient list is **not** used — sites order by use, not
  importance, and it promoted every onion

Heroes carry 3× the weight of side ingredients in `season_score`, and an
out-of-season hero drops `hero_in_season` to False regardless of the score.
Strictness (`field` / `greenhouse` / `storage`) is a user-facing dial.

Recipes with no seasonal produce score 0.0 and should be treated by the
planner as **season-neutral**, not out of season.

## Seasonal data — loaded

The Velt *Groente- en fruitkalender* (2019) is transcribed, reconciled and
loaded: **421 rows, 70 crops, all 12 months**, fruit and vegetables split.

Two things about it that shape everything downstream:

**It's binary.** A crop is listed in a month or it isn't — no supply gradient,
and **no open-field / greenhouse / storage split** (contrary to what the
earlier source survey claimed). Rows load as `cultivation='velt'` and are
accepted by every strictness level, so **the strictness dial is currently
inert**. It starts working when a source with a real cultivation split is
layered in.

**Seven crops are listed all twelve months** — `aardappel`, `groene selderij`,
`paddenstoelen`, `prei`, `rode biet`, `ui`, `wortel`. `ui` is already excluded
as an aromatic; the rest still count, deliberately.

Lexicon keys now track Velt's spelling (nine renames, old spellings kept as
aliases). `witloof` is the single sanctioned deviation from Velt's `witlof`,
and a test enforces that.

Full notes and the refresh procedure: `docs/velt.md`.

## Files

```
CLAUDE.md              context for Claude Code sessions — read first
config.py              sources, politeness, sample sizes
db.py                  SQLite schema
fetch.py               robots.txt, throttling, retries, HTML cache
parse.py               4 parser routes, best-first
classify.py            ingredient parsing, diet, hero detection, scoring
lexicon/animal.py      meat/fish/dairy/egg + compound traps
lexicon/seasonal.py    62 canonical produce items, NL/FR/EN aliases
spike.py               orchestrates the fetch/parse probe
transcribe_velt.py     Velt calendar -> CSV (auditable transcription)
load_velt.py           CSV -> seasonality table, with reconciliation report
tests/                 129 tests, no network required
docs/decisions.md      why things are the way they are
docs/research.md       source survey + legal posture
docs/velt.md           what the Velt data is, and what it isn't
data/velt/             the calendar CSV (PDF itself is gitignored)
```

## Tests

```bash
python -m pytest
```

129 tests, none of which touch the network. Parser routes are tested against
synthetic fixtures in `tests/fixtures/` — hand-written, so no third-party
content is committed to this repo.

`tests/diet_cases.py` is the real asset: every compound trap found in the wild
gets a case there, and `spike.py` imports the same list for its pre-crawl
smoke check so the two can't drift.

`tests/test_velt.py` guards the seasonal data: it fails loudly if a lexicon
edit orphans a Velt crop, if two crops collapse into one canonical, or if the
year-round set changes.
