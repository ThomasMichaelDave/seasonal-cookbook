"""courses.py: main vs dessert/side, against real titles from the crawl."""
import pytest

from courses import classify_course


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
def test_desserts(title):
    assert classify_course(title) == "dessert"


@pytest.mark.parametrize("title,ings", [
    ("One pot champignon-aardappeltaart met prei", ["prei", "aardappelen"]),
    ("Tarte tatin met sjalot en warmoes met spekjes en geitenkaas", ["spekjes"]),
    ("Plaattaart met gerookte zalm, rode biet en veldsla", ["gerookte zalm"]),
    ("Italiaanse plaattaart met pesto, prosciutto en courgette", ["prosciutto"]),
    ("Pasta arrabiata met kip, champignons en courgette", ["spaghetti"]),
    ("Steak met zoete aardappel, salade en lemon-pepper mayo", ["steak"]),
    # savoury crumble must NOT read as dessert
    ("Verse pasta met chorizocrumble en pittig tomatensausje", ["verse tagliatelle"]),
])
def test_mains(title, ings):
    assert classify_course(title, ings) == "main"


@pytest.mark.parametrize("title", [
    "Loempia's uit de airfryer",
    "Wortelfrietjes uit de airfryer",
])
def test_sides(title):
    assert classify_course(title) == "side"


def test_ijs_does_not_catch_ijsbergsla():
    # 'ijsbergsla' (iceberg lettuce) must not be read as ice cream
    assert classify_course("Salade met ijsbergsla, kip en tomaat") == "main"
