"""v2 transliterated alias pass: romanised Hindi/Korean/Japanese/pinyin produce
names must resolve to their Belgian Velt canonical, and vegetables with no Velt
equivalent must keep scoring `unknown` (None), not a wrong guess.

See docs/vegan_sources.md (prereq #2) and lexicon/seasonal.py TRANSLITERATED.
"""
import pytest

from classify import match_seasonal
from lexicon.seasonal import PRODUCE, TRANSLITERATED, APPROXIMATE

# (transliteration, expected canonical). One or two per language where it matters.
MAPS = [
    # eggplant
    ("baingan", "aubergine"), ("brinjal", "aubergine"), ("gaji", "aubergine"),
    ("nasu", "aubergine"), ("qiezi", "aubergine"),
    # cauliflower (gobi / phool gobi -- NOT patta gobi, which is cabbage)
    ("gobi", "bloemkool"), ("phool gobi", "bloemkool"),
    # potato
    ("aloo", "aardappel"), ("gamja", "aardappel"), ("jagaimo", "aardappel"),
    ("tudou", "aardappel"),
    # onion
    ("pyaz", "ui"), ("yangpa", "ui"), ("tamanegi", "ui"), ("yangcong", "ui"),
    # garlic
    ("lehsun", "knoflook"), ("maneul", "knoflook"), ("ninniku", "knoflook"),
    # spinach
    ("palak", "spinazie"), ("sigeumchi", "spinazie"), ("horenso", "spinazie"),
    # peas
    ("matar", "doperwt"),
    # carrot
    ("gajar", "wortel"), ("danggeun", "wortel"), ("ninjin", "wortel"),
    ("hu luobo", "wortel"),
    # turnip
    ("shalgam", "raap"),
    # napa cabbage
    ("baechu", "chinese kool"), ("hakusai", "chinese kool"),
    ("da baicai", "chinese kool"),
    # courgette / pumpkin / tomato
    ("ae hobak", "courgette"), ("kabocha", "pompoen"), ("nangua", "pompoen"),
    ("xihongshi", "tomaat"), ("fanqie", "tomaat"),
]

# These are real vegetables with NO Velt crop. Mapping them would be a lie, so
# they must stay None (scored unknown -> skipped), never an approximation.
NO_VELT_EQUIVALENT = [
    "bhindi", "okra", "karela", "methi", "gobo", "taro", "renkon",
    "lotus root", "drumstick",
]

# Owner-reversible approximations (a different vegetable, closest Velt crop).
APPROX_MAPS = [
    ("daikon", "rammenas"), ("mooli", "rammenas"), ("white radish", "rammenas"),
    ("bai luobo", "rammenas"), ("rettich", "rammenas"),
]


@pytest.mark.parametrize("text,canonical", MAPS)
def test_transliteration_resolves(text, canonical):
    assert match_seasonal(text) == canonical


@pytest.mark.parametrize("text,canonical", MAPS)
def test_transliteration_resolves_in_a_quantified_line(text, canonical):
    # As it actually appears in a recipe, not bare.
    assert match_seasonal(f"2 cups {text}, chopped") == canonical


@pytest.mark.parametrize("word", NO_VELT_EQUIVALENT)
def test_no_velt_equivalent_stays_unknown(word):
    assert match_seasonal(word) is None


@pytest.mark.parametrize("text,canonical", APPROX_MAPS)
def test_approximations_resolve_to_closest_velt_crop(text, canonical):
    # daikon/mooli -> rammenas is a documented, owner-reversible approximation.
    assert match_seasonal(text) == canonical


def test_carrot_pinyin_not_shadowed_by_radish_approximation():
    # `hu luobo` (carrot) must still win over the `bai luobo` (radish) approx:
    # longest-match-first, and neither should collapse to the other.
    assert match_seasonal("hu luobo") == "wortel"
    assert match_seasonal("bai luobo") == "rammenas"


def test_every_alias_target_canonical_exists():
    unknown = [c for c in (*TRANSLITERATED, *APPROXIMATE) if c not in PRODUCE]
    assert not unknown, f"alias block targets a non-existent canonical: {unknown}"
