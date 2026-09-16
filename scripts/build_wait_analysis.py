#!/usr/bin/env python3
"""The 125-day wait — a standalone analysis page.

    python3 scripts/build_wait_analysis.py     # -> site/125-day-wait.html

Batch 49 reached B=10.00 (all ten chapters drawn) on 2026-02-24 and did not go
on sale until 2026-06-29.  V13 uses that 125-day interval as an additive
scheduling floor (docs/model.md, docs/v13_review.md), so it is worth showing
exactly what the production record does and does not say about it.

The page regenerates from `data/processed/` rather than being a frozen copy, so
a correction to the event table flows through.  It is deliberately self-contained
— one file, no build step, no assets — so it can be linked or archived on its own.
Unlike the site's own charts it carries a hover layer, which is the point of it:
the readiness value at any date is the thing being argued about.

Kept out of build_site.py on purpose: this is a one-off argument about a closed
window, not part of the recurring forecast page.
"""
import csv
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
D_ = lambda *p: os.path.join(HERE, "..", *p)
sys.path.insert(0, HERE)

from build_level2 import load as load_l2
from build_readiness import ordered_trace

WINDOW = ("2026-02-24", "2026-06-29")
TARGET_BATCH, NEXT_BATCH = 49, 50
STAGE_LABEL = {
    "manuscript_complete": "manuscript complete", "bg_spec": "background spec",
    "character_inking": "character inking", "dialogue": "dialogue",
    "bg_work": "background work", "panel_layout": "panel layout",
}


def collect():
    ev, batch, pos, start, cur, last = load_l2()
    chapters = lambda h: sorted(c for c, b in batch.items() if b == h)[:10]
    end = max(date.fromisoformat(r["event_date"]) for r in ev if r.get("event_date"))

    def trace(h):
        return [[d.isoformat(), round(b, 3)]
                for d, b, _ in ordered_trace(ev, chapters(h), end)]

    def completed_on(h):
        for d, b, _ in ordered_trace(ev, chapters(h), date(2099, 1, 1)):
            if b >= 9.999:
                return d
        return None

    def readiness_at(h, when):
        tr = ordered_trace(ev, chapters(h), when)
        return round(tr[-1][1], 2) if tr else 0.0

    events = []
    for row in sorted(ev, key=lambda r: (r.get("event_date") or "", r.get("chapter") or "")):
        when = row.get("event_date")
        if not when or not (WINDOW[0] <= when <= WINDOW[1]):
            continue
        ch = row.get("chapter")
        events.append({"date": when,
                       "chapter": int(float(ch)) if ch else None,
                       "stage": STAGE_LABEL.get(row.get("stage") or "",
                                                row.get("event_class") or "")})

    pubs = []
    with open(D_("data", "processed", "chapters.csv"), encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            ch = int(row["chapter"])
            if ch in chapters(TARGET_BATCH) and row.get("publication_date_jp"):
                pubs.append({"chapter": ch, "date": row["publication_date_jp"]})
    pubs.sort(key=lambda r: r["chapter"])

    # Every run with a production record, so "is 125 days normal" is answerable.
    compare = []
    for h in sorted(set(batch.values())):
        done = completed_on(h)
        if not done or h not in start or not chapters(h):
            continue
        compare.append({"batch": h, "complete": done.isoformat(),
                        "publish": start[h].isoformat(),
                        "wait": (start[h] - done).days,
                        "next_B_at_publish": readiness_at(h + 1, start[h])})

    w0, w1 = (date.fromisoformat(x) for x in WINDOW)
    return {
        "b49": trace(TARGET_BATCH), "b50": trace(NEXT_BATCH),
        "window": list(WINDOW), "chapter_pubs": pubs, "events": events,
        "compare": compare,
        "b50_at_w0": readiness_at(NEXT_BATCH, w0),
        "b50_at_w1": readiness_at(NEXT_BATCH, w1),
        "wait_days": (w1 - w0).days,
        "generated": date.today().isoformat(),
    }


TEMPLATE = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="Batch 49 of Hunter x Hunter was finished on 24 February 2026 and went on sale on 29 June. What the production record shows in between.">
<title>The 125-Day Wait</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap">
<style>
*,*::before,*::after{box-sizing:border-box}
html{color-scheme:light dark}
body{margin:0}
img{max-width:100%}
[hidden]{display:none!important}
:root{
  --surface:#fcfcfb; --panel:#ffffff; --ground:#f3f4f2;
  --ink:#0b0b0b; --ink-2:#52514e; --ink-3:#83827d;
  --rule:#e2e3df; --band:#efece1; --band-edge:#c4c0ad;
  --s49:#1baf7a; --s50:#eb6834; --pub:#52514e;
  --sans:"IBM Plex Sans",system-ui,-apple-system,sans-serif;
  --serif:"Newsreader",Georgia,serif;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --surface:#1a1a19; --panel:#21211f; --ground:#141413;
  --ink:#ffffff; --ink-2:#c3c2b7; --ink-3:#8f8e85;
  --rule:#32322e; --band:#302f24; --band-edge:#57554494;
  --s49:#199e70; --s50:#d95926; --pub:#c3c2b7;
}}
:root[data-theme="dark"]{
  --surface:#1a1a19; --panel:#21211f; --ground:#141413;
  --ink:#ffffff; --ink-2:#c3c2b7; --ink-3:#8f8e85;
  --rule:#32322e; --band:#302f24; --band-edge:#57554494;
  --s49:#199e70; --s50:#d95926; --pub:#c3c2b7;
}
body{background:var(--surface);color:var(--ink);font-family:var(--serif);font-size:17px;line-height:1.6}
.wrap{max-width:60rem;margin:0 auto;padding-inline:20px;padding-block:2.6rem 4rem}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.11em;text-transform:uppercase;color:var(--ink-3);margin:0}
h1{font-family:var(--sans);font-weight:600;font-size:clamp(1.9rem,5.2vw,2.5rem);line-height:1.12;letter-spacing:-.02em;text-wrap:balance;margin:.5rem 0 0}
.stand{font-size:1.12rem;color:var(--ink-2);max-width:40rem;margin:.85rem 0 0}
h2{font-family:var(--sans);font-weight:600;font-size:1.3rem;letter-spacing:-.01em;text-wrap:balance;margin:3rem 0 .5rem}
h3{font-family:var(--sans);font-weight:600;font-size:.95rem;margin:2rem 0 .6rem}
p{margin:0 0 1rem;max-width:42rem}
code{font-family:var(--mono);font-size:.86em;color:var(--ink-2)}
strong{font-weight:500;font-variant-numeric:tabular-nums}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(9.5rem,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);margin:1.8rem 0 0}
.tile{background:var(--panel);padding:.9rem 1rem}
.tile .k{font-family:var(--mono);font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-3);display:block;margin-bottom:.35rem}
.tile .v{font-family:var(--sans);font-weight:600;font-size:1.45rem;letter-spacing:-.02em;font-variant-numeric:tabular-nums;display:block;line-height:1.1}
.tile .s{font-family:var(--mono);font-size:11px;color:var(--ink-2);display:block;margin-top:.25rem}
.legend{display:flex;flex-wrap:wrap;gap:.35rem 1.3rem;font-family:var(--sans);font-size:.85rem;color:var(--ink-2);margin:.2rem 0 .7rem;align-items:center}
.legend span{display:inline-flex;align-items:center;gap:.4rem}
.legend i{width:16px;height:3px;border-radius:2px;display:inline-block}
.legend i.tick{width:2px;height:13px;border-radius:1px}
.legend i.bandkey{width:16px;height:12px;border-radius:2px;background:var(--band);border:1px solid var(--band-edge)}
.chart-shell{display:flex;background:var(--panel);border:1px solid var(--rule);position:relative}
.yaxis{flex:none;width:52px;border-right:1px solid var(--rule);background:var(--panel);position:relative;z-index:2}
.scroller{overflow-x:auto;overflow-y:hidden;flex:1;position:relative}
.scroller svg{display:block}
.hint{font-family:var(--mono);font-size:11px;color:var(--ink-3);margin:.5rem 0 0}
.tip{position:absolute;pointer-events:none;background:var(--panel);border:1px solid var(--rule);padding:.5rem .6rem;font-family:var(--mono);font-size:11.5px;line-height:1.55;color:var(--ink);box-shadow:0 2px 10px rgba(0,0,0,.12);white-space:nowrap;z-index:5;opacity:0;transition:opacity .1s}
.tip b{font-weight:500}
.tip .r{display:flex;gap:.45rem;align-items:center}
.tip .r i{width:9px;height:9px;border-radius:50%;flex:none}
table{border-collapse:collapse;width:100%;font-family:var(--mono);font-size:12.5px;font-variant-numeric:tabular-nums;margin-top:.4rem}
caption{caption-side:top;text-align:left;font-family:var(--sans);font-size:.83rem;color:var(--ink-2);padding-bottom:.55rem}
th,td{text-align:right;padding:.4rem .65rem;border-bottom:1px solid var(--rule)}
th:first-child,td:first-child{text-align:left;padding-left:0}
th:last-child,td:last-child{padding-right:0}
thead th{font-weight:500;color:var(--ink-3);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;border-bottom-color:var(--ink-2)}
tbody tr:last-child td{border-bottom:none}
.scroll{overflow-x:auto}
details{margin:1.4rem 0 0;border-top:1px solid var(--rule);padding-top:.8rem}
summary{font-family:var(--sans);font-size:.88rem;color:var(--ink-2);cursor:pointer}
summary:focus-visible{outline:2px solid var(--s50);outline-offset:3px}
.caveat{background:var(--ground);border-left:3px solid var(--band-edge);padding:.9rem 1.1rem;font-family:var(--sans);font-size:.94rem;line-height:1.55;margin:1.5rem 0 0}
.caveat b{font-weight:600}
@media (max-width:560px){.yaxis{width:42px}}
</style>
</head>
<body>

<div class="wrap">
  <p class="eyebrow">Hunter &times; Hunter &middot; batch 49 &middot; production record</p>
  <h1>The 125-Day Wait</h1>
  <p class="stand">Batch 49 was finished on 24 February 2026 and did not appear in Weekly Sh&#333;nen Jump until 29 June. Here is what the production record shows happening in between.</p>

  <div class="tiles">
    <div class="tile"><span class="k">Batch 49 complete</span><span class="v">Feb 24</span><span class="s">B = 10.00 of 10</span></div>
    <div class="tile"><span class="k">First chapter on sale</span><span class="v">Jun 29</span><span class="s">125 days later</span></div>
    <div class="tile"><span class="k">Batch 50 progress</span><span class="v">+1.90</span><span class="s">4.30 &rarr; 6.20</span></div>
    <div class="tile"><span class="k">Reports in window</span><span class="v">14</span><span class="s">13 on later batches</span></div>
  </div>

  <h2>Readiness against real dates</h2>
  <div class="legend" id="legend">
    <span><i style="background:var(--s49)"></i>Batch 49 &mdash; ch. 411&ndash;420</span>
    <span><i style="background:var(--s50)"></i>Batch 50 &mdash; ch. 421&ndash;430</span>
    <span><i class="tick" style="background:var(--pub)"></i>Weekly chapter on sale</span>
    <span><i class="bandkey"></i>The 125-day wait</span>
  </div>
  <div class="chart-shell">
    <div class="yaxis"><svg id="yax" role="presentation"></svg></div>
    <div class="scroller" id="scroller">
      <svg id="plot" role="img" aria-label="Reported production readiness of Hunter x Hunter batches 49 and 50 against calendar dates, June 2024 to September 2026, with the 125-day wait between batch 49 completion and publication highlighted"></svg>
    </div>
    <div class="tip" id="tip" hidden></div>
  </div>
  <p class="hint">Scroll the panel sideways &middot; 0&ndash;10 is ordered chapter-equivalents complete, so 10.00 means all ten chapters finished</p>

  <h2>What the wait was spent on</h2>
  <p>Batch 49&rsquo;s line is flat across the whole window: there was nothing left to report, because every one of its ten chapters was already finished. The work in those 125 days went to <em>batch 50</em>, which climbed from 4.30 to 6.20 chapter-equivalents on thirteen separate reports.</p>
  <p>One of those matters more than the rest. Chapter 421 &mdash; the first chapter of the <em>next</em> batch &mdash; reached manuscript complete on <strong>26 May 2026</strong>, thirty-four days before batch 49 went on sale. So at the moment Shueisha started serializing batch 49, it was holding a finished batch plus six chapters of the batch after it, with the next batch&rsquo;s opener already in hand.</p>

  <div class="scroll"><table>
    <caption>Every production report inside the window, 24 February &ndash; 29 June 2026.</caption>
    <thead><tr><th>Date</th><th>Chapter</th><th>Batch</th><th>Reported</th></tr></thead>
    <tbody id="evrows"></tbody>
  </table></div>

  <h2>Is 125 days normal? No &mdash; it is the only one</h2>
  <p>The two earlier batches with production records did the opposite. Both began serializing <em>before</em> their last chapter was drawn: batch 47 by 29 days, batch 48 by 40. Batch 49 is the first run that was finished and then held.</p>
  <div class="scroll"><svg id="cmp" role="img" aria-label="Days between a batch becoming complete and going on sale: batch 47 published 29 days early, batch 48 40 days early, batch 49 waited 125 days"></svg></div>
  <p>That is why the 125 days is a strange number to build a forecast on. It is not a standing scheduling lag that every batch pays &mdash; it is a single decision, made once, about a batch that happened to be ready early.</p>

  <div class="caveat">
    <b>One caveat on reading the buffer figures.</b> Readiness here is <em>reported</em> progress, and Togashi has been posting more often and in more detail with each run. The buffer the next batch had at publication rises across the three cases &mdash; 1.61, then 5.00, then 6.20 &mdash; but part of that rise may be better reporting rather than more finished pages. The sign flip is the robust part: publishing before completion versus after it does not depend on how granular the reports are.
  </div>

  <details>
    <summary>Series data &mdash; every reported readiness change</summary>
    <div class="scroll"><table>
      <caption>Ordered readiness B(t) on the 0&ndash;10 scale, as reported.</caption>
      <thead><tr><th>Date</th><th>Batch 49</th><th>Batch 50</th></tr></thead>
      <tbody id="serrows"></tbody>
    </table></div>
  </details>
</div>

<script>
const D = __DATA__;
const day = d => new Date(d + "T00:00:00Z").getTime() / 86400000;
const fmtD = d => new Date(d + "T00:00:00Z").toLocaleDateString("en-GB", {day:"numeric", month:"short", year:"numeric", timeZone:"UTC"});
const NS = "http://www.w3.org/2000/svg";
const el = (n, a) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); return e; };

const PX = 6, PAD_T = 38, PLOT_H = 300, PAD_B = 32;
const H = PAD_T + PLOT_H + PAD_B;
const t0 = day(D.b49[0][0]), t1 = day("2026-09-20");
const W = Math.round((t1 - t0) * PX);
const X = d => (day(d) - t0) * PX;
const Y = b => PAD_T + PLOT_H * (1 - b / 10);

/* ---------- y axis (outside the scroller so it stays put) ---------- */
const yax = document.getElementById("yax");
yax.setAttribute("width", 52); yax.setAttribute("height", H);
yax.setAttribute("viewBox", `0 0 52 ${H}`);
for (let b = 0; b <= 10; b += 2) {
  const t = el("text", {x:40, y:Y(b)+4, "text-anchor":"end", fill:"var(--ink-3)",
    "font-family":"var(--mono)", "font-size":11});
  t.textContent = b.toFixed(0) + (b === 10 ? "" : "");
  yax.appendChild(t);
}
const yl = el("text", {x:13, y:PAD_T + PLOT_H/2, "text-anchor":"middle", fill:"var(--ink-3)",
  "font-family":"var(--sans)", "font-size":11, transform:`rotate(-90 13 ${PAD_T + PLOT_H/2})`});
yl.textContent = "chapters complete";
yax.appendChild(yl);

/* ---------- plot ---------- */
const svg = document.getElementById("plot");
svg.setAttribute("width", W); svg.setAttribute("height", H);
svg.setAttribute("viewBox", `0 0 ${W} ${H}`);

/* the wait band, drawn first so everything reads on top of it */
const bx0 = X(D.window[0]), bx1 = X(D.window[1]);
svg.appendChild(el("rect", {x:bx0, y:PAD_T, width:bx1-bx0, height:PLOT_H, fill:"var(--band)"}));
[bx0, bx1].forEach(x => svg.appendChild(el("line",
  {x1:x, y1:PAD_T, x2:x, y2:PAD_T+PLOT_H, stroke:"var(--band-edge)", "stroke-width":1.5})));
const blab = el("text", {x:(bx0+bx1)/2, y:PAD_T-20, "text-anchor":"middle", fill:"var(--ink-2)",
  "font-family":"var(--sans)", "font-size":12, "font-weight":600});
blab.textContent = "125 days, batch 49 finished and waiting";
svg.appendChild(blab);
svg.appendChild(el("line", {x1:bx0, y1:PAD_T-13, x2:bx1, y2:PAD_T-13,
  stroke:"var(--band-edge)", "stroke-width":1}));

/* horizontal gridlines + month ticks */
for (let b = 0; b <= 10; b += 2)
  svg.appendChild(el("line", {x1:0, y1:Y(b), x2:W, y2:Y(b),
    stroke:"var(--rule)", "stroke-width":1, "shape-rendering":"crispEdges"}));
let m = new Date(Date.UTC(2024, 5, 1));
while (m.getTime()/86400000 < t1) {
  const iso = m.toISOString().slice(0,10), x = X(iso);
  if (x >= 0) {
    svg.appendChild(el("line", {x1:x, y1:PAD_T, x2:x, y2:PAD_T+PLOT_H,
      stroke:"var(--rule)", "stroke-width":1, "shape-rendering":"crispEdges"}));
    const jan = m.getUTCMonth() === 0;
    const t = el("text", {x:x, y:H-12, "text-anchor":"middle", fill:jan?"var(--ink-2)":"var(--ink-3)",
      "font-family":"var(--mono)", "font-size":10.5, "font-weight":jan?500:400});
    t.textContent = m.toLocaleDateString("en-GB",{month:"short",timeZone:"UTC"})
      + (jan ? " " + m.getUTCFullYear() : "");
    svg.appendChild(t);
  }
  m = new Date(Date.UTC(m.getUTCFullYear(), m.getUTCMonth()+1, 1));
}

/* step paths: readiness holds until the next report */
function stepPath(pts, extendTo) {
  let d = `M${X(pts[0][0]).toFixed(1)},${Y(pts[0][1]).toFixed(1)}`;
  for (let i = 1; i < pts.length; i++)
    d += ` L${X(pts[i][0]).toFixed(1)},${Y(pts[i-1][1]).toFixed(1)}`
       + ` L${X(pts[i][0]).toFixed(1)},${Y(pts[i][1]).toFixed(1)}`;
  if (extendTo) d += ` L${X(extendTo).toFixed(1)},${Y(pts[pts.length-1][1]).toFixed(1)}`;
  return d;
}
svg.appendChild(el("path", {d:stepPath(D.b49, "2026-09-20"), fill:"none",
  stroke:"var(--s49)", "stroke-width":2, "stroke-linejoin":"miter"}));
svg.appendChild(el("path", {d:stepPath(D.b50, "2026-09-20"), fill:"none",
  stroke:"var(--s50)", "stroke-width":2, "stroke-linejoin":"miter"}));

/* reports inside the window, on the batch-50 line */
D.events.filter(e => e.chapter && e.chapter >= 421).forEach(e => {
  let b = 0; for (const [d, v] of D.b50) { if (d <= e.date) b = v; else break; }
  svg.appendChild(el("circle", {cx:X(e.date), cy:Y(b), r:3.6, fill:"var(--s50)",
    stroke:"var(--panel)", "stroke-width":2}));
});

/* the moment batch 49 hit 10.00, and ch421 completing inside the wait */
function marker(date, b, label, colour, dy) {
  const x = X(date), y = Y(b);
  svg.appendChild(el("circle", {cx:x, cy:y, r:5, fill:colour, stroke:"var(--panel)", "stroke-width":2}));
  svg.appendChild(el("line", {x1:x, y1:y+dy, x2:x, y2:y + (dy>0?8:-8), stroke:colour, "stroke-width":1}));
  const t = el("text", {x:x, y:y + dy + (dy>0?12:-4), "text-anchor":"middle", fill:"var(--ink)",
    "font-family":"var(--sans)", "font-size":11.5, "font-weight":600});
  t.textContent = label;
  svg.appendChild(t);
}
marker(D.window[0], 10, "all ten chapters done", "var(--s49)", -14);
marker("2026-05-26", 6.2, "ch. 421 manuscript complete", "var(--s50)", 20);

/* weekly publication ticks */
const tickY = PAD_T - 6;
D.chapter_pubs.forEach((p, i) => {
  const x = X(p.date);
  svg.appendChild(el("line", {x1:x, y1:tickY-9, x2:x, y2:tickY, stroke:"var(--pub)", "stroke-width":2}));
  if (i === 0 || i === D.chapter_pubs.length - 1) {
    const t = el("text", {x:x, y:tickY-13, "text-anchor":i?"end":"start", fill:"var(--ink-2)",
      "font-family":"var(--mono)", "font-size":10.5});
    t.textContent = "ch." + p.chapter;
    svg.appendChild(t);
  }
});
const sx0 = X(D.chapter_pubs[0].date), sx1 = X(D.chapter_pubs[D.chapter_pubs.length-1].date);
const sl = el("text", {x:(sx0+sx1)/2, y:PAD_T-20, "text-anchor":"middle", fill:"var(--ink-2)",
  "font-family":"var(--sans)", "font-size":12, "font-weight":600});
sl.textContent = "batch 49 serializes, weekly";
svg.appendChild(sl);

/* direct labels at the right edge */
[["Batch 49", D.b49, "var(--s49)"], ["Batch 50", D.b50, "var(--s50)"]].forEach(([name, pts, c]) => {
  const last = pts[pts.length-1];
  const t = el("text", {x:X("2026-09-20")-6, y:Y(last[1]) - 8, "text-anchor":"end", fill:c,
    "font-family":"var(--sans)", "font-size":12, "font-weight":600});
  t.textContent = `${name} · ${last[1].toFixed(2)}`;
  svg.appendChild(t);
});

/* ---------- hover: crosshair + tooltip ---------- */
const cross = el("line", {y1:PAD_T, y2:PAD_T+PLOT_H, stroke:"var(--ink-3)", "stroke-width":1,
  "stroke-dasharray":"3 3", opacity:0});
svg.appendChild(cross);
const dot49 = el("circle", {r:4.5, fill:"var(--s49)", stroke:"var(--panel)", "stroke-width":2, opacity:0});
const dot50 = el("circle", {r:4.5, fill:"var(--s50)", stroke:"var(--panel)", "stroke-width":2, opacity:0});
svg.appendChild(dot49); svg.appendChild(dot50);
const tip = document.getElementById("tip"), scroller = document.getElementById("scroller");
const at = (pts, iso) => { let v = null; for (const [d, b] of pts) { if (d <= iso) v = b; else break; } return v; };

function move(ev) {
  const r = svg.getBoundingClientRect();
  const x = ev.clientX - r.left;
  const iso = new Date((t0 + x / PX) * 86400000).toISOString().slice(0, 10);
  if (x < 0 || x > W) return;
  const v49 = at(D.b49, iso), v50 = at(D.b50, iso);
  cross.setAttribute("x1", x); cross.setAttribute("x2", x); cross.setAttribute("opacity", 1);
  if (v49 != null) { dot49.setAttribute("cx", x); dot49.setAttribute("cy", Y(v49)); dot49.setAttribute("opacity", 1); }
  else dot49.setAttribute("opacity", 0);
  if (v50 != null) { dot50.setAttribute("cx", x); dot50.setAttribute("cy", Y(v50)); dot50.setAttribute("opacity", 1); }
  else dot50.setAttribute("opacity", 0);
  const inWin = iso >= D.window[0] && iso <= D.window[1];
  tip.hidden = false;
  tip.innerHTML = `<b>${fmtD(iso)}</b>`
    + (inWin ? `<div style="color:var(--ink-3)">inside the 125-day wait</div>` : "")
    + (v49 != null ? `<div class="r"><i style="background:var(--s49)"></i>Batch 49 &nbsp;<b>${v49.toFixed(2)}</b></div>` : "")
    + (v50 != null ? `<div class="r"><i style="background:var(--s50)"></i>Batch 50 &nbsp;<b>${v50.toFixed(2)}</b></div>` : "");
  const shell = scroller.parentElement.getBoundingClientRect();
  let left = ev.clientX - shell.left + 14;
  if (left + tip.offsetWidth > shell.width - 6) left = ev.clientX - shell.left - tip.offsetWidth - 14;
  tip.style.left = Math.max(4, left) + "px";
  tip.style.top = Math.min(ev.clientY - shell.top + 12, shell.height - tip.offsetHeight - 6) + "px";
  tip.style.opacity = 1;
}
function leave() {
  cross.setAttribute("opacity", 0); dot49.setAttribute("opacity", 0); dot50.setAttribute("opacity", 0);
  tip.style.opacity = 0; tip.hidden = true;
}
svg.addEventListener("mousemove", move);
svg.addEventListener("mouseleave", leave);
svg.addEventListener("touchmove", e => { if (e.touches[0]) move(e.touches[0]); }, {passive:true});
svg.addEventListener("touchend", leave);

/* open with the wait in view */
scroller.scrollLeft = Math.max(0, bx0 - 120);

/* ---------- comparison: complete -> on sale ---------- */
(function () {
  const c = document.getElementById("cmp");
  const rows = D.compare, rowH = 50, padL = 136, padR = 18, padT = 28;
  const w = 640, h = padT + rows.length * rowH + 16;
  c.setAttribute("viewBox", `0 0 ${w} ${h}`);
  c.setAttribute("width", "100%"); c.setAttribute("height", h);
  c.style.minWidth = "540px";
  const lo = -58, hi = 132, plotW = w - padL - padR;
  const XX = v => padL + plotW * (v - lo) / (hi - lo);
  const zero = XX(0);

  c.appendChild(el("line", {x1:zero, y1:padT-12, x2:zero, y2:padT + rows.length*rowH - 10,
    stroke:"var(--ink-2)", "stroke-width":1.5}));
  const zt = el("text", {x:zero, y:padT-17, "text-anchor":"middle", fill:"var(--ink-2)",
    "font-family":"var(--sans)", "font-size":11, "font-weight":600});
  zt.textContent = "batch complete";
  c.appendChild(zt);

  rows.forEach((r, i) => {
    const y = padT + i*rowH + 8, x = XX(r.wait), pos = r.wait > 0;
    // name and value live in their own left column; nothing sits beside the bar
    const lab = el("text", {x:6, y:y+12, fill:"var(--ink)",
      "font-family":"var(--mono)", "font-size":12});
    lab.textContent = "batch " + r.batch;
    c.appendChild(lab);
    const val = el("text", {x:padL-14, y:y+12, "text-anchor":"end", fill:"var(--ink)",
      "font-family":"var(--mono)", "font-size":13, "font-weight":500});
    val.textContent = (pos ? "+" : "\\u2212") + Math.abs(r.wait) + " d";
    c.appendChild(val);

    c.appendChild(el("rect", {x:Math.min(zero, x), y:y, width:Math.abs(x-zero), height:16,
      rx:3, fill:pos ? "var(--s50)" : "var(--ink-3)", opacity:pos ? 1 : .5}));

    // note hangs off the zero line, on the same side as the bar, so it cannot overflow
    const note = el("text", {x:pos ? zero+7 : zero-7, y:y+29,
      "text-anchor":pos ? "start" : "end", fill:"var(--ink-3)",
      "font-family":"var(--sans)", "font-size":10.5});
    note.textContent = pos ? "held after finishing" : "on sale before finishing";
    c.appendChild(note);
  });
})();

/* ---------- tables ---------- */
const BATCH = ch => ch >= 431 ? 51 : ch >= 421 ? 50 : 49;
document.getElementById("evrows").innerHTML = D.events.map(e =>
  `<tr><td>${e.date}</td><td>${e.chapter ?? "&mdash;"}</td><td>${e.chapter ? BATCH(e.chapter) : "&mdash;"}</td><td style="text-align:left">${e.stage || "&mdash;"}</td></tr>`
).join("");
const dates = [...new Set([...D.b49.map(r=>r[0]), ...D.b50.map(r=>r[0])])].sort();
document.getElementById("serrows").innerHTML = dates.map(d =>
  `<tr><td>${d}</td><td>${(at(D.b49,d) ?? "&mdash;") === "&mdash;" ? "&mdash;" : at(D.b49,d).toFixed(2)}</td><td>${at(D.b50,d) == null ? "&mdash;" : at(D.b50,d).toFixed(2)}</td></tr>`
).join("");
</script>

<footer class="wrap" style="padding-block:0 3rem">
  <p style="font-family:var(--mono);font-size:11.5px;color:var(--ink-3);border-top:1px solid var(--rule);padding-top:1rem;margin:0">
    Built from the production event record &middot; <a href="index.html" style="color:var(--s50)">the running forecast</a> &middot; method in <code>docs/model.md</code> and <code>docs/v13_review.md</code>
  </p>
</footer>
</body>
</html>
"""


def main():
    data = collect()
    out = D_("site", "125-day-wait.html")
    html = TEMPLATE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("site: %s  %.1f KB" % (os.path.relpath(out, D_()), len(html) / 1024))
    w = data["compare"]
    for row in w:
        print("  batch %d: complete %s -> on sale %s  (%+d d)"
              % (row["batch"], row["complete"], row["publish"], row["wait"]))


if __name__ == "__main__":
    main()
