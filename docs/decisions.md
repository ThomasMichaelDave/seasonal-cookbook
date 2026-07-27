# Decisions

Why things are the way they are. Read before changing any of it.

---

## 1. Fetch and parse are permanently separate

Raw HTML goes into `pages`; parsing always reads from there.

The ingredient parser will be rewritten many times as real-world strings turn
up. Re-crawling three sites for each iteration is slow, rude, and gets you
rate-limited. It also makes the pipeline resumable when the connection drops
at recipe 4,200.

`pages.content_hash` means a later re-crawl re-parses only what changed.

---

## 2. Only ~60 items get canonical IDs

Salt has no season. Flour has no season. Olive oil has no season.

Precision is only needed for produce that appears in the Velt calendar,
because that's the only thing the seasonal join needs. Everything else needs
fuzzy grouping at grocery-list time and nothing more. Trying to build a
complete ingredient ontology is how this project dies.

`canonical_id` is nullable and mostly NULL. That's the design, not a gap.

---

## 3. Dutch compounds break matching in both directions

This is the single most error-prone part of the codebase.

**Fakes** — the compound contains an animal word but isn't animal:

| word | actually |
|---|---|
| `vleestomaat` | beefsteak tomato |
| `eierzwam` | chanterelle mushroom |
| `botersla` | butterhead lettuce |
| `boterbonen` | butter beans |
| `pindakaas` | peanut butter |
| `kokosmelk` | coconut milk |
| `wilde rijst` | wild rice |

**Hides** — the animal word is only a prefix, so exact-token matching misses it:

| word | contains |
|---|---|
| `kippenbouten` | kip |
| `roomijs` | room |
| `vissticks` | vis |
| `runderrookvlees` | rund |
| `melkchocolade` | melk |

So: `SAFE_COMPOUNDS` is checked first and **stripped from the text**, and only
then does prefix matching run. The order is load-bearing. Adding a prefix
without a matching safe-list entry is how "beefsteak tomato" becomes
not-vegan.

Every trap found in the wild gets a case in `tests/diet_cases.py`. That list
is the real asset here, not the code.

---

## 4. Heroes decide seasonality, not ingredient presence

First version marked garlic and onion as heroes and every recipe came back
"in season" year-round. The fix, in strict order:

1. **Aromatics** (`ui`, `sjalot`, `knoflook`) are never heroes and are
   excluded from scoring entirely. They're stored year-round and appear in
   most savoury cooking — they tell you nothing about season. They still get
   a `canonical_id` because they belong on the grocery list.
2. **Title match wins outright.** If the title names produce, that is the hero
   set and nothing else is. The title is the strongest statement a recipe
   makes about what it is.
3. Otherwise **bulk**: ≥250 g, ≥1 kg, ≥2 pieces.
4. Otherwise the **single largest** produce item, so any recipe with produce
   has something to score against.

**Ingredient position is deliberately unused.** Sites order ingredients by
order of use, not by importance, and using position promoted every onion.
There's a regression test for this.

Heroes carry 3× the weight of side ingredients. An out-of-season hero sets
`hero_in_season` False regardless of the numeric score — a witloof gratin in
July is not "62% in season", it's wrong.

---

## 5. `uncertain` outranks `vegetarian`

Diet ranking is `vegan < vegetarian < uncertain < omnivore`.

An unidentified bouillon cube is a worse failure than a known knob of butter:
the butter you can see and substitute, the bouillon you can't. `uncertain` is
surfaced to the user rather than silently resolved, via
`diet_allows(..., allow_uncertain=)`.

Things that land in `uncertain` on purpose: bare `bouillon`, `pesto`
(pecorino), `margarine` (whey), `kimchi` and `currypasta` (fish sauce,
shrimp paste), `parmezaan` (animal rennet — strict vegetarians exclude it).

---

## 6. Season scores are derived, never authoritative

`recipe_season_score` is a cache. Delete and recompute it whenever the
lexicon or the Velt data changes. Never treat it as input to anything else.

---

## 7. Recipes with no seasonal produce are season-NEUTRAL

`n_seasonal == 0` means the recipe has no produce with a season, not that it
is out of season. The planner must not filter these out — pasta carbonara is
a valid Tuesday in February. Only recipes with an out-of-season *hero* should
be pushed down.

---

## 7b. Unknown produce is skipped, not scored zero

Seven lexicon entries have no row in the Velt calendar (chanterelles,
gooseberries, quince, rocket, summer purslane, and the two aromatics).

`season_score` originally treated "no seasonality data" as availability zero,
which meant every chanterelle recipe was permanently out of season. Absence of
data is not evidence of absence. Produce with no rows at all is now skipped
entirely — same treatment as salt.

Produce that IS in the calendar but absent in *this* month still scores zero.
That distinction is the whole point.

---

## 7c. The `velt` cultivation tier, and why the strictness dial is inert

The printed Velt calendar has no field/greenhouse/storage split — the research
survey was wrong about that. Rows therefore load as `cultivation='velt'`
(meaning "listed by Velt, cultivation unspecified") rather than being
mislabelled `field`, and `velt` is accepted by all three strictness levels.

So the dial currently does nothing. That is the honest representation of a
binary source. It starts working when VLAM's gradient or a hand-built storage
overlay adds rows tagged with real cultivation types — as *additional* rows,
never by retagging Velt's.

Full reasoning in `docs/velt.md`.

---

## 7d. Lexicon keys track Velt spelling

Nine keys were renamed during reconciliation (`knolselder` → `knolselderij`,
`sla` → `kropsla`, `champignon` → `paddenstoelen`, and so on). Old spellings
survive as aliases, so recipe matching is unaffected.

One deviation is sanctioned: Velt writes `witlof`, the key stays `witloof`.
Belgian sites write `witloof` and this is a Belgian project.
`test_lexicon_keys_match_velt_spelling_except_one` enforces that this stays
the *only* exception.

`spitskool` had to be split out of `wittekool` — Velt lists them as separate
crops with different month ranges (May–Oct vs Jul–Feb), so the alias was
silently merging two different seasons.

---

## 8. Facts are the default; instructions are a personal-use exception

Ingredients, quantities, timings, servings and the source URL are facts; the
instruction text, headnotes and photographs are the copyrightable expression.
The facts path is unchanged and is what any *shareable* artifact contains
(`export.py --no-instructions`).

**Amended (owner decision): for this private, single-household cookbook, the
method prose IS now stored and shown**, so the family has the full recipe
offline. Guardrails that keep this on comfortable EU personal-use ground:

- Instructions live only in `recipes.instructions` in **`cookbook.db`, which is
  gitignored** — copyrighted prose is never committed to the repo.
- The generated **`cookbook.html` is gitignored too** and is for household use;
  do not publish or share it. `export.py --no-instructions` produces a
  facts-only file if you ever need a shareable one.
- Source URL and attribution stay on every recipe.

If this ever goes public or commercial, revert to facts-only and get an opinion
on database rights and photo licensing. See `docs/research.md` for the case law
(*Levola Hengelo*, EU database right) that this exception leans on.

---

## 9. Belgian sources only in v1

15gram, Dagelijkse Kost, Delhaize. All Dutch, so one lexicon.

Marmiton and BBC Good Food both have native `recipe-scrapers` support and were
deliberately deferred: adding them means French and English produce lexicons,
and the seasonal mapping is the hard part of this project, not recipe volume.
~10k Belgian recipes is already far more than 52 weeks needs.
