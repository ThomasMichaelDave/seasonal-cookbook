# Research background

Findings from the source survey that led to the current source list. Kept so
the reasoning isn't lost, and so alternatives aren't re-researched from zero.

## Chosen sources (v1, Belgian only)

| Source | Lang | Catalogue | Rendering | Parser route |
|---|---|---|---|---|
| **15gram.be** | NL | ~6,000 (listing paginates to ~253 pages) | server-side, clean | native `FifteenGram` |
| **dagelijksekost.vrt.be** | NL | ~2,700 | recipe pages server-side; listing pages are Next.js | native `DagelijkseKost` |
| **delhaize.be** | NL/FR | large, Nutri-Score tagged | Next.js, server-rendered detail | none — wild → JSON-LD → `__NEXT_DATA__` |

Notes:

- 15gram emits `og:type: recipe` and is the easiest Belgian site to parse.
- Dagelijkse Kost is VRT's Jeroen Meus catalogue — the most authentic Flemish
  content, with a genuinely seasonal editorial ethos. Enumerate via sitemap or
  A–Z index; don't try to scroll the JS listing pages.
- Delhaize's robots.txt header comment reads `# Allow bots` and disallows only
  login/checkout/account and search-result paths (`*/search/*`, `*/search?*`).
  It publishes four sitemaps including NL and FR content. Crawl via sitemaps,
  never via the search endpoint.

## Deferred

| Source | Lang | Why deferred |
|---|---|---|
| Marmiton | FR | 75,000+ recipes (self-reported), native scraper exists — but needs a French produce lexicon |
| 750g | FR | 80,000+ (self-reported), native scraper exists |
| BBC Good Food | EN | clean JSON-LD, native scraper — weak on Belgian produce |
| Libelle Lekker | NL | returns HTTP 400 to automated fetches; active bot-blocking |
| njam! | NL | browsable, some features need an account |
| Lekker van bij ons (VLAM) | NL/FR | recipes organised around seasonal produce — worth revisiting |
| EVA vzw / ProVeg BE | NL/FR | 1,000+ plant-based recipes; strong fit for the vegan switch |

## Seasonal calendar

**Velt seizoenskalender** is the backbone — and one claim in the original
survey turned out to be wrong.

> ~~It is the only Belgian source that distinguishes open-field (*volle grond*)
> from unheated-greenhouse (*onverwarmde serre*) harvest, which is what makes
> the `field` / `greenhouse` / `storage` strictness dial meaningful.~~

**Corrected after obtaining the actual PDF:** the public *Groente- en
fruitkalender* carries **no cultivation split and no supply gradient**. It is
a flat monthly list — a crop is printed under a month or it isn't. The
strictness dial was designed on the strength of a distinction this source
doesn't make. See `docs/velt.md` for how that was handled.

The calendar is still the right backbone: it's Belgian, ecological in framing
(it argues explicitly against transport, heated greenhouses and refrigeration),
covers 70 crops across all 12 months, and splits fruit from vegetables. It
just carries less structure than the survey claimed.

**VLAM / Lekker van bij ons** is the cross-check: a month-by-month HTML grid
covering 55+ vegetables (including a white/green asparagus split), with
supply shown as a low/normal/high gradient encoded in CSS classes — parse the
class on each month cell, not the text. No field/greenhouse split and no
download; it has to be scraped.

Colruyt, CM and various retailers publish calendars largely derived from VLAM.
Useful for corroboration only.

## APIs and datasets considered, and why they aren't used

| Option | Verdict |
|---|---|
| **Spoonacular** | 365k+ recipes, season tags, free tier + paid ($29–$149/mo). English only, weak on Belgian dishes. Not needed for v1. |
| **Edamam** | 2M+ recipes, but the terms **prohibit scraping and caching** — only the four macro-nutrient values may be stored. Unusable as a local corpus. |
| **TheMealDB** | Free, tiny (hundreds), light on Belgian coverage. Prototyping only. |
| **Open Food Facts** | Not recipes — *products*, millions of them, ODbL, free, no key. **Genuinely useful later** for ingredient normalisation, allergens, Nutri-Score and barcode mapping in the grocery-list phase. |
| **RecipeNLG** | 2,231,142 recipes, 2.14 GB CSV, NER-tagged food entities, CC BY-NC-SA 4.0. US-centric. Useful as a reference corpus for improving the ingredient parser, not as recipe source. |
| **Recipe1M+** | ~1M recipes + 13M images, academic, registration required. |
| **Wikibooks Cookbook** | CC BY-SA — the one source whose full prose could legally be republished. Small and uneven. |

## Legal posture (EU / Belgium, personal non-commercial use)

Practical notes, not legal advice.

- **Facts aren't copyrightable.** Ingredient lists and basic procedural steps
  are factual statements. Storing them is low-risk.
- **CJEU *Levola Hengelo v Smilde*, C-310/17** (Grand Chamber, 13 Nov 2018):
  the taste of a food product cannot be a "work", because it's identified
  through subjective and variable sensory experience. A recipe-as-idea isn't
  protected; its *expression* is.
- **What is protected:** the written prose, headnotes, original photographs,
  and the creative selection/arrangement of a compilation.
- **EU *sui generis* database right** can protect substantial extraction from
  a structured database even where the individual facts are free. Relevant if
  you were to lift a whole site's catalogue wholesale.
- **Therefore:** store ingredients, quantities, timings and a link back.
  Don't store instruction prose or images. Respect robots.txt, rate-limit,
  identify yourself. That's the posture the code enforces.

If this ever goes public or commercial, this section stops being sufficient —
get an opinion on database rights and photo licensing, and drop anything
API-sourced from the local store.
