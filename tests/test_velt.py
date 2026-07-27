"""Velt calendar data integrity + lexicon reconciliation.

These are the tests that catch a lexicon edit silently orphaning a Velt crop.
No network, no database: CSV and lexicon only.
"""
import csv
from collections import Counter
from pathlib import Path

import pytest

from classify import match_seasonal
from lexicon.seasonal import PRODUCE, NOT_IN_VELT
from load_velt import CSV_PATH, reconcile, read_csv

EXPECTED_CROPS = 70
EXPECTED_ROWS = 421


@pytest.fixture(scope="module")
def rows():
    if not CSV_PATH.exists():
        pytest.skip("velt CSV not generated; run transcribe_velt.py")
    return read_csv()


# --- data integrity --------------------------------------------------------
def test_csv_exists_and_is_the_expected_size(rows):
    assert len(rows) == EXPECTED_ROWS
    assert len({r["velt_name"] for r in rows}) == EXPECTED_CROPS


def test_every_month_is_populated(rows):
    per_month = Counter(r["month"] for r in rows)
    assert set(per_month) == set(range(1, 13))
    assert min(per_month.values()) > 15


def test_no_duplicate_crop_month_pairs(rows):
    pairs = [(r["velt_name"], r["month"]) for r in rows]
    dupes = [p for p, c in Counter(pairs).items() if c > 1]
    assert not dupes, f"duplicated: {dupes}"


def test_kind_is_consistent_per_crop(rows):
    """A crop can't be a vegetable in June and fruit in July."""
    kinds = {}
    for r in rows:
        kinds.setdefault(r["velt_name"], set()).add(r["kind"])
    mixed = {n: k for n, k in kinds.items() if len(k) > 1}
    assert not mixed, f"inconsistent kind: {mixed}"


def test_summer_has_more_crops_than_winter(rows):
    per_month = Counter(r["month"] for r in rows)
    assert per_month[8] > per_month[2]


# --- reconciliation against the lexicon ------------------------------------
def test_every_velt_crop_maps_to_a_canonical(rows):
    _, unmatched, _ = reconcile(rows)
    assert not unmatched, (
        f"{len(unmatched)} Velt crops have no lexicon entry: {unmatched}. "
        "Add them to lexicon/seasonal.py -- an unmapped crop is silently "
        "dropped at load time."
    )


def test_no_two_velt_crops_collapse_into_one_canonical(rows):
    """Velt treats spitskool and wittekool as different crops with different
    month ranges. Collapsing them would corrupt both."""
    _, _, collisions = reconcile(rows)
    assert not collisions, f"collisions: {collisions}"


def test_spitskool_and_wittekool_stay_distinct(rows):
    assert match_seasonal("spitskool") == "spitskool"
    assert match_seasonal("wittekool") == "wittekool"
    spits = {r["month"] for r in rows if r["velt_name"] == "spitskool"}
    witte = {r["month"] for r in rows if r["velt_name"] == "wittekool"}
    assert spits != witte, "if these ever match, the split is pointless"


def test_lexicon_keys_match_velt_spelling_except_one(rows):
    """Keys track Velt spelling. `witloof` is the single sanctioned deviation
    (Belgian spelling; Velt writes the Dutch `witlof`)."""
    mapping, _, _ = reconcile(rows)
    deviations = {n: c for n, c in mapping.items() if n != c}
    assert deviations == {"witlof": "witloof"}, (
        f"unexpected spelling deviations: {deviations}"
    )


def test_not_in_velt_is_accurate(rows):
    """The documented gap list must match reality, or the docs lie."""
    mapping, _, _ = reconcile(rows)
    actual = set(PRODUCE) - set(mapping.values())
    assert actual == NOT_IN_VELT, (
        f"NOT_IN_VELT is stale.\n  missing from constant: {actual - NOT_IN_VELT}"
        f"\n  no longer a gap: {NOT_IN_VELT - actual}"
    )


# --- properties worth knowing about ----------------------------------------
def test_year_round_crops_are_what_we_think(rows):
    """Seven crops are listed every month, so they carry no seasonal signal.
    If this set changes, revisit AROMATICS and the planner's weighting."""
    counts = Counter(r["velt_name"] for r in rows)
    year_round = {n for n, c in counts.items() if c == 12}
    assert year_round == {
        "aardappel", "groene selderij", "paddenstoelen", "prei",
        "rode biet", "ui", "wortel",
    }


def test_asparagus_is_tightly_seasonal(rows):
    """Sanity anchor: if asperge ever goes year-round, the data is wrong."""
    months = {r["month"] for r in rows if r["velt_name"] == "asperge"}
    assert months == {5, 6}


def test_witlof_covers_the_winter(rows):
    months = {r["month"] for r in rows if r["velt_name"] == "witlof"}
    assert {11, 12, 1, 2, 3} <= months
    assert 7 not in months
