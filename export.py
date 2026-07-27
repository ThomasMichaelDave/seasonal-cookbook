"""Export the corpus to a single, standalone cookbook.html.

100% standalone: the recipe facts AND the Velt seasonality map are INLINED into
one self-contained HTML file that runs the planner + grocery list entirely in
the browser -- no server, no network, no Python needed to use it. Double-click
it. Python (this script) is only used to GENERATE the file from cookbook.db.

Facts only (the copyright rule): title, source url, servings, diet, ingredients
(text/qty/unit/canonical), staple base, course, seasonal heroes. NO instruction
text -- we never stored it, and none is written here. Only MAINS with a serving
count are exported (the planner pool).

    py export.py                 -> cookbook.html
"""
import argparse
import json
from datetime import datetime

import config
import courses
import db
import grocery
import planner
import season
import staples


def build_data(conn) -> dict:
    # {canonical: [months it is in season]} from the Velt table
    seasonality = {}
    for name, mp in season.load_seasonality(conn).items():
        months = sorted({m for (m, _cult), a in mp.items() if a > 0})
        if months:
            seasonality[name] = months

    base_by = {rid: base for rid, _t, base, _s in staples.by_recipe(conn)}
    course_by = {rid: c for rid, _t, c in courses.by_recipe(conn)}

    recipes = {}
    for row in conn.execute(
        "SELECT r.id rid, r.title, r.url, r.diet, r.servings, s.name src, "
        "ri.ingredient_text itext, ri.raw_text raw, ri.qty, ri.unit, "
        "c.name_nl canon, ri.is_hero hero "
        "FROM recipes r JOIN sources s ON r.source_id=s.id "
        "JOIN recipe_ingredients ri ON ri.recipe_id=r.id "
        "LEFT JOIN canonical c ON ri.canonical_id=c.id "
        "ORDER BY r.id, ri.position"
    ):
        rid = row["rid"]
        if course_by.get(rid) != "main" or not row["servings"]:
            continue                       # planner pool = mains with servings
        r = recipes.setdefault(rid, {
            "id": rid, "title": row["title"], "url": row["url"],
            "source": row["src"], "diet": row["diet"] or "uncertain",
            "servings": row["servings"], "base": base_by.get(rid),
            "heroes": [], "ingredients": []})
        text = row["itext"] or row["raw"] or ""
        r["ingredients"].append({
            "text": text, "qty": row["qty"], "unit": row["unit"],
            "unitDisplay": grocery.DISPLAY_UNIT.get(row["unit"], ""),
            "canonical": row["canon"],
            "aisle": grocery._aisle(text, row["canon"] is not None)})
        if row["hero"] and row["canon"] and row["canon"] not in r["heroes"]:
            r["heroes"].append(row["canon"])

    return {
        "meta": {
            "months": planner.MONTHS_NL,
            "aisleOrder": grocery.AISLE_ORDER,
            "weekSize": config.WEEK_SIZE,
            "household": {"adults": config.HOUSEHOLD_ADULTS,
                          "kids": config.HOUSEHOLD_KIDS,
                          "kidPortion": config.KID_PORTION},
            "generated": datetime.now().strftime("%Y-%m-%d"),
            "nMains": len(recipes),
        },
        "seasonality": seasonality,
        "recipes": list(recipes.values()),
    }


def render_html(data: dict) -> str:
    return HTML_TEMPLATE.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description="Export a standalone cookbook.html.")
    ap.add_argument("-o", "--out", default=str(config.BASE_DIR / "cookbook.html"))
    args = ap.parse_args()
    conn = db.connect()
    db.init(conn)
    if not conn.execute("SELECT COUNT(*) c FROM seasonality").fetchone()["c"]:
        print("seasonality empty -- run `python load_velt.py` first.")
        return
    data = build_data(conn)
    if not data["recipes"]:
        print("no mains in the db -- run crawl.py first.")
        return
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render_html(data))
    print(f"wrote {args.out}  ({data['meta']['nMains']} mains, standalone, offline)")


# The single-file app. __DATA__ is replaced with the inlined JSON. All logic is
# vanilla JS; the Python classifiers already did the hard part (base/course/
# heroes/aisle are precomputed per recipe), so the browser only filters, selects,
# scales and sums.
HTML_TEMPLATE = r"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Seizoenskookboek</title>
<style>
  :root { --bg:#faf9f6; --card:#fff; --ink:#232019; --muted:#7a736a;
          --line:#e7e2d8; --accent:#4b7f52; --accent2:#b5651d; --chip:#eef2ec; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#1a1917; --card:#232120; --ink:#ece7dd; --muted:#a49b8d;
            --line:#332f2a; --accent:#7bb083; --accent2:#d98a45; --chip:#2b2a26; } }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
  header { padding:1.4rem 1rem .6rem; text-align:center; }
  h1 { margin:.2rem 0; font-size:1.5rem; }
  .sub { color:var(--muted); font-size:.85rem; }
  .controls { display:flex; flex-wrap:wrap; gap:.6rem; justify-content:center;
              align-items:end; padding:1rem; max-width:900px; margin:0 auto; }
  .controls label { display:flex; flex-direction:column; font-size:.72rem;
                    color:var(--muted); text-transform:uppercase; letter-spacing:.04em; gap:.25rem; }
  select, input, button { font:inherit; padding:.5rem .6rem; border-radius:8px;
                          border:1px solid var(--line); background:var(--card); color:var(--ink); }
  input[type=number] { width:4.5rem; }
  button.go { background:var(--accent); color:#fff; border:none; cursor:pointer;
              padding:.6rem 1.2rem; font-weight:600; }
  button.go:hover { filter:brightness(1.06); }
  main { max-width:900px; margin:0 auto; padding:0 1rem 3rem; }
  .wrap { display:grid; grid-template-columns:1fr; gap:1.4rem; }
  @media (min-width:760px){ .wrap { grid-template-columns:1.15fr .85fr; align-items:start; } }
  h2 { font-size:1.05rem; border-bottom:2px solid var(--line); padding-bottom:.3rem; }
  .dish { background:var(--card); border:1px solid var(--line); border-radius:12px;
          padding:.7rem .8rem; margin:.55rem 0; }
  .dish .top { display:flex; align-items:baseline; gap:.5rem; }
  .num { color:var(--muted); font-variant-numeric:tabular-nums; }
  .dish a { color:inherit; text-decoration:none; font-weight:600; }
  .dish a:hover { text-decoration:underline; }
  .meta { font-size:.8rem; color:var(--muted); margin-top:.25rem;
          display:flex; flex-wrap:wrap; gap:.4rem .8rem; align-items:center; }
  .chip { background:var(--chip); border-radius:20px; padding:.05rem .55rem; font-size:.72rem; }
  .chip.base { color:var(--accent); font-weight:600; }
  .chip.neutral { color:var(--accent2); }
  .reroll { margin-left:auto; cursor:pointer; border:none; background:none;
            color:var(--muted); font-size:.85rem; padding:.1rem .3rem; }
  .reroll:hover { color:var(--accent); }
  .aisle { margin:.9rem 0 .3rem; font-weight:600; color:var(--accent); font-size:.9rem; }
  ul.items { list-style:none; margin:0; padding:0; }
  ul.items li { display:flex; justify-content:space-between; gap:1rem;
                padding:.18rem 0; border-bottom:1px dashed var(--line); font-size:.92rem; }
  ul.items li .q { color:var(--muted); white-space:nowrap; }
  .note { color:var(--muted); font-size:.78rem; text-align:center; margin-top:2rem; }
  .short { color:var(--accent2); font-size:.85rem; }
</style>
</head>
<body>
<header>
  <h1>🥬 Seizoenskookboek</h1>
  <div class="sub" id="tagline"></div>
</header>

<div class="controls">
  <label>Maand<select id="month"></select></label>
  <label>Dieet<select id="diet">
    <option value="any">alles</option>
    <option value="vegetarian">vegetarisch</option>
    <option value="vegan">veganistisch</option>
  </select></label>
  <label>Onzeker<select id="uncertain">
    <option value="0">uitsluiten</option><option value="1">toestaan</option>
  </select></label>
  <label>Volw.<input type="number" id="adults" min="0" step="1"></label>
  <label>Kind.<input type="number" id="kids" min="0" step="1"></label>
  <button class="go" id="go">Genereer week</button>
</div>

<main>
  <div class="wrap">
    <section>
      <h2>Weekmenu <span id="wcount" class="short"></span></h2>
      <div id="week"></div>
    </section>
    <section>
      <h2>Boodschappenlijst</h2>
      <div id="grocery"></div>
    </section>
  </div>
  <div class="note" id="note"></div>
</main>

<script>
const DATA = /*__DATA__*/;
const M = DATA.meta, R = DATA.recipes, SEAS = DATA.seasonality;
const $ = id => document.getElementById(id);

function mulberry32(a){ return function(){ a|=0; a=a+0x6D2B79F5|0;
  let t=Math.imul(a^a>>>15,1|a); t=t+Math.imul(t^t>>>7,61|t)^t;
  return ((t^t>>>14)>>>0)/4294967296; }; }
const norm = s => (s||"").toLowerCase().replace(/\s+/g," ").trim();

function dietAllows(d, want, allowUnc){
  if(want==="any") return true;
  if(d==="uncertain") return allowUnc;
  if(want==="vegetarian") return d==="vegan"||d==="vegetarian";
  if(want==="vegan") return d==="vegan";
  return true;
}
function season(r, month){
  const withData = r.heroes.filter(h => SEAS[h]);
  if(withData.length===0) return {ok:true, inSeason:false};   // season-neutral
  const inSeason = withData.some(h => SEAS[h].includes(month));
  return {ok:inSeason, inSeason};                              // out-of-season hero dropped
}
function heroesUsedBy(r){ return new Set(r.heroes); }

function planWeek(month, diet, allowUnc, seed){
  const rng = mulberry32(seed);
  const pool = [];
  for(const r of R){
    if(!dietAllows(r.diet, diet, allowUnc)) continue;
    const s = season(r, month);
    if(!s.ok) continue;
    pool.push({r, inSeason:s.inSeason, key:[s.inSeason?1:0, rng()]});
  }
  pool.sort((a,b)=> b.key[0]-a.key[0] || b.key[1]-a.key[1]);
  const byBase = {};
  for(const p of pool){ (byBase[p.r.base||"_flex"] ||= []).push(p); }
  const order = Object.keys(byBase).filter(b=>b!=="_flex");
  order.sort((a,b)=> byBase[b][0].key[1]-byBase[a][0].key[1]);
  if(byBase["_flex"]) order.push("_flex");

  const chosen=[], usedIds=new Set(), usedHeroes=new Set();
  while(chosen.length < M.weekSize){
    let progressed=false;
    for(const b of order){
      if(chosen.length>=M.weekSize) break;
      let pick=null, fallback=null;
      for(const p of byBase[b]){
        if(usedIds.has(p.r.id)) continue;
        if(!fallback) fallback=p;
        if(![...heroesUsedBy(p.r)].some(h=>usedHeroes.has(h))){ pick=p; break; }
      }
      pick = pick||fallback;
      if(pick){ chosen.push(pick); usedIds.add(pick.r.id);
        pick.r.heroes.forEach(h=>usedHeroes.add(h)); progressed=true; }
    }
    if(!progressed) break;
  }
  return chosen;
}

function altFor(slot, week, month, diet, allowUnc){
  const inWeek = new Set(week.map(p=>p.r.id));
  const usedHeroes = new Set(); week.forEach(p=>{ if(p!==slot) p.r.heroes.forEach(h=>usedHeroes.add(h)); });
  const cands=[];
  for(const r of R){
    if(inWeek.has(r.id) || (r.base||"_flex")!==(slot.r.base||"_flex")) continue;
    if(!dietAllows(r.diet,diet,allowUnc)) continue;
    const s=season(r,month); if(!s.ok) continue;
    cands.push({r, inSeason:s.inSeason});
  }
  if(!cands.length) return null;
  cands.sort((a,b)=> (b.inSeason?1:0)-(a.inSeason?1:0));
  const fresh = cands.filter(c=>![...c.r.heroes].some(h=>usedHeroes.has(h)));
  return (fresh[0]||cands[0]);
}

function adultEquiv(){ return (+$("adults").value) + (+$("kids").value)*M.household.kidPortion; }
const fmtQ = n => { const r=Math.round(n*10)/10; return (r%1===0? r.toFixed(0): String(r)); };

function grocery(week){
  const ae = adultEquiv(), items={};
  for(const p of week){
    const scale = p.r.servings ? ae/p.r.servings : 1;
    for(const ing of p.r.ingredients){
      const key = ing.canonical || norm(ing.text);
      if(!key) continue;
      const it = items[key] ||= {label: ing.canonical||ing.text, aisle: ing.aisle,
                                 units:{}, toTaste:false};
      if(ing.qty==null) it.toTaste=true;
      else { const u=ing.unit||""; it.units[u]=(it.units[u]||0)+ing.qty*scale;
             it._ud ||= {}; it._ud[u]=ing.unitDisplay; }
    }
  }
  const byAisle={};
  for(const it of Object.values(items)){
    const parts=Object.entries(it.units).map(([u,q])=> u? `${fmtQ(q)} ${it._ud[u]||""}`.trim(): fmtQ(q));
    let q=parts.join(" + ");
    if(it.toTaste) q = q? q+" + naar smaak" : "naar smaak";
    (byAisle[it.aisle] ||= []).push({label:it.label, q});
  }
  for(const a in byAisle) byAisle[a].sort((x,y)=>x.label.localeCompare(y.label));
  return byAisle;
}

let WEEK=[];
function draw(){
  const month=+$("month").value, diet=$("diet").value, unc=$("uncertain").value==="1";
  const w=$("week"); w.innerHTML="";
  WEEK.forEach((p,i)=>{
    const d=document.createElement("div"); d.className="dish";
    const scale = p.r.servings? (adultEquiv()/p.r.servings):1;
    const heroes = p.r.heroes.length? p.r.heroes.join(", ") : "geen seizoensgroente";
    const tag = p.inSeason? '<span class="chip">in seizoen</span>'
                          : '<span class="chip neutral">seizoensneutraal</span>';
    d.innerHTML =
      `<div class="top"><span class="num">${i+1}.</span>`+
      `<a href="${p.r.url}" target="_blank" rel="noopener">${esc(p.r.title||"")}</a>`+
      `<button class="reroll" title="vervang">↻</button></div>`+
      `<div class="meta"><span class="chip base">${p.r.base||"vrij"}</span>${tag}`+
      `<span>hero: ${esc(heroes)}</span><span>${dietNL(p.r.diet)}</span>`+
      `<span>×${fmtQ(scale)} (${p.r.servings}p)</span></div>`;
    d.querySelector(".reroll").onclick=()=>{
      const alt=altFor(p,WEEK,month,diet,unc);
      if(alt){ WEEK[i]=alt; draw(); }
    };
    w.appendChild(d);
  });
  $("wcount").textContent = WEEK.length<M.weekSize ? `(${WEEK.length}/${M.weekSize} — meer recepten nodig)` : "";
  drawGrocery();
}
function drawGrocery(){
  const g=grocery(WEEK), box=$("grocery"); box.innerHTML="";
  for(const aisle of M.aisleOrder){
    const rows=g[aisle]; if(!rows||!rows.length) continue;
    const h=document.createElement("div"); h.className="aisle"; h.textContent=aisle; box.appendChild(h);
    const ul=document.createElement("ul"); ul.className="items";
    rows.forEach(it=>{ const li=document.createElement("li");
      li.innerHTML=`<span>${esc(it.label)}</span><span class="q">${esc(it.q)}</span>`; ul.appendChild(li); });
    box.appendChild(ul);
  }
}
const esc = s => (s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const dietNL = d => ({vegan:"veganistisch",vegetarian:"vegetarisch",omnivore:"met vlees/vis",uncertain:"onzeker"}[d]||d);

let SEED=1;
function generate(){
  const month=+$("month").value, diet=$("diet").value, unc=$("uncertain").value==="1";
  WEEK=planWeek(month, diet, unc, SEED++);
  draw();
}

// init
(function(){
  const ms=$("month");
  const now=new Date().getMonth()+1;
  for(let m=1;m<=12;m++){ const o=document.createElement("option");
    o.value=m; o.textContent=M.months[m]; if(m===now)o.selected=true; ms.appendChild(o); }
  $("adults").value=M.household.adults; $("kids").value=M.household.kids;
  $("tagline").textContent=`${M.nMains} hoofdgerechten · Belgisch · Velt-seizoenskalender`;
  $("note").innerHTML=`Gegenereerd ${M.generated}. Volledig offline. `+
    `Seizoensdata is binair (Velt), dus de strengheid-instelling is nog inactief. `+
    `Recepten linken naar de bron; hier staan alleen feiten, geen bereidingen.`;
  $("go").onclick=generate;
  // month/diet/uncertain change the pool -> re-plan; household only rescales
  ["month","diet","uncertain"].forEach(id=>$(id).addEventListener("change",generate));
  ["adults","kids"].forEach(id=>$(id).addEventListener("change",()=>{ if(WEEK.length) draw(); }));
  generate();
})();
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
