"""Animal-ingredient lexicon for the vegetarian / vegan switch.

THE CENTRAL PROBLEM, and why this file is longer than you'd expect:

Dutch compounds break naive substring matching, badly and silently.

    vleestomaat   contains "vlees"  -- it is a beefsteak TOMATO.   Vegan.
    eierzwam      contains "ei"     -- it is a CHANTERELLE.        Vegan.
    botersla      contains "boter"  -- it is BUTTERHEAD LETTUCE.   Vegan.
    boterbonen    contains "boter"  -- BUTTER BEANS.               Vegan.
    kokosmelk     contains "melk"   -- COCONUT MILK.               Vegan.
    pindakaas     contains "kaas"   -- PEANUT BUTTER.              Vegan.
    zeewier       -- seaweed. Vegan.

So: SAFE_COMPOUNDS is checked FIRST and wins. Only then do we look for
animal tokens, on whole-word boundaries, never on raw substrings.

Classification is deliberately conservative. An ingredient we don't recognise
that looks ambiguous (a bare "bouillon", "gelatine"-adjacent thickeners)
yields UNCERTAIN rather than a confident vegan label. Better to under-claim
than to serve someone a stock cube they didn't want.
"""

# ---------------------------------------------------------------------------
# Checked first. If a token is here, it is plant-based, full stop.
# ---------------------------------------------------------------------------
SAFE_COMPOUNDS = {
    # false "vlees"
    "vleestomaat", "vleestomaten", "vleesvervanger", "vleesvervangers",
    "vegetarisch", "vegetarische", "veganistisch", "veganistische", "vegan",
    # false "ei"
    "eierzwam", "eierzwammen", "eiervrij", "eiwitpoeder",
    # false "boter"
    "botersla", "boterbonen", "boterboon", "boterham", "boterhammen",
    "pindaboter", "amandelboter", "notenboter", "cacaoboter", "kokosboter",
    "sheaboter", "boterbloem",
    # false "melk" / "room" / "kaas" / "yoghurt"
    "kokosmelk", "sojamelk", "amandelmelk", "havermelk", "rijstmelk",
    "notenmelk", "cashewmelk", "speltmelk", "plantaardigemelk",
    "kokosroom", "sojaroom", "haverroom", "amandelroom", "plantaardigeroom",
    "sojayoghurt", "kokosyoghurt", "plantaardigeyoghurt",
    "pindakaas", "sojakaas", "notenkaas", "plantaardigekaas",
    "melkdistel",
    # traps for the PREFIX matching further down
    "wilde rijst", "wilderijst", "hamburgerbroodje", "hamburgerbroodjes",
    "roomboterletter", "visbloem", "zeewier", "zeezout", "zeekraal",
    "kaasplantje", "boterbloemen",
    # bouillon that is explicitly vegetable
    "groentebouillon", "groentenbouillon", "groentebouillonblokje",
    "bouillon de legumes", "bouillon de legume",
    # FR equivalents
    "beurredecacahuete", "beurredecacao", "laitdecoco", "laitdamande",
    "chanterelle", "chanterelles", "girolle", "girolles",
    "tomatecharnue", "tomatescharnues",
}

# ---------------------------------------------------------------------------
# Contains meat/fish -> omnivore (excluded from BOTH veg and vegan)
# ---------------------------------------------------------------------------
MEAT = {
    # NL
    "vlees", "rund", "rundvlees", "rundsvlees", "gehakt", "gehakts",
    "kip", "kippenvlees", "kipfilet", "kippenborst", "kippendij", "kippenbout",
    "varken", "varkensvlees", "varkenshaas", "spek", "spekjes", "ham", "hesp",
    "worst", "worstjes", "braadworst", "chipolata", "salami", "chorizo",
    "lam", "lamsvlees", "lamsbout", "kalf", "kalfsvlees", "konijn",
    "eend", "eendenborst", "kalkoen", "gevogelte", "wild", "hert", "ree",
    "bacon", "pancetta", "prosciutto", "parmaham", "coppa", "lardon", "lardons",
    "reuzel", "gelatine", "gelatineblaadjes", "bloedworst", "pate", "paté",
    "kippenbouillon", "runderbouillon", "vleesbouillon", "kalfsfond", "fond",
    "filet américain", "americain", "vol-au-vent-vulling",
    "stoofvlees", "carbonade", "bouletten", "frikandel",
    # FR
    "boeuf", "porc", "poulet", "agneau", "veau", "lapin", "canard", "dinde",
    "jambon", "saucisse", "saucisson", "lardons", "viande", "volaille",
    # EN
    "beef", "pork", "chicken", "lamb", "veal", "bacon", "sausage", "gelatin",
}

FISH = {
    # NL
    "vis", "visfilet", "zalm", "kabeljauw", "tonijn", "forel", "makreel",
    "haring", "sardine", "sardines", "ansjovis", "ansjovisfilet", "schol",
    "pladijs", "tong", "tarbot", "zeebaars", "zeeduivel", "wijting", "koolvis",
    "garnaal", "garnalen", "scampi", "mossel", "mosselen", "oester", "oesters",
    "krab", "kreeft", "langoustine", "inktvis", "calamares", "calamari",
    "sint-jakobsschelp", "sint-jakobsschelpen", "coquilles", "surimi",
    "vissaus", "visbouillon", "visfond", "worcestershire", "worcestershiresaus",
    "kaviaar", "gerookte", "rolmops", "haringfilet",
    # FR
    "poisson", "saumon", "cabillaud", "thon", "crevette", "crevettes",
    "moules", "anchois", "sauce poisson",
    # EN
    "fish", "salmon", "cod", "tuna", "shrimp", "prawn", "anchovy", "oyster",
}

# ---------------------------------------------------------------------------
# Contains dairy/egg/honey -> vegetarian but NOT vegan
# ---------------------------------------------------------------------------
DAIRY = {
    "melk", "volle melk", "halfvolle", "karnemelk", "condensmelk",
    "melkpoeder", "room", "slagroom", "zure room", "creme fraiche",
    "crème fraîche", "boter", "roomboter", "ghee", "kaas", "kaasje",
    "mozzarella", "parmezaan", "parmezaanse", "grana", "pecorino", "feta",
    "ricotta", "mascarpone", "gorgonzola", "brie", "camembert", "gruyere",
    "gruyère", "emmentaler", "cheddar", "geitenkaas", "roomkaas",
    "plattekaas", "kwark", "hüttenkäse", "yoghurt", "vla", "pudding",
    "wei", "lactose",
    # FR
    "lait", "creme", "crème", "beurre", "fromage", "yaourt",
    # EN
    "milk", "cream", "butter", "cheese", "yoghurt", "yogurt",
}

EGG = {
    "ei", "eieren", "eitje", "eigeel", "eidooier", "eiwit", "eiwitten",
    "eierdooier", "mayonaise", "mayo", "meringue",
    "oeuf", "oeufs", "jaune d'oeuf", "blanc d'oeuf",
    "egg", "eggs", "mayonnaise",
}

HONEY = {"honing", "honingraat", "bijenwas", "miel", "honey", "beeswax"}

# ---------------------------------------------------------------------------
# Ambiguous: forces UNCERTAIN unless a safe compound disambiguates it.
# ---------------------------------------------------------------------------
AMBIGUOUS = {
    "bouillon", "bouillonblokje", "bouillonblokjes", "fond", "stock",
    "kaasvervanger", "roomvervanger", "margarine",   # margarine may contain whey
    "pesto",          # classic pesto has pecorino/parmesan
    "worcestershire", # anchovy, but some brands are vegan
    "ceasardressing", "caesardressing",
    "curry pasta", "currypasta",   # often contains shrimp paste
    "kimchi",                      # often contains fish sauce
    "parmezaan",                   # animal rennet: strict veg would exclude
}

# ---------------------------------------------------------------------------
# The MIRROR problem: Dutch compounds also HIDE animal terms.
#
#     kippenbouten   -- "kip" is only a prefix, exact-token matching misses it
#     roomijs, kaassaus, melkchocolade, vissticks, runderrookvlees ...
#
# So after SAFE_COMPOUNDS has been stripped, we also match on word-initial
# prefixes. This is only safe BECAUSE the safe-list ran first: "boterbonen"
# and "vleestomaat" are already gone by the time "boter"/"vlees" fire here.
#
# Keep genuinely risky stems OUT of these sets and handle them as exact tokens:
#   "wild"  -> "wilde rijst" is wild rice, vegan
#   "ham"   -> "hamburgerbroodje" is bread
#   "ei"    -> far too short; only explicit egg stems below
# ---------------------------------------------------------------------------
MEAT_PREFIXES = {
    "kip", "kippen", "rund", "runder", "runds", "varken", "varkens",
    "kalfs", "lams", "eend", "eenden", "kalkoen", "gehakt", "spek",
    "worst", "konijn", "gevogelte", "vlees", "hert", "bacon", "salami",
    "chorizo", "pancetta", "lardon", "braadworst", "stoofvlees",
    "poulet", "boeuf", "porc", "jambon", "saucis",
}

FISH_PREFIXES = {
    "vis", "zalm", "kabeljauw", "tonijn", "garnaal", "garnalen", "mossel",
    "oester", "ansjovis", "sardine", "haring", "makreel", "forel", "schol",
    "scampi", "krab", "kreeft", "inktvis", "surimi", "coquille", "zeevruchten",
    "poisson", "saumon", "crevette",
}

DAIRY_PREFIXES = {
    "melk", "room", "boter", "kaas", "yoghurt", "mozzarella", "parmezaan",
    "ricotta", "mascarpone", "karnemelk", "slagroom", "gorgonzola",
    "fromage", "beurre",
}

EGG_PREFIXES = {"eier", "eigeel", "eidooier", "eiwit", "eidoo"}

HONEY_PREFIXES = {"honing"}

# Minimum prefix length before we allow a prefix match, to avoid noise.
MIN_PREFIX = 3

# Convenience roll-ups used by classify.py
NON_VEGETARIAN = MEAT | FISH
NON_VEGAN = DAIRY | EGG | HONEY
