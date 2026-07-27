"""courses.py: main vs dessert/side, against real titles from the crawl.

Every case passes an ingredient list, because production (courses.by_recipe)
ALWAYS passes ingredient_texts -- a test that calls classify_course(title) with
no ingredients exercises a branch the caller never hits. SWEET_PANTRY makes the
'ui' in 'suiker' collision impossible to reintroduce unnoticed.
"""
import pytest

from courses import classify_course

SWEET_PANTRY = ["bloem", "suiker", "boter", "eieren"]      # in ~every sweet bake


@pytest.mark.parametrize("title", [
    "Cheesecake met aardbeien",
    "Simpele citroencake",
    "Courgette-citroencake",
    "Chocolademousse, suzette saus en krokante meringue",
    "Eton mess met frambozen en violette",
    "Smoutebollen met appel en rozijnen",
    "Kaneeltaart",
    "Hazelnoottaart met peer en brésiliennenootjes",
    "Rice Krispie repen",
    "Frisse lemoncurd met passievrucht en crumble van kruidnoten",
    "Blondies met banaan",
    "Havermoutcrumble met rabarber en gember",
    "île flottante, vanillesaus met speculaas en karamel",
    "Bavarois van banaan met karamelsaus en geroosterde pinda's",
    "Confituur-shortbread koekjes",
    "Ananastaart met meringue",
    "Briochetaart",
    "Aardbeien, compote van rabarber, crème chiboust en spritskoeken",
])
def test_desserts_with_ingredients(title):
    assert classify_course(title, SWEET_PANTRY) == "dessert"


@pytest.mark.parametrize("title", [
    "Appeltaart", "Perentaart", "Kersenvlaai", "Abrikozentaart",
    "Chocoladetaart", "Suikertaart", "Rijsttaart", "Kaneeltaart", "Briochetaart",
])
def test_sweet_tarts_are_dessert_despite_sugar(title):
    # regression for 'ui' in 'suiker' -- these all contain sugar. ('Kaastaart'
    # deliberately omitted: in Flemish it's cheesecake, but 'kaas' is a genuine
    # savoury marker, so it's an ambiguous call the review didn't ask us to make.)
    assert classify_course(title, SWEET_PANTRY) == "dessert"


@pytest.mark.parametrize("title,ings", [
    ("Preitaart met geitenkaas", ["prei", "geitenkaas", "eieren", "room"]),
    ("Uientaart", ["uien", "kaas", "eieren", "boter"]),
    ("Quiche lorraine", ["spek", "eieren", "room"]),
    ("One pot champignon-aardappeltaart met prei", ["champignon", "aardappelen", "prei"]),
    ("Tarte tatin met sjalot en warmoes met spekjes", ["warmoes", "spekjes"]),
    ("Plaattaart met gerookte zalm, rode biet en veldsla", ["gerookte zalm"]),
    ("Pasta arrabiata met kip, champignons en courgette", ["spaghetti", "kip"]),
    ("Steak met zoete aardappel, salade en lemon-pepper mayo", ["steak", "zoete aardappel"]),
    # savoury crumble must NOT read as dessert
    ("Verse pasta met chorizocrumble en pittig tomatensausje", ["verse tagliatelle", "chorizo", "tomaat"]),
])
def test_savoury_mains(title, ings):
    assert classify_course(title, ings) == "main"


def test_radijs_salad_is_main():
    # regression for 'radijs' ending in '-ijs'
    assert classify_course("Salade met radijs en veldsla", ["radijs", "veldsla"]) == "main"
    assert classify_course("Lauwe salade met gebakken radijsjes", ["radijs"]) == "main"


def test_real_ice_cream_still_dessert():
    assert classify_course("Roomijs met aardbeien", ["room", "suiker", "aardbeien"]) == "dessert"
    assert classify_course("Gemarineerde ananas met vanille-ijs", ["ananas", "vanille-ijs"]) == "dessert"


@pytest.mark.parametrize("title", ["Loempia's uit de airfryer", "Wortelfrietjes uit de airfryer"])
def test_sides(title):
    assert classify_course(title, ["olie"]) == "side"


def test_ijs_does_not_catch_ijsbergsla():
    assert classify_course("Salade met ijsbergsla, kip en tomaat", ["ijsbergsla", "kip"]) == "main"
