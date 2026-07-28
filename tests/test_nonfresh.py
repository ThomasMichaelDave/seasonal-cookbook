"""Processed 'false friends' must not read as fresh seasonal produce.

A jar of ketchup is not a tomato in season; apple cider is not an apple; garlic
paste is not fresh garlic on the shopping list. match_seasonal strips
lexicon.seasonal.NONFRESH_FORMS before matching. These are the cases surfaced by
alias verification on the eastern corpus.
"""
import pytest

from classify import match_seasonal

# Processed forms -> must NOT match a fresh canonical.
NONFRESH = [
    "tomato ketchup", "2 tbsp tomato paste", "tomato puree", "tomato passata",
    "1 tbsp tomato concentrate", "sun-dried tomatoes", "sun dried tomato",
    "apple cider", "apple cider vinegar", "2 tbsp apple cider vinegar",
    "125 ml apple juice", "apple sauce",
    "garlic paste", "1 tbsp ginger garlic paste", "ginger-garlic paste",
    "1 tsp garlic powder", "onion powder", "garlic salt",
    "2 tbsp potato starch", "potato flour",
]

# Fresh forms -> must STILL match, unchanged by the strip.
FRESH = [
    ("3 ripe tomatoes", "tomaat"), ("2 vleestomaten", "tomaat"),
    ("een handvol kerstomaatjes", "tomaat"), ("500 g tomaten", "tomaat"),
    ("1 appel", "appel"), ("2 apples, cored", "appel"),
    ("3 teentjes knoflook", "knoflook"), ("2 cloves garlic", "knoflook"),
    ("1 grote ui", "ui"), ("2 onions", "ui"),
    ("1 kg aardappelen", "aardappel"), ("4 potatoes", "aardappel"),
    # the transliterated pass must still work through the strip
    ("2 cups aloo", "aardappel"), ("baingan", "aubergine"),
]


@pytest.mark.parametrize("text", NONFRESH)
def test_processed_forms_are_not_fresh_produce(text):
    assert match_seasonal(text) is None


@pytest.mark.parametrize("text,canonical", FRESH)
def test_fresh_produce_still_matches(text, canonical):
    assert match_seasonal(text) == canonical
