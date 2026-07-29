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
from classify import AROMATICS
from matching import tokens, hit

# Dishes that absorb many/variable vegetables -- the "restjesdag" (scraps day)
# candidates. Title-matched, so it's a fact about the dish, not a guess.
FLEX_TITLE = {
    "traybake", "ovenschotel", "ovenschaal", "ovengerecht", "ovenrooster",
    "roerbak", "gewokte", "wok", "soep", "curry", "frittata", "quiche",
    "stoofpot", "stoofpotje", "stoverij", "eenpans", "hutspot", "stamppot",
    "stoemp", "ratatouille", "shakshuka", "gratin", "tajine", "ovenschotels",
}


def is_flexible(title: str) -> bool:
    return hit(tokens(title or ""), FLEX_TITLE)


def build_data(conn, include_instructions=True) -> dict:
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
        "SELECT r.id rid, r.title, r.url, r.diet, r.cuisine, r.servings, "
        "r.instructions instr, "
        "s.name src, ri.ingredient_text itext, ri.raw_text raw, ri.qty, ri.unit, "
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
            "cuisine": row["cuisine"] or "onbekend",
            "servings": row["servings"], "base": base_by.get(rid),
            "flexible": is_flexible(row["title"]),
            # method prose, personal/household use only (see decisions.md #8)
            "instructions": (row["instr"] if include_instructions else None),
            "heroes": [], "produce": set(), "ingredients": []})
        text = row["itext"] or row["raw"] or ""
        r["ingredients"].append({
            "text": text, "qty": row["qty"], "unit": row["unit"],
            "unitDisplay": grocery.DISPLAY_UNIT.get(row["unit"], ""),
            "canonical": row["canon"],
            "aisle": grocery._aisle(text, row["canon"] is not None)})
        if row["canon"] and row["canon"] not in AROMATICS:
            r["produce"].add(row["canon"])       # for waste/overlap (not aromatics)
        if row["hero"] and row["canon"] and row["canon"] not in r["heroes"]:
            r["heroes"].append(row["canon"])

    for r in recipes.values():
        r["produce"] = sorted(r["produce"])       # set -> JSON-safe list

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
    ap.add_argument("--no-instructions", action="store_true",
                    help="omit method prose -> a shareable, facts-only file.")
    args = ap.parse_args()
    conn = db.connect()
    db.init(conn)
    if not conn.execute("SELECT COUNT(*) c FROM seasonality").fetchone()["c"]:
        print("seasonality empty -- run `python load_velt.py` first.")
        return
    data = build_data(conn, include_instructions=not args.no_instructions)
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
  button.go.ghost { background:transparent; color:var(--accent);
                    border:1px solid var(--accent); }
  main { max-width:900px; margin:0 auto; padding:0 1rem 3rem; }
  .wrap { display:grid; grid-template-columns:1fr; gap:1.4rem; }
  @media (min-width:760px){ .wrap { grid-template-columns:1.15fr .85fr; align-items:start; } }
  h2 { font-size:1.05rem; border-bottom:2px solid var(--line); padding-bottom:.3rem; }
  .dish { background:var(--card); border:1px solid var(--line); border-radius:12px;
          padding:.7rem .8rem; margin:.55rem 0; }
  .dish.locked { border-color:var(--accent); box-shadow:inset 3px 0 0 var(--accent); }
  .dish.scraps { border-color:var(--accent2); }
  .chip.scraps { color:var(--accent2); font-weight:600; }
  .scrapline { margin-top:.3rem; font-size:.8rem; color:var(--accent2); }
  details.recept { margin-top:.5rem; border-top:1px dashed var(--line); padding-top:.4rem; }
  details.recept summary { cursor:pointer; color:var(--accent); font-size:.85rem;
                           font-weight:600; list-style:none; }
  details.recept summary::-webkit-details-marker { display:none; }
  details.recept summary:before { content:"▸ "; }
  details.recept[open] summary:before { content:"▾ "; }
  details.recept ul.ing { margin:.5rem 0; padding-left:1.1rem; font-size:.9rem; }
  details.recept .method p { margin:.45rem 0; font-size:.92rem; }
  details.recept .bron { font-size:.78rem; margin-top:.4rem; }
  details.recept .bron a { color:var(--muted); }
  .dish .top { display:flex; align-items:baseline; gap:.5rem; }
  .num { color:var(--muted); font-variant-numeric:tabular-nums; }
  .dish a { color:inherit; text-decoration:none; font-weight:600; }
  .dish a:hover { text-decoration:underline; }
  .slotbtn { cursor:pointer; border:none; background:none; font-size:.95rem;
             padding:.1rem .3rem; color:var(--muted); }
  .slotbtn:hover { color:var(--accent); }
  .slotbtn.lock.on { color:var(--accent); }
  .hint { color:var(--accent2); font-size:.82rem; margin:.3rem 0 .6rem; }
  .meta { font-size:.8rem; color:var(--muted); margin-top:.25rem;
          display:flex; flex-wrap:wrap; gap:.4rem .8rem; align-items:center; }
  .chip { background:var(--chip); border-radius:20px; padding:.05rem .55rem; font-size:.72rem; }
  .chip.base { color:var(--accent); font-weight:600; }
  .chip.neutral { color:var(--accent2); }
  .chip.cuisine { color:var(--accent2); font-weight:600; }
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
  <label>Keuken<select id="cuisine"><option value="any">alles</option></select></label>
  <label>Onzeker<select id="uncertain">
    <option value="0">uitsluiten</option><option value="1">toestaan</option>
  </select></label>
  <label>Minder seizoensgebonden<select id="relax">
    <option value="0">nee</option><option value="1">ja, om aan te vullen</option>
  </select></label>
  <label>Restjesdag<select id="restjes">
    <option value="0">nee</option><option value="1">ja, traybake met restjes</option>
  </select></label>
  <label>Volw.<input type="number" id="adults" min="0" step="1"></label>
  <label>Kind.<input type="number" id="kids" min="0" step="1"></label>
  <button class="go" id="newweek">Nieuwe week</button>
  <button class="go ghost" id="refresh" title="behoud vergrendelde gerechten">Vernieuw open plekken</button>
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

// --- foundation -----------------------------------------------------------
// A week is M.weekSize slots. Each slot is {r, inSeason, locked}. Every action
// only ever refills OPEN (unlocked) slots; the toggles just widen or re-rank the
// candidate pool. Locked dishes stay put AND their bases/heroes still count
// toward variety, so refills complement them.
let WEEK = [], SEED = 1;

function mulberry32(a){ return function(){ a|=0; a=a+0x6D2B79F5|0;
  let t=Math.imul(a^a>>>15,1|a); t=t+Math.imul(t^t>>>7,61|t)^t;
  return ((t^t>>>14)>>>0)/4294967296; }; }
const norm = s => (s||"").toLowerCase().replace(/\s+/g," ").trim();
const cmp = (a,b) => { for(let i=0;i<a.length;i++){ if(a[i]!==b[i]) return a[i]<b[i]?-1:1; } return 0; };

function dietAllows(d, want, unc){
  if(want==="any") return true;
  if(d==="uncertain") return unc;
  if(want==="vegetarian") return d==="vegan"||d==="vegetarian";
  if(want==="vegan") return d==="vegan";
  return true;
}
function season(r, month){
  const withData = r.heroes.filter(h => SEAS[h]);
  const neutral = withData.length===0;                        // no produce w/ a season
  const inSeason = !neutral && withData.some(h => SEAS[h].includes(month));
  return {neutral, inSeason, ok: neutral||inSeason};
}
// tier: 2 in-season > 1 neutral > 0 out-of-season(only when 'relax') ; -1 excluded
function tierOf(s, relax){ return s.inSeason?2 : s.neutral?1 : (relax?0:-1); }
const opts = () => ({ month:+$("month").value, diet:$("diet").value,
  cuisine:$("cuisine").value,
  unc:$("uncertain").value==="1", relax:$("relax").value==="1",
  restjes:$("restjes").value==="1" });

function rankedPool(usedIds, o, rng){
  const pool=[];
  for(const r of R){
    if(usedIds.has(r.id) || !dietAllows(r.diet,o.diet,o.unc)) continue;
    if(o.cuisine!=="any" && r.cuisine!==o.cuisine) continue;
    const s=season(r,o.month), t=tierOf(s,o.relax);
    if(t<0) continue;
    pool.push({r, inSeason:s.inSeason, tier:t, rnd:rng()});
  }
  return pool;
}
// best candidate: prefer an under-used base, then higher season tier, then no
// repeated hero, then REUSE of produce already bought this week (less waste),
// then the seeded random.
function pickNext(pool, usedIds, usedHeroes, baseCount, usedProduce){
  let best=null;
  for(const c of pool){
    if(usedIds.has(c.r.id)) continue;
    const b=c.r.base||"_flex", clash=c.r.heroes.some(h=>usedHeroes.has(h))?1:0;
    const overlap=c.r.produce.reduce((n,p)=> n+(usedProduce.has(p)?1:0), 0);
    const score=[-(baseCount[b]||0), c.tier, -clash, overlap, c.rnd];
    if(!best || cmp(score,best.score)>0) best={c,score};
  }
  return best ? best.c : null;
}

function acct(s, usedIds, usedHeroes, usedProduce, baseCount){
  usedIds.add(s.r.id); s.r.heroes.forEach(h=>usedHeroes.add(h));
  s.r.produce.forEach(p=>usedProduce.add(p));
  const b=s.r.base||"_flex"; baseCount[b]=(baseCount[b]||0)+1;
}
function refillOpen(){
  const o=opts();
  const slots=[]; for(let i=0;i<M.weekSize;i++) slots.push(WEEK[i] && WEEK[i].locked ? WEEK[i] : null);
  const usedIds=new Set(), usedHeroes=new Set(), usedProduce=new Set(), baseCount={};
  slots.forEach(s=>{ if(s) acct(s, usedIds, usedHeroes, usedProduce, baseCount); });
  const pool=rankedPool(usedIds, o, mulberry32(SEED++));

  // Restjesdag: reserve the last open slot for a flexible (traybake/one-pot)
  // dish, unless we already have one.
  if(o.restjes && !slots.some(s=>s && s.r.flexible)){
    let idx=-1; for(let i=slots.length-1;i>=0;i--){ if(!slots[i]){ idx=i; break; } }
    if(idx>=0){
      const fp=pickNext(pool.filter(c=>c.r.flexible), usedIds, usedHeroes, baseCount, usedProduce);
      if(fp){ slots[idx]={r:fp.r, inSeason:fp.inSeason, locked:false, scraps:true};
        acct(slots[idx], usedIds, usedHeroes, usedProduce, baseCount); }
    }
  }
  for(let i=0;i<slots.length;i++){
    if(slots[i]) continue;
    const p=pickNext(pool, usedIds, usedHeroes, baseCount, usedProduce);
    if(!p) continue;
    slots[i]={r:p.r, inSeason:p.inSeason, locked:false};
    acct(slots[i], usedIds, usedHeroes, usedProduce, baseCount);
  }
  WEEK=slots.filter(Boolean);
  draw();
}
function newWeek(){ WEEK=[]; refillOpen(); }
function toggleLock(i){ WEEK[i].locked=!WEEK[i].locked; draw(); }
function replaceOne(i){                                        // swap a single open dish
  const o=opts(), others=new Set(), usedHeroes=new Set(), usedProduce=new Set(), baseCount={};
  WEEK.forEach((s,j)=>{ if(j!==i) acct(s, others, usedHeroes, usedProduce, baseCount); });
  const pool=rankedPool(others, o, mulberry32(SEED++));
  const p=pickNext(pool, others, usedHeroes, baseCount, usedProduce);
  if(p){ WEEK[i]={r:p.r, inSeason:p.inSeason, locked:false}; draw(); }
}

// --- grocery + render -----------------------------------------------------
const adultEquiv = () => (+$("adults").value) + (+$("kids").value)*M.household.kidPortion;
const fmtQ = n => { const r=Math.round(n*10)/10; return r%1===0 ? r.toFixed(0) : String(r); };
const esc = s => (s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const dietNL = d => ({vegan:"veganistisch",vegetarian:"vegetarisch",omnivore:"met vlees/vis",uncertain:"onzeker"}[d]||d);
const cuisineNL = c => ({belgian:"Belgisch","western-vegan":"Vegan (westers)",indian:"Indiaas",chinese:"Chinees",greek:"Grieks",onbekend:"onbekend"}[c]||c);
// full ingredient list + method, collapsed. Only when instructions were exported.
function recept(r){
  const ings = r.ingredients.map(ing=>{
    const q = ing.qty==null ? "" : `${fmtQ(ing.qty)} ${ing.unitDisplay||""} `.replace(/\s+/g," ");
    return `<li>${esc(q)}${esc(ing.text)}</li>`; }).join("");
  const steps = (r.instructions||"").split(/\n+/).filter(s=>s.trim())
    .map(s=>`<p>${esc(s)}</p>`).join("");
  const method = steps ? `<div class="method">${steps}</div>` : "";
  if(!r.instructions && !ings) return "";
  return `<details class="recept"><summary>Recept</summary>`+
    `<ul class="ing">${ings}</ul>${method}`+
    `<div class="bron"><a href="${esc(r.url)}" target="_blank" rel="noopener">bron: ${esc(r.source||"")}</a></div>`+
    `</details>`;
}

function grocery(week){
  const ae=adultEquiv(), items={};
  for(const p of week){
    const scale = p.r.servings ? ae/p.r.servings : 1;
    for(const ing of p.r.ingredients){
      const key = ing.canonical || norm(ing.text); if(!key) continue;
      const it = items[key] ||= {label: ing.canonical||ing.text, aisle: ing.aisle, units:{}, ud:{}, toTaste:false};
      if(ing.qty==null) it.toTaste=true;
      else { const u=ing.unit||""; it.units[u]=(it.units[u]||0)+ing.qty*scale; it.ud[u]=ing.unitDisplay; }
    }
  }
  const byAisle={};
  for(const it of Object.values(items)){
    const parts=Object.entries(it.units).map(([u,q])=> u? `${fmtQ(q)} ${it.ud[u]||""}`.trim() : fmtQ(q));
    let q=parts.join(" + "); if(it.toTaste) q = q? q+" + naar smaak" : "naar smaak";
    (byAisle[it.aisle] ||= []).push({label:it.label, q});
  }
  for(const a in byAisle) byAisle[a].sort((x,y)=>x.label.localeCompare(y.label));
  return byAisle;
}

function draw(){
  const w=$("week"); w.innerHTML="";
  const open = M.weekSize - WEEK.length;
  if(open>0 && $("relax").value!=="1"){
    const h=document.createElement("div"); h.className="hint";
    h.textContent = `${open} plek(ken) niet ingevuld voor deze maand — zet "minder seizoensgebonden" op "ja" om aan te vullen.`;
    w.appendChild(h);
  }
  // produce that appears in only ONE dish this week -> the fractions most likely
  // to go to waste (aromatics excluded from r.produce already).
  const pc={}; WEEK.forEach(s=> s.r.produce.forEach(p=> pc[p]=(pc[p]||0)+1));
  const singles = Object.keys(pc).filter(p=>pc[p]===1).sort();
  const hasScraps = WEEK.some(s=>s.scraps);
  if(!hasScraps && singles.length>=4){
    const h=document.createElement("div"); h.className="hint";
    h.textContent = `${singles.length} groenten komen in maar één gerecht voor (kans op restjes) — zet Restjesdag aan.`;
    w.appendChild(h);
  }
  WEEK.forEach((p,i)=>{
    const d=document.createElement("div"); d.className="dish"+(p.locked?" locked":"")+(p.scraps?" scraps":"");
    const scale = p.r.servings ? adultEquiv()/p.r.servings : 1;
    const heroes = p.r.heroes.length ? p.r.heroes.join(", ") : "geen seizoensgroente";
    const tag = p.inSeason ? '<span class="chip">in seizoen</span>'
                           : '<span class="chip neutral">seizoensneutraal</span>';
    const scrapsChip = p.scraps ? '<span class="chip scraps">♻ restjesdag</span>' : "";
    const lockBtn = `<button class="slotbtn lock ${p.locked?'on':''}" title="${p.locked?'ontgrendel':'behoud'}">${p.locked?'🔒':'🔓'}</button>`;
    const repl = p.locked ? "" : `<button class="slotbtn replace" title="vervang">↻</button>`;
    const scrapsLine = p.scraps && singles.length ?
      `<div class="scrapline">restjes hier: ${esc(singles.join(", "))}</div>` : "";
    d.innerHTML =
      `<div class="top"><span class="num">${i+1}.</span>`+
      `<a href="${esc(p.r.url)}" target="_blank" rel="noopener">${esc(p.r.title||"")}</a>`+
      `<span style="margin-left:auto">${lockBtn}${repl}</span></div>`+
      `<div class="meta"><span class="chip base">${esc(p.r.base||"vrij")}</span>${scrapsChip}${tag}`+
      `<span>hero: ${esc(heroes)}</span><span>${dietNL(p.r.diet)}</span>`+
      `<span class="chip cuisine">${esc(cuisineNL(p.r.cuisine))}</span>`+
      `<span>×${fmtQ(scale)} (${p.r.servings}p)</span></div>`+ scrapsLine + recept(p.r);
    d.querySelector(".lock").onclick=()=>toggleLock(i);
    const rb=d.querySelector(".replace"); if(rb) rb.onclick=()=>replaceOne(i);
    w.appendChild(d);
  });
  $("wcount").textContent = WEEK.length<M.weekSize ? `(${WEEK.length}/${M.weekSize})` : "";
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

// --- init -----------------------------------------------------------------
(function(){
  const ms=$("month"), now=new Date().getMonth()+1;
  for(let m=1;m<=12;m++){ const o=document.createElement("option");
    o.value=m; o.textContent=M.months[m]; if(m===now)o.selected=true; ms.appendChild(o); }
  // Cuisine filter: only offer the cuisines actually present, most-common first.
  const cCount={}; R.forEach(r=>{ cCount[r.cuisine]=(cCount[r.cuisine]||0)+1; });
  const cs=$("cuisine");
  Object.keys(cCount).sort((a,b)=>cCount[b]-cCount[a]).forEach(c=>{
    const o=document.createElement("option");
    o.value=c; o.textContent=`${cuisineNL(c)} (${cCount[c]})`; cs.appendChild(o); });
  $("adults").value=M.household.adults; $("kids").value=M.household.kids;
  const nCuis=Object.keys(cCount).length;
  $("tagline").textContent=`${M.nMains} hoofdgerechten · `+
    `${nCuis>1?nCuis+" keukens":"Belgisch"} · Velt-seizoenskalender`;
  $("note").innerHTML=`Gegenereerd ${M.generated}. Volledig offline, voor eigen huishoudelijk gebruik. `+
    `Vergrendel (🔒) gerechten die je wilt houden en klik "Vernieuw open plekken". `+
    `Klik "Recept" voor de volledige bereiding. Seizoensdata is binair (Velt).`;
  $("newweek").onclick=newWeek;
  $("refresh").onclick=refillOpen;
  // month/diet/uncertain change the pool fundamentally -> fresh week;
  // relax refills only the OPEN slots (keeps your locked picks);
  // household size only rescales.
  ["month","diet","cuisine","uncertain"].forEach(id=>$(id).addEventListener("change",newWeek));
  ["relax","restjes"].forEach(id=>$(id).addEventListener("change",refillOpen));
  ["adults","kids"].forEach(id=>$(id).addEventListener("change",()=>{ if(WEEK.length) draw(); }));
  newWeek();
})();
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
