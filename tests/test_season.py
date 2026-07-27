"""season.py: DB-backed season scoring feeds the planner correctly."""
import db
import season
from tests.test_planner import seed_corpus


def _db():
    conn = db.connect(":memory:")
    db.init(conn)
    seed_corpus(conn)
    return conn


def test_hero_in_season_flips_with_month():
    conn = _db()
    rid = conn.execute("SELECT id FROM recipes WHERE title LIKE 'Pompoen%'").fetchone()["id"]
    # pompoen: in season Sep-Nov, out in June
    _score_sep, hero_sep, n_sep = season.score_all(conn, 9)[rid]
    _score_jun, hero_jun, n_jun = season.score_all(conn, 6)[rid]
    assert hero_sep is True and n_sep > 0
    assert hero_jun is False and n_jun > 0          # has a hero, just out of season


def test_neutral_recipe_has_no_seasonal_signal():
    conn = _db()
    rid = conn.execute("SELECT id FROM recipes WHERE title LIKE 'Pasta carbonara%'").fetchone()["id"]
    score, hero_ok, n = season.score_all(conn, 9)[rid]
    assert n == 0 and hero_ok is False and score == 0.0


def test_year_round_hero_is_always_in_season():
    conn = _db()
    rid = conn.execute("SELECT id FROM recipes WHERE title LIKE 'Prei-%'").fetchone()["id"]
    for month in (1, 6, 12):
        _s, hero_ok, n = season.score_all(conn, month)[rid]
        assert hero_ok is True and n > 0
