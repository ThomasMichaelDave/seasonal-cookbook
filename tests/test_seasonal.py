import pytest

from classify import (
    match_seasonal, mark_heroes, season_score, parse_ingredient, AROMATICS,
)

# Stand-in for the Velt import: {canonical: {(month, cultivation): availability}}
FAKE_SEASONALITY = {
    "witloof":    {(1, "field"): 3, (2, "field"): 3},
    "prei":       {(1, "field"): 3, (2, "field"): 2},
    "aardappel":  {(1, "storage"): 3, (7, "storage"): 2},
    "knolselderij": {(1, "storage"): 2},
    "tomaat":     {(7, "field"): 3, (1, "greenhouse"): 1},
    "courgette":  {(7, "field"): 3},
    "aubergine":  {(7, "greenhouse"): 3},
    "paprika":    {(7, "greenhouse"): 3},
    "ui":         {(1, "storage"): 3, (7, "storage"): 3},
}


def build(title, lines):
    parsed = []
    for line in lines:
        p = parse_ingredient(line)
        p["raw"] = line
        p["canonical"] = match_seasonal(p["ingredient_text"] or line)
        parsed.append(p)
    mark_heroes(title, parsed)
    return parsed


WINTER = ("Stoofpotje van witloof en prei", [
    "500 g prei, in ringen", "1 kg witloof", "2 vleestomaten",
    "3 teentjes knoflook", "snuf zout", "1,5 kg aardappelen", "2 uien",
])
SUMMER = ("Zomerse ratatouille", [
    "2 courgettes", "1 aubergine", "3 paprika's", "4 tomaten",
    "2 uien", "4 teentjes knoflook", "4 el olijfolie",
])
NEUTRAL = ("Pasta pesto", [
    "400 g spaghetti", "2 el pesto", "1 teentje knoflook",
])


# --- alias matching --------------------------------------------------------
@pytest.mark.parametrize(
    "text,expected",
    [
        ("prei", "prei"), ("poireaux", "prei"), ("leeks", "prei"),
        ("witlof", "witloof"), ("chicons", "witloof"),
        ("vleestomaten", "tomaat"), ("kerstomaatjes", "tomaat"),
        ("aardappelen", "aardappel"), ("pommes de terre", "aardappel"),
        ("sperziebonen", "prinsessenboon"), ("haricots verts", "prinsessenboon"),
        # Dutch diminutives are the NORMAL way to write these
        ("kerstomaatjes", "tomaat"), ("worteltjes", "wortel"),
        ("uitjes", "ui"), ("aardappeltjes", "aardappel"),
        ("boontjes", "prinsessenboon"), ("preitjes", "prei"),
        ("olijfolie", None), ("zout", None), ("spaghetti", None),
    ],
)
def test_match_seasonal(text, expected):
    assert match_seasonal(text) == expected


def test_longest_alias_wins():
    """'knolselder' must not be swallowed by 'selder'."""
    assert match_seasonal("1 knolselder") == "knolselderij"
    assert match_seasonal("2 stengels bleekselder") == "bleekselderij"


# --- hero detection --------------------------------------------------------
def test_title_match_defines_heroes():
    parsed = build(*WINTER)
    heroes = {i["canonical"] for i in parsed if i["is_hero"]}
    assert heroes == {"prei", "witloof"}


def test_aromatics_are_never_heroes():
    parsed = build(*WINTER)
    for ing in parsed:
        if ing["canonical"] in AROMATICS:
            assert not ing["is_hero"], f"{ing['canonical']} must not be a hero"


def test_bulk_defines_heroes_when_title_is_silent():
    parsed = build(*SUMMER)
    heroes = {i["canonical"] for i in parsed if i["is_hero"]}
    assert "tomaat" in heroes and "paprika" in heroes
    assert "ui" not in heroes and "knoflook" not in heroes


def test_recipe_without_produce_has_no_heroes():
    parsed = build(*NEUTRAL)
    assert not any(i["is_hero"] for i in parsed)


def test_ingredient_position_does_not_confer_hero_status():
    """First-listed onion must not become the hero. This regressed once."""
    parsed = build("Simpele soep", ["2 uien", "1 blokje bouillon", "1 l water"])
    assert not any(i["is_hero"] for i in parsed)


# --- scoring ---------------------------------------------------------------
def test_winter_dish_scores_high_in_january():
    parsed = build(*WINTER)
    score, hero_ok, n = season_score(parsed, 1, FAKE_SEASONALITY, "storage")
    assert score > 0.7
    assert hero_ok is True
    assert n > 0


def test_winter_dish_scores_low_in_july():
    parsed = build(*WINTER)
    score, hero_ok, _ = season_score(parsed, 7, FAKE_SEASONALITY, "storage")
    assert score < 0.3
    assert hero_ok is False


def test_summer_dish_inverts():
    parsed = build(*SUMMER)
    jan, jan_hero, _ = season_score(parsed, 1, FAKE_SEASONALITY, "greenhouse")
    jul, jul_hero, _ = season_score(parsed, 7, FAKE_SEASONALITY, "greenhouse")
    assert jul > jan
    assert jul_hero is True and jan_hero is False


def test_strictness_is_monotonic():
    """storage >= greenhouse >= field, always."""
    parsed = build(*WINTER)
    field, _, _ = season_score(parsed, 1, FAKE_SEASONALITY, "field")
    green, _, _ = season_score(parsed, 1, FAKE_SEASONALITY, "greenhouse")
    store, _, _ = season_score(parsed, 1, FAKE_SEASONALITY, "storage")
    assert field <= green <= store


def test_produceless_recipe_is_season_neutral():
    """n == 0 signals 'neutral'. The planner must not filter these out."""
    parsed = build(*NEUTRAL)
    score, hero_ok, n = season_score(parsed, 1, FAKE_SEASONALITY, "storage")
    assert n == 0
    assert score == 0.0
    assert hero_ok is False


def test_out_of_season_hero_fails_regardless_of_score():
    parsed = build("Witloof in de oven", ["1 kg witloof", "2 uien", "1 kg aardappelen"])
    score, hero_ok, _ = season_score(parsed, 7, FAKE_SEASONALITY, "storage")
    assert hero_ok is False


# --- unknown vs out-of-season ---------------------------------------------
def test_produce_with_no_data_is_skipped_not_penalised():
    """Absence of data is not evidence of absence.

    Velt doesn't list chanterelles. A recipe using them must not be scored as
    if they were out of season all year.
    """
    known = build("Preisoep", ["1 kg prei"])
    mixed = build("Preisoep met eierzwammen", ["1 kg prei", "200 g eierzwammen"])

    k_score, _, k_n = season_score(known, 1, FAKE_SEASONALITY, "field")
    m_score, _, m_n = season_score(mixed, 1, FAKE_SEASONALITY, "field")

    assert "eierzwam" not in FAKE_SEASONALITY, "fixture assumption"
    assert m_n == k_n, "unknown produce must not be counted"
    assert m_score == pytest.approx(k_score), "unknown produce must not drag the score"


def test_unknown_hero_does_not_fail_the_recipe():
    parsed = build("Eierzwammen op toast", ["300 g eierzwammen", "2 sneden brood"])
    _, hero_ok, n = season_score(parsed, 1, FAKE_SEASONALITY, "field")
    assert n == 0
    assert hero_ok is False       # neutral, not a failure signal


# --- the velt cultivation tier --------------------------------------------
VELT_ONLY = {"witloof": {(1, "velt"): 3, (2, "velt"): 3}}


def test_velt_tier_is_accepted_by_every_strictness_level():
    """Velt's calendar carries no cultivation split, so its rows must not be
    filtered out by the strictest setting."""
    parsed = build("Witloof in de oven", ["1 kg witloof"])
    scores = [season_score(parsed, 1, VELT_ONLY, s)[0]
              for s in ("field", "greenhouse", "storage")]
    assert all(s == pytest.approx(1.0) for s in scores)


def test_velt_tier_still_respects_month():
    parsed = build("Witloof in de oven", ["1 kg witloof"])
    score, hero_ok, _ = season_score(parsed, 7, VELT_ONLY, "storage")
    assert score == 0.0
    assert hero_ok is False
