# The Velt calendar

**Status: loaded.** 421 rows, 70 crops, 12 months. Regenerate with
`python transcribe_velt.py`, load with `python load_velt.py`.

Source: Velt vzw, *Groente- en fruitkalender*, 2019 edition
(V.U. Leen Laenens). <https://velt.nu/seizoenskalender>

---

## Correction to the earlier research

The source survey (`docs/research.md`, since amended) claimed Velt was **the
only Belgian source distinguishing open field from unheated greenhouse**, and
that claim drove the whole `field` / `greenhouse` / `storage` strictness
design.

**The public calendar does not carry that split.** It is a flat monthly list:
a crop is either printed under a month or it isn't. No cultivation column, no
supply gradient. The distinction may exist in Velt's members' magazine or in
their sowing/planting calendars, but not in this artifact.

Everything below follows from that.

---

## What the data supports

| | |
|---|---|
| Granularity | binary — listed or not |
| Availability levels | one (`3`); levels `1` and `2` unused |
| Cultivation | **unspecified** |
| Months | all 12 populated |
| Fruit/vegetable split | yes — Velt bolds fruit in the original |

### The `velt` cultivation tier

Rows load as `cultivation='velt'`, not `'field'`.

Tagging them `field` would have been false: potatoes in February and apples in
March are storage crops, and Velt lists both. Rather than invent a
distinction the source doesn't make, the tier is named after its provenance
and accepted by all three strictness levels:

```python
STRICTNESS_CULTIVATION = {
    "field":      {"field", "velt"},
    "greenhouse": {"field", "greenhouse", "velt"},
    "storage":    {"field", "greenhouse", "storage", "velt"},
}
```

**Consequence: the strictness dial is currently inert.** With Velt-only data
all three settings return identical results. It starts discriminating when a
source with a real cultivation split is layered in — VLAM's low/normal/high
gradient, or a hand-built storage overlay for the obvious keepers. Wire that
in as *additional* rows tagged `field`/`greenhouse`/`storage`; don't retag the
Velt rows.

---

## Reconciliation

70/70 crops mapped. Lexicon keys were renamed to Velt's spelling:

| was | now |
|---|---|
| `bleekselder` | `bleekselderij` |
| `knolselder` | `knolselderij` |
| `sla` | `kropsla` |
| `sperzieboon` | `prinsessenboon` |
| `snijbiet` | `warmoes` |
| `erwt` | `doperwt` |
| `maïs` | `mais` |
| `champignon` | `paddenstoelen` |
| `spruitjes` | `spruiten` |

Old spellings survive as aliases, so recipe matching is unaffected.

**One sanctioned deviation:** Velt writes `witlof` (Netherlands spelling); the
key stays **`witloof`** (Belgian spelling), because Belgian recipe sites write
`witloof` and this is a Belgian project. `witlof` is an alias, so the Velt row
lands correctly. `test_lexicon_keys_match_velt_spelling_except_one` pins this
as the only permitted exception — if a second one appears, that test fails.

### One split was required

`spitskool` was previously an alias of `wittekool`. Velt lists them as
**separate crops with different ranges** (spitskool May–Oct, wittekool
Jul–Feb), so collapsing them would have corrupted both. Now separate
canonicals, with a test asserting their month sets differ.

### 15 crops were missing from the lexicon

Added: `aardpeer`, `chinese kool`, `groene selderij`, `paksoi`, `raapsteel`,
`roodlof`, `snijboon`, `winterpostelein`, `spitskool` (split), plus fruit
`abrikoos`, `perzik`, `nectarine`, `vijg`, `meloen`, `kiwibes`.

### 7 lexicon entries have no Velt row

`eierzwam`, `knoflook`, `sjalot`, `kruisbes`, `kweepeer`, `postelein`,
`rucola` — tracked in `NOT_IN_VELT`, with a test keeping the constant honest.

This forced a real fix. `season_score` previously scored a canonical with no
seasonality rows as **zero**, i.e. never in season — so every chanterelle
recipe was permanently penalised. Absence of data is not evidence of absence;
unknown produce is now **skipped**, exactly like non-produce. See
`test_produce_with_no_data_is_skipped_not_penalised`.

---

## Seven crops are listed all twelve months

```
aardappel, groene selderij, paddenstoelen, prei, rode biet, ui, wortel
```

These carry **no discriminating seasonal signal** under binary data. `ui` is
already excluded as an aromatic. The other six still count, deliberately — a
leek tart is legitimately a leek dish, and suppressing them would make winter
vegetable cooking look unseasonal.

Worth revisiting if the planner's output feels indiscriminate: these six are
where a VLAM gradient would add the most, since VLAM distinguishes *peak leek*
from *leek is technically available*.

`test_year_round_crops_are_what_we_think` pins the set, so a data refresh that
changes it is caught.

---

## Observed behaviour

Scores against the real calendar (greenhouse strictness):

| recipe | heroes | peak months |
|---|---|---|
| Stoofpotje van witloof en prei | prei, witloof | Oct–Apr (1.00 in Oct) |
| Zomerse ratatouille | courgette, paprika, tomaat | Jul–Oct (1.00) |
| Aspergesoep | asperge | May–Jun only |
| Pompoensoep | pompoen | Aug–Apr |
| Aardbeientaart | aardbei | Apr–Aug |
| Pasta pesto | — | neutral, all months 0.00, n=0 |

Asparagus in May–June only, and pesto pasta as season-neutral rather than
out-of-season, are the two behaviours most worth keeping intact.

---

## Refreshing to a newer edition

1. Update the month blocks in `transcribe_velt.py`, bump `EDITION`
2. `python transcribe_velt.py` — reports crop count and the year-round set
3. `python -m pytest tests/test_velt.py` — will fail loudly on any newly
   unmapped crop, new collision, or changed year-round set
4. Fix the lexicon (rename keys to match Velt, add missing crops)
5. `python load_velt.py` — idempotent; clears and reloads the `velt` tier only
6. Delete and recompute `recipe_season_score`; it's a derived cache

Update `EXPECTED_CROPS` / `EXPECTED_ROWS` in `tests/test_velt.py` to the new
figures once you've confirmed them.

---

## A note on the CSV

`data/velt/velt_seizoenskalender_2019.csv` is committed; the source PDF is
gitignored. The CSV is factual data — which crops are harvestable in Belgium
in which month — and month-by-month availability is not expressive content.
The EU *sui generis* database right can still attach to a compilation's
selection and arrangement, so for a public repo it would be worth linking to
Velt rather than redistributing the table. For a private, personal repo this
is fine, and `transcribe_velt.py` makes the provenance explicit either way.
