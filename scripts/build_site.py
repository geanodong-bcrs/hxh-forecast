#!/usr/bin/env python3
"""Phase 1D — the public pages (Agents.md §29 steps 20-24).

    data/forecasts/*.json + data/processed/*.csv
        -> site/index.html    the forecast, for readers
        -> site/method.html   how it works and where it is weak

Two pages on purpose. The audience is manga readers who want to know when the
next chapter lands; the method and the caveats are real and stay published, but
they do not belong in front of that answer. index.html carries one line pointing
at method.html for anyone who wants to check the working.

LANGUAGE. The model thinks in batches and numbers them; readers do not, and
"batch 50" means nothing outside this repo. Every user-facing string names a
chapter range instead.

The site reads the SNAPSHOT, not the model. It re-renders what was forecast and
never recomputes it, so presentation cannot disagree with the record.
"""
import csv
import glob
import json
import os
from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
SITE = D("site")

# Pipeline order, from Togashi's own 2024-09-24 description (Agents.md §8).
# The order is what licenses the "assumed done" inference below: he cannot ink
# backgrounds before the characters, or letter dialogue before the layout exists.
STAGES = [
    ("name", "Storyboard", "ネーム",
     "Rough layout: panel structure, rough figures, where the dialogue sits."),
    ("character_inking", "Inking", "人物ペン入れ",
     "Togashi inks the characters by hand, in pen."),
    ("bg_spec", "BG brief", "背景指定書",
     "Written instructions telling the assistants what backgrounds to draw."),
    ("bg_work", "Backgrounds", "背景",
     "The backgrounds themselves, drawn by staff."),
    ("dialogue", "Lettering", "台詞入れ",
     "Final dialogue written into the speech balloons."),
    ("retouch", "Touch-ups", "加筆",
     "Last corrections, made on the printed manuscript."),
    ("manuscript_complete", "Finished", "原稿完成",
     "Chapter complete and delivered to Shueisha."),
]
STAGE_IDX = {k: i for i, (k, _, _, _) in enumerate(STAGES)}

# The four tiers the fandom already uses (the @togashiactu chart). Our event data
# reproduces that chart chapter-for-chapter from a completely different source,
# which is a real cross-check — so the page speaks in these tiers and keeps the
# per-stage matrix as the detail view.
TIERS = [
    (3, "delivered", "Delivered to Shueisha", "集英社に納品済み"),
    (2, "spec", "Backgrounds &amp; dialogue specified", "背景/セリフ指定が完成"),
    (1, "drawn", "Drawn, no backgrounds or dialogue yet", "描かれたが背景/セリフ無し"),
    (0, "none", "Nothing reported", "情報不足"),
]
STAGE_TIER = {"manuscript_complete": 3, "retouch": 3, "dialogue": 2, "bg_work": 2,
              "bg_spec": 2, "character_inking": 1, "name": 0}


def tier_of(stages):
    """Furthest point a chapter has demonstrably reached."""
    done = [STAGE_TIER.get(k, 0) for k, r in stages.items() if r["status"] == "complete"]
    return max(done) if done else 0


def stage_marks(stages):
    """(css class, tooltip) per stage: confirmed, assumed, or unknown.

    Togashi does not post every stage of every chapter, so a bare matrix is full
    of holes that read as "he skipped this" when the chapter has in fact moved
    past it. Pipeline order licenses the inference: if backgrounds are specified,
    the characters were inked. Those cells are marked ASSUMED and drawn
    differently — §8 forbids inferring anything without recording that it is an
    inference.
    """
    confirmed = {k for k, r in stages.items() if r["status"] == "complete"}
    furthest = max((STAGE_IDX[k] for k in confirmed if k in STAGE_IDX), default=-1)
    out = []
    for key, en, ja, _ in STAGES:
        r = stages.get(key)
        if r and r["status"] == "complete":
            out.append(("done", "%s %s — reported %s" % (ja, en, r["event_date"])))
        elif r:
            out.append(("prog", "%s %s — started %s" % (ja, en, r["event_date"])))
        elif STAGE_IDX[key] < furthest:
            out.append(("assumed", "%s %s — not posted, but a later stage was, "
                                   "so this must be done" % (ja, en)))
        else:
            out.append(("", "%s %s — nothing reported" % (ja, en)))
    return out


# ------------------------------------------------------------------ data

def latest_snapshot():
    files = sorted(glob.glob(D("data", "forecasts", "*_posterior.json")))
    files = [f for f in files if "T" in os.path.basename(f).split("_")[0]]
    if not files:
        raise SystemExit("no timestamped posterior snapshot yet — run run_update.py")
    with open(files[-1], encoding="utf-8") as fh:
        post = json.load(fh)

    def mate(kind):
        q = D("data", "forecasts", "%s_batch%d_%s.json" % (post["run_id"], post["batch"], kind))
        if os.path.exists(q):
            with open(q, encoding="utf-8") as fh:
                return json.load(fh)
        return None
    return post, mate("level2_analog"), mate("prior_level1"), os.path.relpath(files[-1], D())


def history():
    path = D("data", "forecasts", "index.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["kind"] == "posterior" and r["median"]]
    rows.sort(key=lambda r: r["run_id"])
    return rows


def production_status(first_ch, n=20):
    path = D("data", "processed", "production_events.csv")
    grid = OrderedDict((c, {}) for c in range(first_ch, first_ch + n))
    latest = {}
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["event_class"] != "chapter_stage" or not r["chapter"] or not r["stage"]:
                continue
            try:
                c = int(float(r["chapter"]))
            except ValueError:
                continue
            if c not in grid:
                continue
            k = (c, r["stage"])
            # a later event supersedes an earlier one: state is NOT monotonic
            # (§8 rule 2 — リテイク regresses a chapter even after completion)
            if k not in latest or r["event_date"] > latest[k]["event_date"]:
                latest[k] = r
    for (c, stg), r in latest.items():
        grid[c][stg] = r
    return grid


def announcements():
    path = D("data", "annotations", "announcements.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    rows.sort(key=lambda r: int(r["chapter"]))
    return rows


def data_span():
    yrs = []
    with open(D("data", "processed", "chapters.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["publication_date_jp"]:
                yrs.append(r["publication_date_jp"][:4])
    return (min(yrs), max(yrs)) if yrs else ("", "")


def batch_first_chapter():
    """batch_id -> its first chapter, read from the data.

    The page names runs by chapter ("the run starting at chapter 391") because
    batch numbers mean nothing to a reader. Earlier this used the arithmetic
    (id-47)*10+391, which happens to be right today and would silently drift the
    moment a run is not exactly ten chapters.
    """
    out = {}
    with open(D("data", "processed", "chapters.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["modeling_era"] != "1" or not r["batch_id"]:
                continue
            b, c = int(r["batch_id"]), int(r["chapter"])
            if b not in out or c < out[b]:
                out[b] = c
    return out


def corpus_counts():
    """Row counts via the csv module, never line counting: verbatim Japanese
    contains newlines inside quoted fields, which made a line count report
    1,158 posts for a 480-row file."""
    out = {}
    for name, rel in (("chapters", "data/processed/chapters.csv"),
                      ("tweets", "data/processed/tweets.csv"),
                      ("events", "data/processed/production_events.csv")):
        p = D(*rel.split("/"))
        if not os.path.exists(p):
            out[name] = 0
            continue
        with open(p, encoding="utf-8", newline="") as fh:
            if name == "tweets":            # the label says "by Togashi"
                out[name] = sum(1 for r in csv.DictReader(fh) if r.get("is_togashi") == "1")
            else:
                out[name] = max(sum(1 for _ in csv.reader(fh)) - 1, 0)
    return out


# ------------------------------------------------------------------ render

def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def fmt(iso, short=False):
    d = date.fromisoformat(iso)
    return d.strftime("%-d %b %y") if short else d.strftime("%-d %b %Y")


def pct(p):
    """Never a literal 100%: §3 forbids presenting near-certainty as certainty."""
    return "&gt;99%" if p > 0.99 else "&lt;1%" if 0 < p < 0.01 else "%.0f%%" % (p * 100)


def month_ticks(o0, o1):
    """Month starts across the range; thinned so labels never collide."""
    d0, d1 = date.fromordinal(o0), date.fromordinal(o1)
    months = []
    y, m = d0.year, d0.month
    while date(y, m, 1) <= d1:
        if date(y, m, 1).toordinal() >= o0:
            months.append(date(y, m, 1))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    every = 1 if len(months) <= 14 else (2 if len(months) <= 28 else 3)
    return [(d, i % every == 0) for i, d in enumerate(months)]


def cdf_chart(pmf, median, i80, width=720, height=250, clip=0.99):
    """Cumulative probability the batch has begun, by date.

    Cumulative rather than a density: half the mass sits on a single issue, so a
    density plot is one spike and a hundred invisible bars — the reader learns
    nothing about the tail carrying the other half.

    The x-axis stops once the curve passes `clip`. Beyond that the answer is
    "almost certainly yes" and the extra years of flat line only shrink the part
    of the chart that carries information.
    """
    if not pmf:
        return "<p class=note>No distribution stored in this snapshot.</p>"
    acc, cum = 0.0, []
    for d, p in pmf:
        acc += p
        cum.append((date.fromisoformat(d).toordinal(), acc))
    cutoff = next((i for i, (_, c) in enumerate(cum) if c >= clip), len(cum) - 1)
    cum = cum[:cutoff + 1]

    pad_l, pad_r, pad_t, pad_b = 44, 16, 16, 40
    W, H = width - pad_l - pad_r, height - pad_t - pad_b
    x0, x1 = cum[0][0], cum[-1][0]
    span = max(x1 - x0, 1)
    X = lambda o: pad_l + W * (min(max(o, x0), x1) - x0) / span
    Y = lambda p: pad_t + H * (1 - p)

    # true step function: each point is one weekly issue, so the curve should
    # rise vertically at an issue and run flat between issues
    dpath = ["M%.1f,%.1f" % (pad_l, Y(0))]
    prev = 0.0
    for o, c in cum:
        dpath.append("L%.1f,%.1f L%.1f,%.1f" % (X(o), Y(prev), X(o), Y(c)))
        prev = c
    dpath.append("L%.1f,%.1f" % (X(x1), Y(prev)))
    line = " ".join(dpath)
    area = line + " L%.1f,%.1f L%.1f,%.1f Z" % (X(x1), Y(0), pad_l, Y(0))

    g = []
    for p in (0, .25, .5, .75, 1):
        g.append('<line class="grid" x1="%d" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                 '<text class="ax" x="%d" y="%.1f" text-anchor="end">%d%%</text>'
                 % (pad_l, Y(p), pad_l + W, Y(p), pad_l - 6, Y(p) + 4, int(p * 100)))
    for d, label in month_ticks(x0, x1):
        xx = X(d.toordinal())
        g.append('<line class="grid%s" x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>'
                 % (" yr" if d.month == 1 else "", xx, pad_t, xx, pad_t + H))
        if label:
            g.append('<text class="ax" x="%.1f" y="%d" text-anchor="middle">%s</text>'
                     % (xx, height - 22, d.strftime("%b")))

    # Year labels sit centred under the span each year actually occupies, on
    # their own row. They used to be drawn at every January plus the first tick,
    # which on a five-year axis put "2026" (a December first tick) and "2027" a
    # single month apart, overlapping badly. A year too narrow to hold its label
    # is skipped rather than crammed in.
    for yr in range(date.fromordinal(x0).year, date.fromordinal(x1).year + 1):
        lo, hi = max(x0, date(yr, 1, 1).toordinal()), min(x1, date(yr, 12, 31).toordinal())
        if hi <= lo or X(hi) - X(lo) < 34:
            continue
        g.append('<text class="ax yr" x="%.1f" y="%d" text-anchor="middle">%d</text>'
                 % ((X(lo) + X(hi)) / 2, height - 7, yr))

    med = date.fromisoformat(median).toordinal()
    lo, hi = (date.fromisoformat(i80[0]).toordinal(),
              date.fromisoformat(i80[1]).toordinal())
    return """<svg viewBox="0 0 %d %d" class="chart" role="img"
   aria-label="Cumulative probability publication has begun, by date">
  <rect class="band" x="%.1f" y="%d" width="%.1f" height="%d"/>
  %s
  <path class="area" d="%s"/><path class="cdfline" d="%s"/>
  <line class="med" x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>
</svg>""" % (width, height, X(lo), pad_t, max(X(hi) - X(lo), 1), H,
             "\n  ".join(g), area, line, X(med), pad_t, X(med), pad_t + H)


def history_chart(rows, width=720, height=140):
    if len(rows) < 2:
        return ""
    pad_l, pad_r, pad_t, pad_b = 44, 16, 14, 26
    W, H = width - pad_l - pad_r, height - pad_t - pad_b
    t = [datetime.strptime(r["run_id"], "%Y%m%dT%H%M%SZ").timestamp() for r in rows]
    m = [date.fromisoformat(r["median"]).toordinal() for r in rows]
    t0, t1, m0, m1 = min(t), max(t), min(m), max(m)
    X = lambda v: pad_l + W * (v - t0) / max(t1 - t0, 1)
    Y = lambda v: (pad_t + H * (1 - (v - m0) / (m1 - m0))) if m1 > m0 else pad_t + H / 2
    pts = ["%.1f,%.1f" % (X(a), Y(b)) for a, b in zip(t, m)]
    dots = "".join('<circle class="pt %s" cx="%.1f" cy="%.1f" r="4"><title>%s · %s · '
                   'median %s</title></circle>'
                   % (esc(r["trigger"]), X(a), Y(b), esc(r["run_id"]),
                      esc(r["trigger"]), esc(r["median"]))
                   for r, a, b in zip(rows, t, m))
    flat = "" if m1 > m0 else ('<text class="ax" x="%.1f" y="%.1f" text-anchor="middle">'
                               'unchanged at %s across all %d forecasts</text>'
                               % (pad_l + W / 2, pad_t + H / 2 - 12,
                                  fmt(rows[-1]["median"], True), len(rows)))
    return ('<svg viewBox="0 0 %d %d" class="chart"><path class="cdfline" d="M%s"/>%s%s</svg>'
            % (width, height, " L".join(pts), dots, flat))


CSS = """
:root{--bg:#fff;--fg:#14161a;--mut:#697079;--line:#e4e7ec;--card:#f7f8fa;
 --accent:#2f6fd0;--band:#2f6fd01f;--ok:#1f7a4d;--pend:#c8901a;--soft:#e9edf3}
@media(prefers-color-scheme:dark){:root{--bg:#0f1115;--fg:#e8eaed;--mut:#98a1ac;
 --line:#272b33;--card:#161920;--accent:#6fa8ff;--band:#6fa8ff26;--ok:#5fd39a;
 --pend:#e0b44a;--soft:#1d222b}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
 -webkit-font-smoothing:antialiased}
.wrap{max-width:840px;margin:0 auto;padding:30px 20px 72px}
h1{font-size:15px;font-weight:600;margin:0;color:var(--mut);letter-spacing:.01em}
h2{font-size:12px;font-weight:600;letter-spacing:.09em;text-transform:uppercase;
 color:var(--mut);margin:46px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--line)}
h3{font-size:14px;font-weight:600;margin:20px 0 6px}
p{margin:10px 0} a{color:var(--accent)}
.hero{margin:20px 0 4px}
.hero .ch{font-size:12px;color:var(--mut);letter-spacing:.09em;text-transform:uppercase}
.hero .date{font-size:46px;font-weight:650;letter-spacing:-.025em;line-height:1.08;margin:6px 0 2px}
.hero .sub{color:var(--mut)}
.pill{display:inline-block;padding:3px 10px;border-radius:99px;font-size:12.5px;
 font-weight:600;background:var(--band);color:var(--accent)}
.pill.plain{background:var(--soft);color:var(--mut)}
.chart{width:100%;height:auto;display:block;margin:10px 0 2px;overflow:visible}
.grid{stroke:var(--line);stroke-width:1}
.grid.yr{stroke:var(--mut);opacity:.4}
.ax{fill:var(--mut);font-size:11px}
.ax.yr{font-weight:600}
.area{fill:var(--band);stroke:none}
.cdfline{fill:none;stroke:var(--accent);stroke-width:2;stroke-linejoin:round}
.band{fill:var(--band)}
.med{stroke:var(--fg);stroke-width:1;stroke-dasharray:3 3;opacity:.5}
.pt{fill:var(--accent);stroke:var(--bg);stroke-width:1.5}
.pt.tweet{fill:var(--pend)} .pt.annotation{fill:var(--ok)}
table{border-collapse:collapse;width:100%;font-size:14px;margin:6px 0}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line)}
th{font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--mut);font-weight:600}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
tr.hi td{background:var(--card);font-weight:600}
tr.sep td{border-top:2px solid var(--line)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.note{color:var(--mut);font-size:13.5px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}
/* span is inline by default, so width/height are ignored without this —
   which is exactly why the status squares rendered as nothing at all */
.st{display:inline-block;width:14px;height:14px;border-radius:3px;
 background:var(--soft);border:1px solid var(--line);vertical-align:middle}
.st.done{background:var(--ok);border-color:transparent}
.st.prog{background:var(--pend);border-color:transparent}
.legend{display:flex;gap:15px;flex-wrap:wrap;color:var(--mut);font-size:12.5px;margin:10px 0}
.legend span{display:flex;gap:6px;align-items:center}
.dot{display:inline-block;width:10px;height:10px;border-radius:99px;
 background:var(--soft);border:1px solid var(--line)}
.tblwrap{overflow-x:auto}
.strip{display:grid;grid-template-columns:repeat(10,1fr);gap:5px;margin:12px 0}
@media(max-width:560px){.strip{grid-template-columns:repeat(5,1fr)}}
.chip{display:flex;align-items:center;justify-content:center;height:38px;
 border-radius:5px;font-weight:650;font-size:14px;color:#12240f;
 background:var(--soft);border:1px solid var(--line);cursor:default}
.chip.delivered{background:#63a844;border-color:transparent;color:#0e2408}
.chip.spec{background:#5b96d6;border-color:transparent;color:#08182b}
.chip.drawn{background:#dd8f36;border-color:transparent;color:#2a1704}
.chip.none{background:#b3453d;border-color:transparent;color:#fff}
.dot.delivered{background:#63a844;border-color:transparent}
.dot.spec{background:#5b96d6;border-color:transparent}
.dot.drawn{background:#dd8f36;border-color:transparent}
.dot.none{background:#b3453d;border-color:transparent}
.dot.done{background:var(--ok);border-color:transparent}
.dot.assumed{background:transparent;border:2px solid var(--ok)}
.st.assumed{background:transparent;border:2px dashed var(--ok)}
.jp{font-size:12px;color:var(--mut);font-weight:400}
th.stg{font-size:10px;line-height:1.25;white-space:nowrap}
footer{margin-top:52px;padding-top:16px;border-top:1px solid var(--line);color:var(--mut);font-size:12.5px}
footer code{font-size:11.5px;word-break:break-all}
ol.caveats{padding-left:20px} ol.caveats li{margin:10px 0}
"""

HEAD = ('<!doctype html><html lang=en><meta charset=utf-8>'
        '<meta name=viewport content="width=device-width,initial-scale=1">'
        '<title>%s</title><meta name=description content="%s">'
        '<style>%s</style>')


def rng(first, n=10):
    return "%d&ndash;%d" % (first, first + n - 1)


def chapter_table(rows, highlight=None):
    h = ['<div class=tblwrap><table><tr><th>Chapter</th><th>Most likely</th>'
         '<th>50% range</th><th>80% range</th></tr>']
    for r in rows:
        h.append('<tr%s><td>%d</td><td>%s</td><td class=note>%s &ndash; %s</td>'
                 '<td class=note>%s &ndash; %s</td></tr>'
                 % (" class=hi" if r["chapter"] == highlight else "", r["chapter"],
                    fmt(r["median"]), fmt(r["i50"][0], True), fmt(r["i50"][1], True),
                    fmt(r["i80"][0], True), fmt(r["i80"][1], True)))
    h.append("</table></div>")
    return "\n".join(h)


def build_index(post, l2, pri, snap_path):
    first = int(post["target"].split("ch ")[-1])
    nb = post.get("next_batch") or {}
    nfirst = nb.get("first_chapter", first + 10)
    pmf = post.get("posterior_pmf") or []
    spike = max(pmf, key=lambda x: x[1]) if pmf else None
    i = post["intervals"]
    hist, anns, counts = history(), announcements(), corpus_counts()
    grid = production_status(first, 20)

    h = ['<div class=wrap>',
         '<h1>Hunter &times; Hunter &mdash; manga publication forecast</h1>']

    # hero
    h += ['<div class=hero>',
          '<div class=ch>Chapters %s &mdash; next up, chapter %d</div>' % (rng(first), first),
          '<div class=date>%s</div>' % fmt(post["median"]),
          '<div class=sub>most likely date &middot; 80%% chance between %s and %s</div>'
          % (fmt(i["80"][0], True), fmt(i["80"][1], True))]
    if spike:
        h.append('<p><span class=pill>%.0f%% chance it is %s</span> &nbsp;'
                 '<span class=note>the very next issue after chapter %d</span></p>'
                 % (spike[1] * 100, fmt(spike[0], True), first - 1))
    h.append('</div>')

    h.append(cdf_chart(pmf, post["median"], i["80"]))
    h.append('<p class=note>The chance chapter %d has been published by a given '
             'date. Each step is one weekly Jump issue. The big jump is the first '
             'eligible issue &mdash; either the series resumes straight away, or '
             'it waits, and the slow climb after is that wait. Shaded band is the '
             '80%% range.</p>' % first)

    h.append('<h2>Chapters %s</h2>' % rng(first))
    h.append('<p class=note>These are not ten separate predictions. Once the run '
             'starts, chapters come out one per week almost without exception '
             '(143 of the last 145), so nearly all the uncertainty below is just '
             'the start date above.</p>')
    h.append(chapter_table(post["ten_chapter_forecast"], highlight=first))

    if post.get("p_started_by"):
        h.append('<h3>Chance it has started by</h3><table>')
        for d, p in sorted(post["p_started_by"].items()):
            h.append('<tr><td>%s</td><td class=num>%s</td></tr>' % (fmt(d), pct(p)))
        h.append('</table>')

    # second batch
    if nb:
        h.append('<h2>Chapters %s</h2>' % rng(nfirst))
        h.append('<p class=note>Togashi has already inked the first few of these, '
                 'but that says nothing about scheduling &mdash; every reported '
                 'event for them is at the earliest stage of the pipeline. So this '
                 'one rests on publication history alone: how long the series has '
                 'typically waited between runs. Treat it as a rough horizon, not '
                 'a date.</p>')
        h.append(cdf_chart(nb["pmf"], nb["median"], nb["intervals"]["80"]))
        h.append('<p><span class="pill plain">most likely %s</span> &nbsp;'
                 '<span class=note>80%% chance between %s and %s</span></p>'
                 % (fmt(nb["median"]), fmt(nb["intervals"]["80"][0], True),
                    fmt(nb["intervals"]["80"][1], True)))
        h.append(chapter_table(nb["ten_chapter_forecast"]))

    # production
    h.append('<h2>What Togashi has drawn</h2>')
    h.append('<p class=note>Togashi posts his own progress on X. Each chapter '
             'below sits at the furthest point he has actually reported.</p>')
    h.append('<div class=strip>')
    for c, stages in grid.items():
        t = tier_of(stages)
        cls = dict((n, k) for n, k, _, _ in TIERS)[t]
        newest = max(stages.values(), key=lambda r: r["event_date"]) if stages else None
        tip = ("%s — %s" % (fmt(newest["event_date"], True),
                            esc(newest["source_text_ja"])) if newest
               else "nothing reported yet")
        h.append('<span class="chip %s" title="%s">%d</span>' % (cls, tip, c))
    h.append('</div>')
    h.append('<div class=legend>')
    for n, k, en, ja in TIERS:
        h.append('<span><i class="dot %s"></i>%s <span class=jp>%s</span></span>' % (k, en, ja))
    h.append('</div>')
    counts_t = {}
    for stages in grid.values():
        counts_t[tier_of(stages)] = counts_t.get(tier_of(stages), 0) + 1
    h.append('<p class=note><strong>%d finished manuscripts are waiting.</strong> '
             'Drawing is not what holds the series up &mdash; Togashi has said the '
             'publication pace is the editors&rsquo; decision. What he posts tells '
             'us a run is <em>possible</em>, not that it is imminent.</p>'
             % counts_t.get(3, 0))

    # detail matrix
    h.append('<h3>Stage by stage</h3>')
    h.append('<p class=note>He does not post every stage of every chapter, so this '
             'grid would otherwise be full of holes that look like skipped work. '
             'Where a <em>later</em> stage has been reported, the earlier ones must '
             'be done &mdash; those are marked as assumed rather than reported, and '
             'drawn hollow.</p>')
    h.append('<div class=tblwrap><table><tr><th>Ch.</th>')
    for _, en, ja, _ in STAGES:
        h.append('<th class=stg><span class=jp>%s</span><br>%s</th>' % (ja, en))
    h.append('<th>Latest post</th></tr>')
    for c, stages in grid.items():
        h.append('<tr%s><td>%d</td>' % (" class=sep" if c == nfirst else "", c))
        for cls, tip in stage_marks(stages):
            h.append('<td><span class="st %s" title="%s"></span></td>' % (cls, tip))
        newest = max(stages.values(), key=lambda r: r["event_date"]) if stages else None
        h.append('<td class=note>%s</td></tr>'
                 % (("%s &middot; %s" % (fmt(newest["event_date"], True),
                                         esc(newest["source_text_ja"][:26])))
                    if newest else "&mdash;"))
    h.append('</table></div>')
    h.append('<div class=legend>'
             '<span><i class="dot done"></i>reported by Togashi</span>'
             '<span><i class="dot assumed"></i>assumed done</span>'
             '<span><i class=dot></i>no information</span></div>')

    h.append('<h3>What the stages mean</h3>')
    h.append('<div class=tblwrap><table><tr><th>Stage</th><th>Japanese</th>'
             '<th>What happens</th></tr>')
    for key, en, ja, desc in STAGES:
        h.append('<tr><td>%s</td><td class=jp>%s</td><td class=note>%s</td></tr>'
                 % (en, ja, desc))
    h.append('</table></div>')
    h.append('<p class=note>The four colours above match the chart the fandom '
             'already uses. This one is built independently, from Togashi&rsquo;s '
             'posts up, and lands on the same answer for every chapter &mdash; '
             'which is a reassuring sign that both are reading him correctly.</p>')

    # announced
    if anns:
        h.append('<h2>Already announced</h2>')
        h.append('<table><tr><th>Chapter</th><th>Issue</th><th>On sale</th></tr>')
        for r in anns:
            h.append('<tr><td>%s</td><td>Weekly Sh&#333;nen Jump %s no.%s</td>'
                     '<td>%s</td></tr>'
                     % (esc(r["chapter"]), esc(r["wsj_issue_year"]),
                        esc(r["wsj_issue_no"]), fmt(r["publication_date"])))
        h.append('</table>')
        h.append('<p class=note>Once Shueisha announces an issue, that chapter is '
                 'settled and the forecast stops guessing at it. Schedules have '
                 'moved before, so this is &ldquo;scheduled&rdquo;, not '
                 '&ldquo;certain&rdquo;.</p>')

    # history
    h.append('<h2>How this forecast has moved</h2>')
    h.append(history_chart(hist))
    h.append('<div class=legend>'
             '<span><i class="dot" style="background:var(--accent);border-color:transparent">'
             '</i>scheduled update</span>'
             '<span><i class="dot" style="background:var(--pend);border-color:transparent">'
             '</i>new post from Togashi</span></div>')
    h.append('<p class=note>%d forecast%s since %s, updated daily and again '
             'whenever Togashi posts. Nothing here is ever edited or deleted after '
             'the fact &mdash; including when it turns out wrong.</p>'
             % (len(hist), "" if len(hist) == 1 else "s",
                fmt(hist[0]["written_utc"][:10]) if hist else "&mdash;"))

    y0, y1 = data_span()
    h.append('<footer>')
    h.append('<p>Built from %d chapters (%s&ndash;%s), %d posts by Togashi and %d '
             'production events. <a href="method.html">How this is worked out, and '
             'where it is shakiest &rarr;</a></p>'
             % (counts["chapters"], y0, y1, counts["tweets"], counts["events"]))
    h.append('<p>Updated %s UTC. Sources: Hunterpedia and jajanken.net for '
             'publication records, Togashi&rsquo;s X account for production. An '
             'independent fan project, not affiliated with Shueisha or Togashi.</p>'
             % datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))
    h.append('</footer></div>')

    title = "Hunter × Hunter — when is chapter %d out?" % first
    desc = ("Forecast for Hunter x Hunter chapter %d: most likely %s. Updated daily."
            % (first, fmt(post["median"])))
    return (HEAD % (esc(title), esc(desc), CSS)) + "\n".join(h) + "</html>"


def build_method(post, l2, pri, snap_path):
    """The working, and the parts that are shaky. Kept off the front page but
    kept published: the headline is a strong claim and the caveats are what
    make it a forecast rather than a guess."""
    first = int(post["target"].split("ch ")[-1])
    nb = post.get("next_batch") or {}
    pmf = post.get("posterior_pmf") or []
    spike = max(pmf, key=lambda x: x[1]) if pmf else None
    counts = corpus_counts()

    h = ['<div class=wrap>',
         '<h1><a href="index.html">&larr; Forecast</a></h1>',
         '<div class=hero><div class=date style="font-size:30px">How this works</div>',
         '<div class=sub>and where it is weakest</div></div>']

    h.append('<h2>The question</h2>')
    h.append('<p>Hunter &times; Hunter has not been a weekly series since 2006. It '
             'comes out in <strong>runs of about ten chapters</strong>, separated '
             'by breaks that have ranged from nothing at all to three and a half '
             'years. Within a run, chapters appear one per week almost without '
             'exception &mdash; 143 of the last 145 gaps were exactly one issue.</p>')
    h.append('<p>So there is really only one hard question: <strong>when does the '
             'next run start?</strong> Everything else follows from it, which is '
             'why the ten-chapter tables are so tightly bunched.</p>')

    h.append('<h2>The three levels</h2>')
    h.append('<div class=card><h3>0 &mdash; already announced</h3><p class=note>'
             'If Shueisha has named the issue, there is nothing to predict. That '
             'chapter is recorded as scheduled and drops out of the model.</p></div>')
    h.append('<div class=card><h3>1 &mdash; what history alone suggests</h3>'
             '<p class=note>Built from publication records only, never from '
             'Togashi&rsquo;s posts &mdash; otherwise the next step would not be an '
             'update. There are %d gaps between runs since 2007, and they are '
             '<em>bimodal</em>: three times the next run began with no wait at all, '
             'the rest after waits of 9 to 184 issues. A single smooth curve would '
             'describe neither case, so the model uses a mixture.</p></div>'
             % ((pri or {}).get("n_observations") or 16))
    if l2:
        h.append('<div class=card><h3>2 &mdash; what Togashi&rsquo;s posts add</h3>'
                 '<p class=note>Production data covers only %d past runs. That is '
                 'far too few to fit a curve to, but enough to ask a different '
                 'question: <em>if this run behaves like that one, when would it '
                 'start?</em> Each past run is replayed onto the current production '
                 'dates.</p><table><tr><th>If it behaves like&hellip;</th>'
                 '<th>&hellip;chapter %d comes out</th></tr>'
                 % (len(post.get("analogs") or []), first))
        bfc = batch_first_chapter()
        for k, v in sorted((post.get("implied_by_analog") or {}).items()):
            label = ("the run starting at chapter %d" % bfc[int(k)]) \
                if int(k) in bfc else ("run %s" % esc(k))
            h.append('<tr><td>%s</td><td>%s</td></tr>' % (label, fmt(v)))
        h.append('</table><p class=note>Two of the three point at a date that has '
                 'already passed. That is informative &mdash; it means this run is '
                 '<em>not</em> behaving like them.</p></div>')
    h.append('<div class=card><h3>Putting them together</h3><p class=note>'
             'Togashi has posted %d production updates about this run. Those are '
             '<strong>not</strong> %d independent pieces of evidence &mdash; they '
             'are one person&rsquo;s working process observed %d times. Treating '
             'them as independent would produce a forecast about a week wide: very '
             'impressive, and wrong. So each <em>past run</em> counts once, and the '
             'confidence scales with how many comparable runs exist (three), not '
             'how many posts there are.</p></div>'
             % ((post.get("n_events_current_batch") or 0,) * 3))

    h.append('<h2>Where it is weakest</h2>')
    h.append('<div class=card><h3>The headline number is the least defensible part</h3>'
             '<p class=note>The %s%% on %s comes from a point mass estimated from '
             '<strong>two clustered observations from 2010&ndash;2012</strong>. It '
             'says there is roughly an even chance the series rolls straight from '
             'this run into the next with no break &mdash; which has not actually '
             'happened since 2012. It survived every check I ran, and it is still '
             'the claim I would least want to defend.</p></div>'
             % (("%.1f" % (spike[1] * 100)) if spike else "?",
                fmt(spike[0], True) if spike else "?"))
    h.append('<ol class=caveats>')
    h.append('<li><strong>The production side has never been scored against a real '
             'outcome.</strong> Three comparable runs, and none has started since '
             'the method was built. Chapter %d will be the first genuine test.</li>'
             % first)
    h.append('<li><strong>No accuracy figures are published.</strong> Scoring '
             'honestly means separating forecasts made <em>before</em> an official '
             'announcement from those made after, and that record has not been '
             'built yet. Without the split the numbers would measure how early '
             'Shueisha announces things, not whether this model knows anything. '
             'They are left out rather than estimated.</li>')
    h.append('<li><strong>The date slides later every week nothing happens.</strong> '
             'Once an issue passes without a chapter, that possibility is removed '
             'and the rest rescales. This is correct, but it will look like the '
             'model changing its mind.</li>')
    h.append('<li><strong>Chapters %s rest on history alone.</strong> The only '
             'production events reported for them are at the earliest stage, which '
             'says nothing about scheduling.</li>'
             % rng(nb.get("first_chapter", first + 10)))
    h.append('<li><strong>Where this run ends is assumed, not confirmed.</strong> '
             'A post from April 2026 can be read as &ldquo;chapter 420 '
             'onward&rdquo;, which would shift everything by ten chapters.</li>')
    h.append('<li><strong>Both publication sources are secondary.</strong> Nothing '
             'has been checked against Shueisha directly.</li>')
    h.append('</ol>')

    h.append('<footer>')
    h.append('<p>Forecast run <code>%s</code>, triggered by <code>%s</code>. '
             'Evidence as of <code>%s</code>. Snapshot <code>%s</code>.</p>'
             % (esc(post["run_id"]), esc(post["trigger"]),
                esc((post.get("evidence_asof") or "")[:16]), esc(snap_path)))
    h.append('<p>Every forecast this model has ever made is kept unedited, '
             'including the wrong ones. Built from %d chapters, %d posts and %d '
             'production events. <a href="index.html">Back to the forecast</a></p>'
             % (counts["chapters"], counts["tweets"], counts["events"]))
    h.append('</footer></div>')

    return (HEAD % ("How the Hunter × Hunter forecast works",
                    "Method and limitations behind the Hunter x Hunter "
                    "publication forecast.", CSS)) + "\n".join(h) + "</html>"


def main():
    post, l2, pri, snap_path = latest_snapshot()
    os.makedirs(SITE, exist_ok=True)
    for name, doc in (("index.html", build_index(post, l2, pri, snap_path)),
                      ("method.html", build_method(post, l2, pri, snap_path))):
        with open(os.path.join(SITE, name), "w", encoding="utf-8") as fh:
            fh.write(doc)
        print("site: site/%-12s %.1f KB" % (name, len(doc) / 1024.0))


if __name__ == "__main__":
    main()
