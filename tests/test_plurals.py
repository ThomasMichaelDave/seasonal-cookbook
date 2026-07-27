"""Dutch vowel-shortening plurals: raap->rapen, not raapen.

Regression guard for a bug that silently cost seasonal matches on the existing
Belgian corpus: aa/ee/oo/uu closing a stem shorten before the plural -en, so
plain suffix-appending ('raap'+'en'='raapen') never generated the real word.
Surfaced by docs/vegan_sources.md.
"""
import pytest

from classify import match_seasonal


@pytest.mark.parametrize("plural,canonical", [
    ("500 g rapen", "raap"),
    ("2 koolrapen", "koolraap"),
    ("aardperen", "aardpeer"),
    ("300 g pastinaken", "pastinaak"),
    ("2 bloemkolen", "bloemkool"),
    ("3 peren", "peer"),
    ("spitskolen", "spitskool"),
    ("2 wittekolen", "wittekool"),
    ("boerenkolen", "boerenkool"),
    ("schorseneren", "schorseneer"),
    ("prinsessenbonen", "prinsessenboon"),
])
def test_vowel_shortening_plurals_match(plural, canonical):
    assert match_seasonal(plural) == canonical


@pytest.mark.parametrize("singular,canonical", [
    ("1 raap", "raap"),
    ("1 bloemkool", "bloemkool"),
    ("300 g pastinaak", "pastinaak"),
])
def test_singular_still_matches(singular, canonical):
    assert match_seasonal(singular) == canonical
