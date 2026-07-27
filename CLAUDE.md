# CLAUDE.md

Context for Claude Code sessions on this repo. Read this first.

## What this is

A season-based cookbook for Belgium. Scrape Belgian recipe sites, map their
ingredients onto the Belgian seasonal produce calendar, then generate a week
of menus and a grocery list from it.

Personal, non-commercial project. Owner is in Belgium, develops on **Windows**.

## Current state

Phase 0 spike is complete and tested. First live probe has run against all
three sources; wider crawler now exists.

| Component | State |
|---|---|
| SQLite schema (`db.py`) | done |
| Polite fetcher + HTML cache (`fetch.py`) | done; live-tested. Uses OS trust store (Zscaler/corporate TLS) + gzip sitemaps |
| Parser routes (`parse.py`) | done; live-confirmed — 15gram/DK native `recipe_scrapers`, Delhaize `wild` |
| Diet classification (`classify.py`) | done, 39 cases passing (9 added from the first crawl) |
| Seasonal lexicon  (77 items) | done, seeded |
| Hero detection + season scoring | done, tested |
| **Velt calendar** | **loaded — 421 rows, 70 crops, all 12 months** |
| Recipe persistence (`persist.py`) | done — idempotent upsert, shared by spike + crawl |
| Wider crawl (`crawl.py`) | done — polite, resumable, `--list-only`/`--limit`/`--all` |
| Menu planner / grocery list | not started |
| UI | not started — decided: single-file browser app |

Nothing is blocked. Current step: run `crawl.py` wider, then build the planner.

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
python -m pytest              # full suite (152 tests), no network
python transcribe_velt.py     # regenerate the Velt CSV from the transcription
python load_velt.py --report  # reconciliation report, no writes
python load_velt.py           # load Velt into the seasonality table
python spike.py --offline     # lexicon seeding + self-checks, no network
python spike.py               # the fixed 20/5/5 probe -> dumps/ingredients.txt

# Wider crawl (task 4). Reuses fetch.py politeness UNCHANGED; resumable via the
# pages cache; idempotent via persist.store_recipe. Also touches the network.
python crawl.py --list-only               # discover, report sizes + ETA, no fetch
python crawl.py --source 15gram --limit 500
python crawl.py --all --limit 300         # 300 per source
python crawl.py --source delhaize --yes   # whole source (--yes clears the size gate)
```

`spike.py` (without `--offline`) and `crawl.py` are THE ONLY commands that touch
the network. Both are rate-limited to ~1 req/sec per domain. Both tee their full
output — including the final summary + diet breakdown — to a timestamped file in
`logs/` (gitignored); the path is printed at the start and end of every run.

Windows setup:

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set PYTHONUTF8=1
setx COOKBOOK_CONTACT "you@example.be"   :: contact addr via env, not config.py
```

`COOKBOOK_CONTACT` keeps your email out of the tracked `config.py`, so it never
collides on `git pull`. `cookbook.db`, `dumps/` and `logs/` are gitignored, so a
pull never touches your crawl data.

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

**v2 — incidentally-vegan, winter-coverage crawl (survey: `docs/vegan_sources.md`).**
The point is NOT more vegan volume — it's traditions that cook Belgian *winter*
crops (witloof, spruiten, boerenkool, pastinaak, knolselderij, koolraap,
rammenas): Punjabi/North Indian, Korean temple/home, Northern Chinese, Japanese
nimono, Turkish/Balkan. Mediterranean/Levantine material peaks Jun–Oct and is
already covered by the Belgian sources. Prerequisites, in order (from the
survey — do NOT crawl before these):
1. Add a `cuisine` column to `recipes` (a Belgian stoofpotje and a Sichuan
   stir-fry must be distinguishable at plan time).
2. A transliterated-Hindi / romanised-Korean+Japanese produce **alias pass**
   (mooli, gobi, baingan, bhindi, karela, daikon…) — else match rates are poor.
3. Start with THREE, chosen for winter coverage: `vegrecipesofindia.com`
   (native scraper), `redhousespice.com` (native, Northern Chinese),
   `miakouppa.com` (wild_mode, Greek nistisima). English-language, so no new
   language layer — but see the alias pass above.
4. Re-measure the per-month in-season-hero count; if February is still thin,
   the answer is more Punjabi/Korean/N-Chinese, not more Mediterranean.

Traps (all already handled by the classifier, per the survey): Indian
"vegetarian" ≠ vegan (ghee/paneer/dahi → `vegetarian`); nistisima/Lenten tags
permit shellfish and are NOT a vegan filter — run the classifier; kimchi &
curry paste stay `uncertain` (maker-dependent fish sauce/shrimp paste).

## Next tasks, in order

Done in the first crawl round: ✅ ran the probe and tuned `parse_ingredient()`
against real strings; ✅ confirmed parser routes (Delhaize = `wild`); ✅ fixed
the diet misses (steak/entrecote/sardienen/halloumi, `gehakte`), the `kl`/
deciliter units, Delhaize trailing quantities, and the spike re-run FK crash.
`url_patterns` verified against live sitemaps (no tightening needed yet).

1. **Crawl wider** with `crawl.py` (start `--list-only` to see sizes + ETA,
   then `--source 15gram --limit …`, working up). Watch the diet breakdown.
2. **Answer the first real question:** how many scraped recipes have a
   seasonal hero at all? That number decides whether the lexicon needs to grow.
3. **Menu planner** — decided shape: a **single-file browser app**; **main
   dishes only**, each centred on a *staple base* (potato / rice+grain / pasta
   / bread family); servings **scale to a household of 2 adults + 2 kids**.
   Needs a small **staple-base classifier** (potato/rice/pasta/bread) — a new
   axis alongside the seasonal hero — which does not exist yet.
4. **Grocery list:** aggregate ingredients across the week, group by aisle,
   scaled to household size.

Optional, once there's real recipe data: layer VLAM's low/normal/high gradient
in as `field`/`greenhouse`/`storage` rows to make the strictness dial live.

Deferred lexicon polish (Tier 3, low priority): `champignonmix` and
`stoofselder` don't match a seasonal canonical; `edamame` wrongly matches
`prinsessenboon`. Seasonal-signal only, not diet.

Open lexicon decisions raised by `docs/vegan_sources.md` (judgment calls, left
for the owner):
- **`kool` on its own** — common ("500 g kool") but ambiguous (white / savoy /
  pointed / red). A low-confidence default to `wittekool` would be wrong ~⅓ of
  the time. Not mapped.
- **`daikon` / `rettich`** — closest Velt crop is `rammenas` (same season, same
  role, different vegetable). Mapping daikon→rammenas is an approximation, not a
  fact, so not done silently. Needed for Japanese/Korean/N-Chinese.
- **No Velt equivalent:** gobo, taro, lotus root, mustard greens, bitter gourd,
  drumstick — will always score `unknown` (skipped), which is correct.

Fixed from that survey: Dutch vowel-shortening plurals (`raap`→`rapen`, not
`raapen`; `bloemkool`→`bloemkolen`; `pastinaak`→`pastinaken`; +7 more). Eight
are Velt crops, so this was silently costing matches on the *Belgian* corpus.
See `tests/test_plurals.py`.

## Open questions for the owner

- Final tool form: local Python + web UI, single-file browser app, or CLI?
- Does the planner need to balance courses (soup / main / dessert)?
- Household size — fixed servings, or scale per recipe?
