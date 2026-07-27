"""One-off transcription of the Velt Groente- en fruitkalender (2019 edition).

Run once to (re)generate data/velt/velt_seizoenskalender_2019.csv.
Kept in the repo so the transcription is auditable and re-runnable rather
than a CSV of unknown provenance.

Source: Velt vzw, "Groente- en fruitkalender", V.U. Leen Laenens, 2019.
        https://velt.nu/seizoenskalender

WHAT THIS SOURCE ACTUALLY IS -- read before trusting it:
  * BINARY. A crop is listed in a month or it is not. There is no
    low/normal/high gradient.
  * NO CULTIVATION SPLIT. The printed calendar does NOT distinguish open
    field from unheated greenhouse from storage. See docs/velt.md.
  * Velt's framing is ecological: the leaflet argues against transport,
    heated greenhouses and refrigeration. But the calendar still lists
    storage crops (potato in February, apple in March) without labelling
    them as such.
  * Fruit is typeset in bold in the original; that split is preserved in
    the `kind` column.
"""
import csv
from pathlib import Path

EDITION = "2019"
OUT = Path(__file__).resolve().parent / "data" / "velt" / "velt_seizoenskalender_2019.csv"

MONTHS = {
    1: "januari", 2: "februari", 3: "maart", 4: "april", 5: "mei", 6: "juni",
    7: "juli", 8: "augustus", 9: "september", 10: "oktober", 11: "november",
    12: "december",
}

# Transcribed verbatim from the printed columns. Names are kept EXACTLY as
# Velt spells them -- reconciliation to the lexicon happens in load_velt.py,
# never here.
VEG = {
    3: """aardappel bloemkool boerenkool "groene selderij" knolselderij
          paddenstoelen pastinaak pompoen prei raap radijs rammenas
          "rode biet" rodekool roodlof savooikool schorseneer spinazie
          spruiten ui veldsla warmoes winterpostelein witlof wittekool
          wortel""",
    4: """aardappel andijvie bloemkool "groene selderij" paddenstoelen paksoi
          pompoen prei raap raapsteel radijs "rode biet" roodlof spinazie ui
          warmoes waterkers wortel witlof""",
    5: """aardappel andijvie asperge bloemkool doperwt "groene selderij"
          koolrabi kropsla paddenstoelen paksoi peultjes prei raap raapsteel
          radijs "rode biet" roodlof spinazie spitskool ui warmoes waterkers
          wortel""",
    6: """aardappel andijvie artisjok asperge bloemkool broccoli doperwt
          "groene selderij" koolrabi kropsla paddenstoelen paksoi peultjes
          prei prinsessenboon raap radijs "rode biet" savooikool spinazie
          spitskool tomaat tuinboon ui venkel warmoes waterkers wortel""",
    7: """aardappel andijvie artisjok aubergine bleekselderij bloemkool
          broccoli "chinese kool" courgette doperwt "groene selderij"
          komkommer koolrabi kropsla paddenstoelen paksoi paprika peultjes
          prei prinsessenboon radijs "rode biet" rodekool savooikool snijboon
          spinazie spitskool tomaat tuinboon ui venkel warmoes waterkers
          wittekool wortel""",
    8: """aardappel andijvie artisjok aubergine bleekselderij bloemkool
          broccoli "chinese kool" courgette "groene selderij" knolselderij
          komkommer koolrabi kropsla mais paddenstoelen paksoi paprika pompoen
          prei prinsessenboon raapsteel radijs "rode biet" rodekool savooikool
          snijboon spinazie spitskool tomaat ui venkel warmoes waterkers
          wittekool wortel""",
    9: """aardappel andijvie artisjok aubergine bleekselderij bloemkool
          broccoli "chinese kool" courgette "groene selderij" knolselderij
          komkommer koolrabi kropsla mais paddenstoelen paksoi paprika pompoen
          prei prinsessenboon raapsteel radijs rammenas "rode biet" rodekool
          savooikool snijboon spinazie spitskool tomaat ui venkel warmoes
          waterkers wittekool wortel""",
    10: """aardappel andijvie artisjok aubergine bleekselderij boerenkool
           bloemkool broccoli "chinese kool" courgette "groene selderij"
           knolselderij komkommer koolrabi kropsla paddenstoelen paksoi paprika
           pastinaak pompoen prei prinsessenboon raapsteel radijs rammenas
           "rode biet" rodekool roodlof savooikool schorseneer snijboon spinazie
           spitskool spruiten tomaat ui veldsla venkel warmoes waterkers
           winterpostelein witlof wittekool wortel""",
    11: """aardappel aardpeer andijvie bleekselderij bloemkool boerenkool
           broccoli "chinese kool" courgette "groene selderij" knolselderij
           koolraap paddenstoelen pastinaak pompoen prei raap rammenas
           "rode biet" rodekool savooikool schorseneer spruiten ui veldsla
           venkel warmoes waterkers winterpostelein witlof wittekool wortel""",
    12: """aardappel aardpeer andijvie boerenkool "groene selderij"
           knolselderij koolraap paddenstoelen pastinaak pompoen prei raap
           rammenas "rode biet" rodekool savooikool schorseneer spruiten ui
           veldsla waterkers winterpostelein witlof wittekool wortel""",
    1: """aardappel aardpeer boerenkool "groene selderij" knolselderij koolraap
          paddenstoelen pastinaak pompoen prei raap rammenas "rode biet"
          rodekool savooikool schorseneer spruiten ui veldsla waterkers
          winterpostelein witlof wittekool wortel""",
    2: """aardappel boerenkool "groene selderij" knolselderij paddenstoelen
          pastinaak pompoen prei raap rammenas "rode biet" rodekool savooikool
          schorseneer spruiten ui veldsla winterpostelein witlof wittekool
          wortel""",
}

# Bold entries in the original -- Velt's own culinary grouping.
FRUIT = {
    3:  """appel rabarber""",
    4:  """aardbei rabarber""",
    5:  """aardbei rabarber""",
    6:  """aardbei abrikoos "blauwe bes" framboos kers nectarine perzik
           rabarber "rode bes" "zwarte bes\"""",
    7:  """aardbei abrikoos "blauwe bes" braam framboos kers nectarine perzik
           rabarber "rode bes" "zwarte bes\"""",
    8:  """aardbei abrikoos appel "blauwe bes" braam druif framboos kers meloen
           nectarine peer perzik pruim vijg "zwarte bes\"""",
    9:  """appel "blauwe bes" braam druif framboos kiwibes meloen nectarine
           peer perzik pruim vijg""",
    10: """appel braam druif framboos kiwibes meloen peer""",
    11: """appel druif meloen peer""",
    12: """appel peer""",
    1:  """appel peer""",
    2:  """appel peer""",
}


def split(block: str) -> list[str]:
    """Whitespace-split, honouring "quoted multi-word names"."""
    return next(csv.reader([" ".join(block.split())], delimiter=" "))


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for month in range(1, 13):
        for name in split(VEG[month]):
            rows.append((name, "vegetable", month, MONTHS[month]))
        for name in split(FRUIT[month]):
            rows.append((name, "fruit", month, MONTHS[month]))

    rows.sort(key=lambda r: (r[0], r[2]))
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["velt_name", "kind", "month", "month_name"])
        w.writerows(rows)

    names = sorted({r[0] for r in rows})
    print(f"wrote {OUT}")
    print(f"  edition {EDITION}: {len(rows)} rows, {len(names)} distinct crops")
    veg = sorted({r[0] for r in rows if r[1] == "vegetable"})
    fruit = sorted({r[0] for r in rows if r[1] == "fruit"})
    print(f"  {len(veg)} vegetables, {len(fruit)} fruit")

    counts = {n: sum(1 for r in rows if r[0] == n) for n in names}
    year_round = sorted(n for n, c in counts.items() if c == 12)
    print(f"\n  listed in ALL 12 months ({len(year_round)}): {', '.join(year_round)}")


if __name__ == "__main__":
    main()
