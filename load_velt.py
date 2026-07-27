"""Load the Velt seizoenskalender CSV into the `seasonality` table.

    python load_velt.py            # load + report
    python load_velt.py --report   # report only, no writes

Idempotent: clears and reloads the `velt` cultivation tier, leaving any
field/greenhouse/storage rows from other sources untouched.

WHAT THE VELT DATA IS AND IS NOT
--------------------------------
The printed Groente- en fruitkalender is a flat monthly list. It does NOT
carry a low/normal/high supply gradient, and it does NOT distinguish open
field from unheated greenhouse from storage. So every row loads as:

    availability = 3   (listed; levels 1 and 2 stay unused)
    cultivation  = 'velt'   (cultivation unspecified)

`velt` is accepted by all three strictness levels, so the strictness dial is
inert until a source with a real cultivation split is layered in. Loading
everything as 'field' would have been a lie -- potatoes in February are
storage, not field -- so the tier is named after its source instead.

See docs/velt.md for the reconciliation notes and the known gaps.
"""
import csv
import sys
from pathlib import Path

import db
from classify import match_seasonal
from lexicon.seasonal import PRODUCE, NOT_IN_VELT

CSV_PATH = Path(__file__).resolve().parent / "data" / "velt" / "velt_seizoenskalender_2019.csv"
CULTIVATION = "velt"
AVAILABILITY = 3


def read_csv(path=CSV_PATH):
    if not path.exists():
        sys.exit(f"missing {path}\nrun: python transcribe_velt.py")
    with open(path, encoding="utf-8", newline="") as fh:
        return [
            {"velt_name": r["velt_name"], "kind": r["kind"], "month": int(r["month"])}
            for r in csv.DictReader(fh)
        ]


def reconcile(rows):
    """Map every Velt crop name onto a canonical key. Report, don't guess."""
    names = sorted({r["velt_name"] for r in rows})
    mapping, unmatched = {}, []
    for name in names:
        canon = match_seasonal(name)
        if canon:
            mapping[name] = canon
        else:
            unmatched.append(name)

    collisions = {}
    for canon in set(mapping.values()):
        sources = [n for n, c in mapping.items() if c == canon]
        if len(sources) > 1:
            collisions[canon] = sources

    return mapping, unmatched, collisions


def load(conn, rows, mapping):
    for nl, kind, en, pairs in __import__("lexicon.seasonal", fromlist=["rows"]).rows():
        conn.execute(
            "INSERT OR IGNORE INTO canonical(name_nl, name_en, kind) VALUES (?,?,?)",
            (nl, en, kind),
        )
        cid = conn.execute("SELECT id FROM canonical WHERE name_nl=?", (nl,)).fetchone()["id"]
        for alias, lang in pairs:
            conn.execute(
                "INSERT OR IGNORE INTO aliases(alias, lang, canonical_id) VALUES (?,?,?)",
                (alias.lower(), lang, cid),
            )

    ids = {r["name_nl"]: r["id"] for r in conn.execute("SELECT id, name_nl FROM canonical")}

    conn.execute("DELETE FROM seasonality WHERE cultivation=?", (CULTIVATION,))
    written = 0
    for row in rows:
        canon = mapping.get(row["velt_name"])
        if not canon:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO seasonality(canonical_id, month, availability, cultivation) "
            "VALUES (?,?,?,?)",
            (ids[canon], row["month"], AVAILABILITY, CULTIVATION),
        )
        written += 1
    conn.commit()
    return written


def seasonality_dict(conn):
    """-> {canonical_nl: {(month, cultivation): availability}} for season_score."""
    out = {}
    for r in conn.execute(
        "SELECT c.name_nl, s.month, s.availability, s.cultivation "
        "FROM seasonality s JOIN canonical c ON c.id = s.canonical_id"
    ):
        out.setdefault(r["name_nl"], {})[(r["month"], r["cultivation"])] = r["availability"]
    return out


def report(rows, mapping, unmatched, collisions):
    names = sorted({r["velt_name"] for r in rows})
    print(f"Velt 2019 calendar: {len(rows)} rows, {len(names)} distinct crops")
    print(f"  matched to lexicon: {len(mapping)}/{len(names)}")

    if unmatched:
        print(f"\n  !! UNMATCHED ({len(unmatched)}) -- add these to lexicon/seasonal.py:")
        for n in unmatched:
            print(f"       {n}")
    if collisions:
        print(f"\n  !! COLLISIONS -- two Velt crops mapping to one canonical:")
        for canon, sources in collisions.items():
            print(f"       {canon} <- {sources}")
        print("       Velt treats these as distinct crops; split the lexicon entry.")

    spelling = [(n, c) for n, c in sorted(mapping.items()) if n != c]
    if spelling:
        print(f"\n  spelling deviations (Velt name -> lexicon key):")
        for n, c in spelling:
            print(f"       {n:20} -> {c}")

    gaps = sorted(set(PRODUCE) - set(mapping.values()))
    print(f"\n  lexicon entries with no Velt row ({len(gaps)}): {', '.join(gaps)}")
    if set(gaps) != NOT_IN_VELT:
        print("       !! differs from NOT_IN_VELT in lexicon/seasonal.py -- update it")
    print("       these score as UNKNOWN (skipped), never as out-of-season")

    counts = {}
    for r in rows:
        counts[r["velt_name"]] = counts.get(r["velt_name"], 0) + 1
    year_round = sorted(n for n, c in counts.items() if c == 12)
    print(f"\n  listed in ALL 12 months ({len(year_round)}):")
    print(f"       {', '.join(year_round)}")
    print("       these carry no discriminating seasonal signal; 'ui' is already")
    print("       excluded as an aromatic, the rest still count (a leek tart is")
    print("       legitimately a leek dish)")

    per_month = {m: sum(1 for r in rows if r["month"] == m) for m in range(1, 13)}
    print("\n  crops per month:")
    bars = "".join(f"{m:>4}" for m in range(1, 13))
    vals = "".join(f"{per_month[m]:>4}" for m in range(1, 13))
    print(f"     month {bars}")
    print(f"     crops {vals}")


def main():
    rows = read_csv()
    mapping, unmatched, collisions = reconcile(rows)
    report(rows, mapping, unmatched, collisions)

    if "--report" in sys.argv:
        return

    conn = db.connect()
    db.init(conn)
    written = load(conn, rows, mapping)
    print(f"\nwrote {written} seasonality rows (cultivation='{CULTIVATION}')")

    total = conn.execute("SELECT COUNT(*) c FROM seasonality").fetchone()["c"]
    print(f"seasonality table now holds {total} rows")


if __name__ == "__main__":
    main()
