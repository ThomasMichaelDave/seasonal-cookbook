# Traditional vegan sources — survey

Scope: cuisines that are **incidentally vegan** — dishes that were always
plant-based — rather than modern veganised versions built on seitan, textured
protein, vegan cheese and meat analogues.

The distinction is not snobbery, it's mechanical. Substitute-driven recipes
have few whole vegetables in them, so they carry almost no seasonal signal and
are close to useless to a seasonal planner. `mujaddara` scores as
season-neutral because lentils and rice have no season; `vegan shawarma` with
seitan scores nothing at all.

---

## The finding that matters most

Almost every naturally-vegan Mediterranean and South Asian dish peaks **June
to October** on the Belgian calendar. Tested against the loaded Velt data:

| dish | matched produce | months ≥0.75 |
|---|---|---|
| Briam | courgette, aubergine, aardappel, tomaat | Jul–Oct |
| Baingan bharta | aubergine, tomaat | Jul–Oct |
| Gigantes plaki | tomaat, wortel, bleekselderij | Jul–Oct |
| Fasolakia | prinsessenboon, tomaat, aardappel | Jun–Oct |
| Koshari | tomaat | Jun–Oct |
| Ful medames | tuinboon, tomaat | Jun–Jul |
| Mujaddara | — (lentils/rice/onion only) | none — neutral |

That's a **summer-heavy corpus bolted onto a country whose vegetable calendar
is dominated by winter brassicas and roots**. Adding 5,000 Levantine and South
Indian recipes would make July brilliant and February no better than it is now.

So the useful question isn't "where are the vegan recipes" — it's **which
traditions cook witloof, spruiten, boerenkool, pastinaak, knolselderij,
schorseneer, rammenas, koolraap and rodekool.**

### Traditions that do

| tradition | Belgian winter crops it actually uses |
|---|---|
| **Punjabi / North Indian** | mustard greens ≈ boerenkool (*sarson ka saag*), cauliflower (*gobi*), turnip (*shalgam*), radish (*mooli*), carrot, peas |
| **Korean temple / home** | napa cabbage, winter radish, root *namul*, doenjang stews |
| **Northern Chinese** | cabbage, daikon, potato — a genuinely winter-oriented regional cuisine |
| **Japanese *nimono* / *kenchinjiru*** | daikon, carrot, burdock, taro, lotus root — root-vegetable simmering is the core technique |
| **Turkish / Balkan** | cabbage rolls (*lahana sarma*), leek dishes (*zeytinyağlı pırasa*), turnip |
| **Orthodox Lenten (Greek/Slavic)** | cabbage, beans, root vegetables — see caveat below |

Verified against the pipeline:

| dish | matched | months ≥0.75 |
|---|---|---|
| Nimono (wortel + pastinaak) | wortel, pastinaak | Jan–Mar, Oct–Dec |
| Muguk (radish soup) | rammenas, prei | Jan–Mar, Sep–Dec |
| Spruitjes met sesam | spruiten | Jan–Mar, Oct–Dec |
| Sarson ka saag | boerenkool, spinazie | Mar, Oct |
| Lahana sarma | wittekool | Jan–Mar, Jul–Dec |

These invert cleanly into winter. **This is the half of the corpus worth
prioritising** — the Mediterranean summer material is already well covered by
the Belgian sources.

---

## Sources, by scrapability

### Already have native `recipe-scrapers` support

Zero extra parser work; add the domain and go.

| domain | tradition | notes |
|---|---|---|
| `vegrecipesofindia.com` | Indian, all-vegetarian | ~1,200+ recipes (app listing); "rooted in traditional Indian vegetarian home cooking"; regional Punjabi/South Indian breadth. **Best single pick.** |
| `indianhealthyrecipes.com` | Indian (Swasthi) | very large, traditional, strong South Indian |
| `archanaskitchen.com` | Indian, regional | broad regional coverage incl. lesser-known states |
| `ministryofcurry.com` | Indian | smaller, modern-leaning |
| `thewoksoflife.com` | Chinese, family | traditional home cooking, strong vegetable section |
| `redhousespice.com` | Chinese, Northern | **the winter-vegetable one** — cabbage, daikon, potato |
| `omnivorescookbook.com` | Chinese | traditional, good vegetable coverage |
| `mykoreankitchen.com`, `maangchi.com` | Korean | traditional; *namul* and stew sections are the relevant part |
| `justonecookbook.com` | Japanese | has *nimono* and some shojin material |
| `themediterraneandish.com` | Mediterranean/Levantine | large, whole-food oriented |
| `akispetretzikis.com`, `argiro.gr` | Greek (Greek-language) | both have substantial *nistisima* sections |
| `feelgoodfoodie.net` | Lebanese | family recipes, whole-food |
| `cookpad.com` | Japanese, user-generated | enormous; quality varies wildly |
| `books.ottolenghi.co.uk` | — | small, vegetable-forward |

### No native scraper — wild_mode / JSON-LD route

Most are WordPress with a recipe plugin, so they very likely emit JSON-LD and
`wild_mode` will parse them. Verify per site before committing to a crawl.

| domain | tradition |
|---|---|
| `miakouppa.com` | Greek, **large explicit *nistisima* corpus** with Lenten meal plans |
| `kopiaste.org` | Greek/Cypriot, long-running, explicit Lenten tagging |
| `thegreekvegan.com` | Greek, vegan-only |
| `mygreekdish.com`, `dimitrasdishes.com`, `olivetomato.com` | Greek |
| `hebbarskitchen.com`, `swasthisrecipes.com`, `cookwithmanali.com` | Indian |
| `manjulaskitchen.com`, `padhuskitchen.com`, `sharmispassions.com` | Indian, traditional/regional |
| `tarladalal.com` | Indian, very large archive |
| `holycowvegan.net`, `myheartbeets.com` | Indian, vegan-leaning |
| `chinasichuanfood.com` | Sichuan, traditional |
| `plantbasedfolk.com`, `hanadykitchen.com`, `zenandzaatar.com` | Levantine |
| `simplyleb.com`, `amiraspantry.com`, `everylittlecrumb.com` | Levantine/Egyptian |
| `palestineinadish.com`, `urbanfarmandkitchen.com` | Palestinian |

### Deprioritise for this project

Not bad sites — just the substitute-driven end, which contributes little
seasonal signal: `minimalistbaker.com`, `noracooks.com`, `elavegan.com`,
`lovingitvegan.com`, `rainbowplantlife.com`, `simple-veganista.com`,
`theplantbasedschool.com`, `bestofvegan.com`.

A useful test when in doubt: does the site's Levantine section list *ful
medames*, *mujaddara* and *mutabbal* — or *vegan shawarma* and *vegan kofta*?

---

## Traps specific to these cuisines

**"Vegetarian" in Indian sources is not vegan.** Ghee, paneer, dahi/curd and
cream are everywhere, and *vegrecipesofindia* is explicitly a vegetarian —
not vegan — site. The existing classifier handles this correctly (ghee and
paneer are in `DAIRY`), which is exactly why the `vegan` vs `vegetarian`
distinction earns its keep here.

**Nistisima ≠ vegan.** Greek Orthodox fasting permits shellfish and molluscs,
and Mia Kouppa's own Lenten archive says so plainly — the recipes exclude
meat, dairy and eggs "although you will find some seafood and shellfish which
is appropriate for lent". Strict fasting days also exclude olive oil. **Never
treat a `nistisima` or `lenten` tag as a vegan filter** — run the classifier.
Honey is likewise fasting-permitted in some traditions but is not vegan; it's
already in the lexicon.

**Kimchi and curry paste were right to flag.** Commercial and most regional
kimchi contains fish sauce or shrimp paste; Thai and Malaysian curry pastes
usually contain shrimp paste. Both are already in `AMBIGUOUS`, which the
eastern corpus will exercise hard. Temple kimchi is genuinely vegan — so the
`uncertain` verdict is right: it depends on the maker, not the word.

**Buddhist temple cuisine excludes the five pungent vegetables** (*osinchae* /
*oshinchae*): garlic, onion, scallion, chives, and leek or asafoetida
depending on the tradition. Both Korean *sachal eumsik* and Japanese *shojin
ryori* observe this.

This is a happy accident for the pipeline: those are exactly `AROMATICS` plus
`prei`. Temple recipes therefore contain **almost nothing but scoreable
seasonal produce**, giving unusually clean signal. They're also explicitly
seasonal by doctrine. The catch is supply: the English-language *recipe* web
for shojin ryori is thin — mostly restaurant guides and travel writing, not
scrapable recipe corpora. Korean temple food has more, via the mainstream
Korean sites' *namul* and *jjigae* sections.

**Ingredient vocabulary is the real integration cost**, not the scraping.
Asafoetida, curry leaves, tamarind, gochugaru, doenjang, pomegranate molasses,
dried limes, perilla, kombu — none have a Belgian season and none need one.
They just need to be *recognised* well enough not to pollute the grocery list.

---

## Lexicon gaps this survey exposed

Confirmed by running the dishes through the pipeline:

**Fixed:** Dutch vowel-shortening plurals. `raap → rapen`,
`bloemkool → bloemkolen`, `pastinaak → pastinaken`, `koolraap → koolrapen`,
`aardpeer → aardperen` and five more all failed to match, because
suffix-appending produces "raapen", which is not a word. Eight of the ten are
Velt crops, so this was silently breaking the **existing Belgian** corpus too,
not just this one. Rule added, ten regression tests.

**Still open, deliberately left for a decision:**

- **`kool` on its own** → no match. Common in recipes ("500 g kool"), but
  ambiguous between white, savoy, pointed and red. Guessing `wittekool` would
  be wrong maybe a third of the time. Probably worth a low-confidence default,
  but that's a judgment call.
- **`daikon` / `mooli` / `rettich` → `rammenas`** — RESOLVED. Closest Velt crop
  is `rammenas` (black winter radish): same season, same role, different
  vegetable. Done as an explicit, owner-reversible **approximation** (kept in a
  separate `APPROXIMATE` block, not `TRANSLITERATED`, so the distinction stays
  visible) because it is what gives Japanese/Korean/Northern-Chinese daikon
  dishes a winter signal instead of `unknown`. Reverse by deleting the block or
  retargeting to `radijs`.
- **No Velt equivalent at all:** gobo/burdock, taro, lotus root, bok choy
  beyond `paksoi`, mustard greens, bitter gourd, drumstick. Some are grown in
  Belgium; Velt lists none of them. These will always score as *unknown*
  (skipped), which is the correct behaviour, but means those dishes rely on
  their other vegetables for a seasonal signal.

---

## Recommendation

1. **Don't add a second language yet.** These sources are overwhelmingly
   English. That's cheaper than French, but the produce lexicon is currently
   Dutch-keyed with English aliases — fine for `carrot`/`cauliflower`, useless
   for `mooli`, `gobi`, `baingan`, `bhindi`, `karela`. Budget for a
   transliterated-Hindi and romanised-Korean/Japanese alias pass **before**
   crawling, or match rates will be poor and you won't know why.

2. **Start with three, chosen for winter coverage, not volume:**
   `vegrecipesofindia.com` (native scraper, huge, traditional, and Punjabi
   winter-vegetable coverage), `redhousespice.com` (native, Northern Chinese,
   cabbage-and-daikon), `miakouppa.com` (nistisima corpus, wild_mode).

3. **Add a `cuisine` column to `recipes`** before this crawl, not after.
   Otherwise a Belgian stoofpotje and a Sichuan stir-fry are indistinguishable
   at planning time, and the weekly menu will read like a random walk.

4. **Then measure the thing that matters:** for each month, how many recipes
   have a seasonal hero in season? If February is still thin after adding
   these, the answer is more Punjabi/Korean/Northern Chinese sources — not
   more Mediterranean ones.
