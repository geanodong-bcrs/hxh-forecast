#!/usr/bin/env python3
"""Build the paper-style explanation of the forecast's prior and posterior."""
import html
import glob
import json
import os
import sys
import csv
from collections import defaultdict
from datetime import date

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
sys.path.insert(0, HERE)
from build_batch_prior import load_gaps, weights, build_prior  # noqa: E402


def plot_svg(pmf, gaps, pi0):
    """The selected zero-point-mass plus positive-gap KDE prior."""
    width, height, left, right = 920, 330, 72, 22
    top, bottom = 34, 50
    w, h = width - left - right, height - top - bottom
    xmax = len(pmf) - 1
    x = lambda g: left + g / xmax * w

    def panel(title, values, y_max, conditional=False):
        y = lambda p: top + h - p / y_max * h
        ticks = [0, y_max / 2, y_max]
        grid = "".join('<line x1="%g" y1="%.1f" x2="%g" y2="%.1f" class="grid"/>'
                       '<text x="%g" y="%.1f" text-anchor="end" class="tick">%.1f%%</text>'
                       % (left, y(v), width-right, y(v), left-9, y(v)+4, 100*v)
                       for v in ticks)
        xt = "".join('<text x="%.1f" y="%d" text-anchor="middle" class="tick">%d</text>'
                      % (x(g), top+h+21, g) for g in (0, 50, 100, 150, 200))
        path = "M " + " L ".join("%.2f %.2f" % (x(g), y(v))
                                  for g, v in enumerate(values) if g > 0)
        rugs = "".join('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" class="rug"/>'
                       % (x(g), top+h, x(g), top+h-8) for g in gaps if g > 0)
        zero = '' if conditional else (
            '<rect x="%.1f" y="%.1f" width="8" height="%.1f" class="zero"/>'
            '<text x="%.1f" y="%.1f" text-anchor="start" class="label">G=0: %.1f%%</text>'
            % (x(0)-4, y(values[0]), top+h-y(values[0]), x(0)+11, y(values[0])+13, 100*values[0]))
        return '''<svg viewBox="0 0 %d %d" role="img" aria-label="%s">
<text x="%d" y="18" class="title">%s</text>
<rect x="%d" y="%d" width="%d" height="%d" class="frame"/>
%s%s%s<path d="%s" class="line"/>%s
<text x="%d" y="%d" text-anchor="middle" class="axis">issues skipped between batches (G)</text>
<text x="18" y="%d" transform="rotate(-90 18 %d)" text-anchor="middle" class="axis">probability</text>
</svg>''' % (width, height, html.escape(title), left, html.escape(title), left, top, w, h, grid, xt, rugs, path, zero,
                 left+w/2, height-8, top+h/2, top+h/2)

    positive = np.array(pmf, float)
    positive[0] = 0
    positive /= positive.sum()
    return (panel("Selected Level 1 gap prior", pmf, max(float(max(pmf))*1.08, .01)) +
            panel("Positive-gap component, conditional on G > 0", positive,
                  max(float(max(positive))*1.08, .01), conditional=True))


def level1_date_svg():
    """Current direct-target Level 1 distribution, after no-start conditioning."""
    latest = None
    for path in glob.glob(D("data", "forecasts", "*_posterior.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                snap = json.load(fh)
        except Exception:
            continue
        if snap.get("provenance") == "replay" or not snap.get("run_id"):
            continue
        if latest is None or snap["run_id"] > latest["run_id"]:
            latest = snap
    if not latest:
        return "", "", "", ""
    floor = latest.get("truncation_floor") or ""
    pmf = [(d, float(p)) for d, p in (latest.get("prior_pmf") or []) if d >= floor]
    total = sum(p for _, p in pmf)
    if not total:
        return "", "", "", ""
    pmf = [(d, p / total) for d, p in pmf]
    running, median = 0.0, pmf[-1][0]
    for d, p in pmf:
        running += p
        if running >= .5:
            median = d
            break
    monthly = defaultdict(float)
    for d, p in pmf:
        monthly[d[:7]] += p
    months = sorted(monthly)
    width, height, left, right, top, bottom = 920, 310, 68, 22, 34, 52
    w, h = width-left-right, height-top-bottom
    ymax = max(monthly.values()) * 1.10
    X = lambda i: left + (i + .5) * w / len(months)
    Y = lambda p: top + h - p / ymax * h
    bars = "".join('<rect class="bar" x="%.2f" y="%.2f" width="%.2f" height="%.2f"><title>%s: %.1f%%</title></rect>'
                   % (left + i*w/len(months) + 1, Y(monthly[m]), max(w/len(months)-2, 1),
                      top+h-Y(monthly[m]), m, 100*monthly[m]) for i, m in enumerate(months))
    grid = "".join('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" class="grid"/><text x="%d" y="%.1f" text-anchor="end" class="tick">%.0f%%</text>'
                   % (left, Y(v), width-right, Y(v), left-8, Y(v)+4, 100*v)
                   for v in (0, ymax/2, ymax))
    ticks = "".join('<text x="%.1f" y="%d" text-anchor="middle" class="tick">%s</text>'
                    % (X(i), top+h+21, m[:4]) for i, m in enumerate(months) if m.endswith("-01"))
    med_month = median[:7]
    med_i = months.index(med_month)
    med = '<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" class="med"/><text x="%.1f" y="%d" class="label">median: %s</text>' % (X(med_i), top, X(med_i), top+h, X(med_i)+5, top+14, median)
    svg = '''<svg viewBox="0 0 %d %d" role="img" aria-label="Level 1 only probability distribution for chapter 421 publication date">
<text x="%d" y="18" class="title">Chapter 421 — Level 1-only probability by month</text>
<rect x="%d" y="%d" width="%d" height="%d" class="frame"/>%s%s%s%s
<text x="%d" y="%d" text-anchor="middle" class="axis">publication month</text>
<text x="18" y="%d" transform="rotate(-90 18 %d)" text-anchor="middle" class="axis">probability</text>
</svg>''' % (width, height, left, left, top, w, h, grid, bars, ticks, med,
              left+w/2, height-8, top+h/2, top+h/2)
    return svg, latest.get("forecast_timestamp", ""), floor, median


def forecast_history_svg(path, title, aria, *, date_key="asof", median_key="median",
                         lo_key="i80_lo", hi_key="i80_hi"):
    """Render a fixed-target median and 80% band from a working replay table."""
    if not os.path.exists(path):
        return "", 0
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    rows = [r for r in rows if r.get(date_key) and r.get(median_key)
            and r.get(lo_key) and r.get(hi_key)]
    if len(rows) < 2:
        return "", len(rows)
    width, height, left, right, top, bottom = 920, 315, 72, 26, 34, 48
    w, h = width-left-right, height-top-bottom
    T = lambda s: date.fromisoformat(s).toordinal()
    t0, t1 = T(rows[0][date_key]), T(rows[-1][date_key])
    vals = [T(r[k]) for r in rows for k in (lo_key, hi_key, median_key)]
    lo, hi = min(vals), max(vals)
    pad = max((hi-lo)*.06, 14)
    lo, hi = lo-pad, hi+pad
    X = lambda t: left + w*(t-t0)/max(t1-t0, 1)
    Y = lambda t: top + h*(t-lo)/max(hi-lo, 1)
    grid = ""
    for year in range(date.fromordinal(int(t0)).year, date.fromordinal(int(t1)).year + 2):
        tick = date(year, 1, 1).toordinal()
        if t0 <= tick <= t1:
            grid += '<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" class="grid"/><text x="%.1f" y="%d" text-anchor="middle" class="tick">%d</text>' % (X(tick), top, X(tick), top+h, X(tick), height-10, year)
    for frac in (0, .5, 1):
        tick = lo + frac*(hi-lo)
        grid += '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" class="grid"/><text x="%d" y="%.1f" text-anchor="end" class="tick">%s</text>' % (left, Y(tick), width-right, Y(tick), left-8, Y(tick)+4, date.fromordinal(int(tick)).strftime("%b %Y"))
    upper = [(X(T(r[date_key])), Y(T(r[hi_key]))) for r in rows]
    lower = [(X(T(r[date_key])), Y(T(r[lo_key]))) for r in reversed(rows)]
    band = " ".join("%.1f,%.1f" % p for p in upper + lower)
    median = " L ".join("%.1f,%.1f" % (X(T(r[date_key])), Y(T(r[median_key]))) for r in rows)
    return ('''<svg viewBox="0 0 %d %d" role="img" aria-label="%s">
<text x="%d" y="18" class="title">%s</text>
<rect x="%d" y="%d" width="%d" height="%d" class="frame"/>%s
<polygon points="%s" class="band"/><path d="M %s" class="line"/>
<text x="%d" y="%d" text-anchor="middle" class="axis">forecast date</text>
<text x="18" y="%d" transform="rotate(-90 18 %d)" text-anchor="middle" class="axis">predicted publication date</text>
</svg>''' % (width, height, html.escape(aria), left, html.escape(title), left, top, w, h, grid, band, median,
              left+w/2, height-8, top+h/2, top+h/2), len(rows))


def pairs_history_svg():
    return forecast_history_svg(D("data", "working", "chapter421_pairs_history.csv"),
                                "Chapter 421 — all-pairs likelihood history",
                                "Chapter 421 all-pairs likelihood history")


def posterior_history_svg():
    return forecast_history_svg(
        D("data", "working", "chapter421_forecast_steps.csv"),
        "Chapter 421 — final V11 prediction history",
        "Chapter 421 final V11 posterior prediction history",
        date_key="as_of", median_key="chapter421_p50",
        lo_key="chapter421_p10", hi_key="chapter421_p90")


def feasibility_diagnostics_svgs():
    """Show the observable inputs that shape the one-sided feasibility term."""
    path = D("data", "working", "chapter421_feasibility_history.csv")
    if not os.path.exists(path):
        return "", "", 0
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    rows = [r for r in rows if r.get("readiness") and r.get("floor_47") and r.get("floor_48") and r.get("floor_49")]
    if len(rows) < 2:
        return "", "", len(rows)

    width, height, left, right, top, bottom = 920, 315, 72, 26, 34, 48
    w, h = width-left-right, height-top-bottom
    T = lambda s: date.fromisoformat(s).toordinal()
    t0, t1 = T(rows[0]["asof"]), T(rows[-1]["asof"])
    X = lambda t: left + w*(t-t0)/max(t1-t0, 1)

    def x_grid():
        ticks = sorted({T(r["asof"]) for r in rows[::max(1, len(rows)//4)]} | {t1})
        return "".join(
            '<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" class="grid"/><text x="%.1f" y="%d" text-anchor="middle" class="tick">%s</text>'
            % (X(tick), top, X(tick), top+h, X(tick), height-10,
               date.fromordinal(tick).strftime("%b %-d"))
            for tick in ticks
        )

    def date_chart():
        keys = (("floor_47", "f47", "batch 47 analog"),
                ("floor_48", "f48", "batch 48 analog"),
                ("floor_49", "f49", "batch 49 analog"))
        vals = [T(r[key]) for r in rows for key, _, _ in keys]
        lo, hi = min(vals)-10, max(vals)+10
        Y = lambda v: top + h*(hi-v)/max(hi-lo, 1)
        grid = x_grid()
        for frac in (0, .5, 1):
            tick = lo + frac*(hi-lo)
            grid += '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" class="grid"/><text x="%d" y="%.1f" text-anchor="end" class="tick">%s</text>' % (left, Y(tick), width-right, Y(tick), left-8, Y(tick)+4, date.fromordinal(int(tick)).strftime("%b %Y"))
        paths = ""
        legend = ""
        for i, (key, css, label) in enumerate(keys):
            pts = " L ".join("%.1f,%.1f" % (X(T(r["asof"])), Y(T(r[key]))) for r in rows)
            paths += '<path d="M %s" class="%s"/>' % (pts, css)
            lx = left + i*160
            legend += '<line x1="%d" y1="29" x2="%d" y2="29" class="%s"/><text x="%d" y="33" class="tick">%s</text>' % (lx, lx+20, css, lx+26, label)
        return '''<svg viewBox="0 0 %d %d" role="img" aria-label="Chapter 421 feasibility boundaries by forecast date">
<text x="%d" y="18" class="title">Chapter 421 — feasibility dates implied by each historical analog</text>%s
<rect x="%d" y="%d" width="%d" height="%d" class="frame"/>%s%s
<text x="%d" y="%d" text-anchor="middle" class="axis">forecast date</text>
<text x="18" y="%d" transform="rotate(-90 18 %d)" text-anchor="middle" class="axis">earliest feasible publication date</text>
</svg>''' % (width, height, left, legend, left, top, w, h, grid, paths,
              left+w/2, height-8, top+h/2, top+h/2)

    def readiness_chart():
        Y = lambda v: top + h*(1-v/10.0)
        grid = x_grid()
        for tick in (0, 2.5, 5, 7.5, 10):
            grid += '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" class="grid"/><text x="%d" y="%.1f" text-anchor="end" class="tick">%g</text>' % (left, Y(tick), width-right, Y(tick), left-8, Y(tick)+4, tick)
        pts = " L ".join("%.1f,%.1f" % (X(T(r["asof"])), Y(float(r["readiness"]))) for r in rows)
        return '''<svg viewBox="0 0 %d %d" role="img" aria-label="Chapter 421 reported readiness by forecast date">
<text x="%d" y="18" class="title">Chapter 421 — summed readiness of chapters 421–430</text>
<rect x="%d" y="%d" width="%d" height="%d" class="frame"/>%s
<path d="M %s" class="ready"/>
<text x="%d" y="%d" text-anchor="middle" class="axis">forecast date</text>
<text x="18" y="%d" transform="rotate(-90 18 %d)" text-anchor="middle" class="axis">\\(B(t)\\)</text>
</svg>''' % (width, height, left, left, top, w, h, grid, pts,
              left+w/2, height-8, top+h/2, top+h/2)

    return date_chart(), readiness_chart(), len(rows)


def all_pairs_component_rows():
    """Latest retained V8 all-pairs component summaries for the worked example."""
    candidates = []
    for path in glob.glob(D("data", "forecasts", "*_posterior.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                snap = json.load(fh)
        except Exception:
            continue
        if snap.get("level2_design") != "all_pairs_coordinate_likelihood_v8_parametric_level1_frozen_fade":
            continue
        if snap.get("provenance") == "replay":
            continue
        candidates.append(snap)
    if not candidates:
        return ""
    snap = max(candidates, key=lambda x: x.get("run_id", ""))
    detail = (snap.get("all_pairs_coordinate_likelihood") or {}).get("historical_component_detail") or {}
    rows = []
    for h, d in sorted(detail.items(), key=lambda x: int(x[0])):
        rows.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s days</td><td>%s</td><td>\\(L_%s(s)=%.4fQ_%s(s)+%.4f\\)</td></tr>'
                    % (html.escape(h), html.escape(str(d.get("centre", "—"))),
                       html.escape(str(d.get("current_events_matched", "—"))),
                       html.escape(str(d.get("weighted_pair_matches", "—"))),
                       html.escape(str(d.get("sigma_days", "—"))),
                       html.escape(str(d.get("fade_alpha", "—"))), h,
                       float(d.get("fade_alpha", 0)), h,
                       1 - float(d.get("fade_alpha", 0))))
    return "".join(rows)


def build():
    gaps, cluster_w = load_gaps(with_cluster_weights=True)
    raw_gaps = [g for _, g in gaps]
    w = weights(len(gaps), None) * np.array(cluster_w)
    pmf, pi0 = build_prior(gaps, w, 200, separate_zero=True)
    effective = float(w.sum())
    raw = ", ".join(map(str, raw_gaps))
    chart = plot_svg(pmf, raw_gaps, pi0)
    chapter_chart, chart_asof, chart_floor, chart_median = level1_date_svg()
    pairs_chart, pairs_n = pairs_history_svg()
    posterior_history_chart, posterior_history_n = posterior_history_svg()
    feasibility_floor_chart, readiness_chart, feasibility_diag_n = feasibility_diagnostics_svgs()
    all_pairs_rows = all_pairs_component_rows()
    page = rf'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Statistical methods — Hunter × Hunter publication forecast</title>
<script>window.MathJax={{tex:{{inlineMath:[['\\(','\\)']],displayMath:[['\\[','\\]']]}}}};</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<style>
body{{margin:0;background:#f8f8f5;color:#222;font:16px/1.55 ui-serif,Georgia,serif}} .wrap{{max-width:900px;margin:auto;padding:42px 22px 70px}}
h1{{font-size:34px;line-height:1.12;margin:0 0 8px}} h2{{margin-top:42px;font-size:24px}} h3{{margin-top:28px;font-size:18px}}
.sub,.note{{color:#666}} .card{{background:#fff;border:1px solid #ddd;border-radius:10px;padding:16px 18px;margin:18px 0}} code{{font-size:.9em}}
svg{{display:block;width:100%;height:auto;margin:22px 0}} .frame{{fill:#fff;stroke:#bdbdb8}} .grid{{stroke:#e3e3de;stroke-width:1}} .line{{fill:none;stroke:#2c6c76;stroke-width:2.4}} .band{{fill:#2c6c76;opacity:.14}} .bar{{fill:#2c6c76;opacity:.82}} .med{{stroke:#b77b27;stroke-width:1.5;stroke-dasharray:4 3}} .zero{{fill:#b77b27}} .rug{{stroke:#888;stroke-width:1.2}} .f47,.f48,.f49,.ready{{fill:none;stroke-width:2.4}} .f47{{stroke:#2c6c76}} .f48{{stroke:#b77b27}} .f49{{stroke:#775b9c}} .ready{{stroke:#2c6c76}} .tick{{font:12px ui-sans-serif,system-ui;fill:#666}} .axis{{font:12px ui-sans-serif,system-ui;fill:#444}} .title{{font:600 15px ui-sans-serif,system-ui;fill:#222}} .label{{font:12px ui-sans-serif,system-ui;fill:#7a4d0e}}
table{{border-collapse:collapse;width:100%}} td,th{{padding:7px 8px;border-bottom:1px solid #ddd;text-align:left}} th{{font:12px ui-sans-serif,system-ui;text-transform:uppercase;color:#666}}
a{{color:#245b6b}}
</style><body><main class="wrap">
<p class="note"><a href="method.html">← Short method</a></p>
<h1>Statistical methods</h1>
<p class="sub">The selected forecast combines a publication-history prior, an ordered production-readiness likelihood, and continuous conditioning on issues that have already passed without chapter 421.</p>
<h2>1. The question: chapter 421</h2>
<p>The immediate target is the Weekly Shonen Jump issue in which chapter 421, the first chapter after the 411&ndash;420 run, begins publication. Let \(S_{{421}}\) be that issue&rsquo;s on-sale date. The model first predicts the number of eligible issues skipped after chapter 420:</p>
\[G=\text{{issues skipped after ch. 420 before ch. 421 appears}}.\]
<p>A gap of \(G=0\) means ch. 421 appears in the next eligible issue. Dates are only a display layer: every calculation is on the actual WSJ issue calendar, including combined issues and breaks.</p>
<h2>2. Historical Level 1 data</h2>
<p>Only the 2007-onward publication regime is used. Long uninterrupted runs are divided into 10-chapter batches, so immediate continuations are real observations. The modern-era gaps are:</p>
<div class="card"><code>{raw}</code></div>
<p>There is no recency decay. Leakage-free rolling-origin tests found that downweighting older gaps worsened both CRPS and log score; with so few observations, it loses more information than it gains.</p>
<h2>3. Selected Level 1 prior</h2>
<p>The selected prior is a mixture, not the later V8 shifted-lognormal experiment:</p>
\[P(G=g)=\pi_0 I(g=0)+(1-\pi_0)f_+(g),\qquad g=0,1,\ldots,200.\]
<p>\(f_+\) is a 60-issue Gaussian-kernel estimate fitted only to positive gaps. The point mass is retained because the rolling-origin test favored it over smoothing zero into the positive-gap curve.</p>
<p>Two adjacent zero gaps arose from one long historical run and share one observation&rsquo;s total weight. Thus \(\pi_0=2/15={pi0:.4f}\), with an effective sample size of {effective:.0f}. This is a modest, historically grounded probability of immediate continuation&mdash;not a claim that ch. 421 is likely to be scheduled immediately.</p>
<p>Here and below, \(I(A)\) is the <strong>indicator function</strong>: it equals 1 when condition \(A\) is true and 0 otherwise.</p>
{chart}
<h2>4. From the prior to ch. 421</h2>
<p>If chapter 420 is the final issue of the preceding run, with sequence \(E\), then a possible gap maps to ch. 421&rsquo;s start issue:</p>
\[S_{{421}}=E+G+1.\]
<p>This produces the initial distribution for ch. 421 before conditioning on the public fact that a particular issue did not contain it.</p>
<h2>5. Continuous no-start conditioning</h2>
<p>At any forecast date \(t\), let \(F_t\) be the most recent eligible WSJ issue publicly known not to contain ch. 421. Those dates are impossible, regardless of whether Togashi posted that week:</p>
\[P(S_{{421}}=s\mid S_{{421}}>F_t)=\frac{{P_0(s)I(s>F_t)}}{{\sum_u P_0(u)I(u>F_t)}}.\]
<p>This is not a production update. It is ordinary conditioning on non-publication. It avoids the old V4 error of leaving probability on past issues during a quiet stretch and then removing months of impossible mass at the next tweet.</p>
<h3>Current ch. 421 Level 1-only distribution</h3>
<p class="note">As of {chart_asof}, after excluding issues through {chart_floor}. This figure isolates Level 1 before the selected Level 2 feasibility likelihood is applied; its median is {chart_median}.</p>
{chapter_chart}
<h2>6. What Level 2 does&mdash;and does not&mdash;do</h2>
<p>The selected Level 2 treats production readiness as two-sided evidence about publication timing. It downweights dates that are implausibly early or much later than comparable historical readiness trajectories; it does not translate each tweet into a fixed publication date.</p>
<h3>Why event-to-date translation was rejected</h3>
<p>The V5&ndash;V8 all-pairs experiment translated every production event into candidate publication dates by matching chapter-progress coordinates and event-to-publication lags from resolved historical batches. It has only two leakage-free independent targets. It improved their average score, but both realized starts still fell before its 80% interval, and its behavior can make a later progress report move a date later. That is not strong enough evidence to make it the public headline.</p>
<p>The two-sided ordered-readiness model instead compresses the correlated reports into one batch state. It is selected because its physical interpretation is better, but it still rests on only three resolved tweet-era starts and must remain broad. The all-pairs approach is retained below as a research comparison.</p>
<h3>Experimental method A: all-pairs coordinate likelihood</h3>
<p>Each usable event is represented as a point \((C_e,t_e)\). Its coordinate is the chapter number plus within-chapter progress: page logs contribute early fractions of a chapter, while reported stages map to later fractions. For ch. 421, the target coordinate is the beginning of that chapter. An event on ch. 425 therefore has a negative coordinate distance from the target; that is intentional, because a publisher can begin a run while later chapters are still being finished.</p>
<p>For every resolved historical start \(h\), the method stores all pre-start pairs</p>
\[\Delta C_{{hr}}=C_h-C_r,\qquad \ell_{{hr}}=S_h-t_r.\]
<p>A current ch. 421&ndash;430 event \(e\) is compared to historical pairs with similar distance. A pair&rsquo;s weight is</p>
\[w_{{ehr}}=\exp\left[-\frac12\left(\frac{{(C_{{421}}-C_e)-\Delta C_{{hr}}}}{{b_C}}\right)^2\right],\qquad b_C=1\text{{ chapter}}.\]
<p>It proposes an implied ch. 421 start date \(m_{{ehr}}=t_e+\ell_{{hr}}\). The phrase &ldquo;three nested averages&rdquo; means the following.</p>
<p><strong>First: pairs within one current event.</strong> Let \(R_{{eh}}\) be the historical pairs from batch \(h\) that receive non-negligible weight for current event \(e\). Normalize their coordinate weights <em>within that event</em>:</p>
\[\widetilde w_{{ehr}}=w_{{ehr}}/W_{{eh}},\qquad W_{{eh}}=\sum_{{q\in R_{{eh}}}}w_{{ehq}}.\]
<p>Using the robust date spread \(\sigma_h\) for that historical batch, event \(e\) contributes one date-shaped mixture:</p>
\[K_{{eh}}(s)=\sum_{{r\in R_{{eh}}}}\widetilde w_{{ehr}}\exp\left[-\frac12\left(\frac{{s-m_{{ehr}}}}{{\sigma_h}}\right)^2\right].\]
<p>So a current page log with many compatible historical pairs still has total weight one; the pairs merely determine its shape.</p>
<p><strong>Second: current events within one historical batch.</strong> Let \(E_h\) be the current events that find at least one compatible pair in historical batch \(h\). Their mixtures are averaged, not multiplied:</p>
\[Q_h(s)=\frac{{1}}{{|E_h|}}\sum_{{e\in E_h}}K_{{eh}}(s).\]
<p>This gives a page log, a stage completion, and a later report on the same chapter equal total influence after they have been converted to comparable event mixtures. It does <em>not</em> say that they are independent observations.</p>
<p><strong>Third: historical batch components.</strong> Each resolved historical batch is one competing analog for how a run can be scheduled. A stale analog can be faded toward a flat likelihood with \(\alpha_h\in[0,1]\):</p>
\[L_h(s)=\alpha_h Q_h(s)+(1-\alpha_h).\]
<p>The all-pairs likelihood then averages those batch-level components:</p>
\[L_{{\mathrm{{pairs}}}}(s)\propto\frac{{1}}{{|H|}}\sum_{{h\in H}}L_h(s).\]
<p>They are never multiplied. Thus, even if ch. 421&ndash;430 contain thirty related posts and thousands of matched pairs, the method has only as many top-level scheduling components as resolved historical batches&mdash;currently three. This is the correlation safeguard.</p>
<h4>Worked path for one ch. 421 event</h4>
<p>Here is one concrete path through the calculation. On 2026-05-26, Togashi reported <em>manuscript complete</em> for ch. 421. The coordinate mapping assigns that event \(C_e=420.9\): chapter 421 starts at 420, and manuscript completion contributes 0.9. The target coordinate is \(C_{{421}}=421\), so its target distance is</p>
\[d_e=C_{{421}}-C_e=421-420.9=0.1.\]
<p>Now consider one exact-distance template from each resolved historical batch. The table shows only one template per batch; the real calculation retains <em>all</em> compatible templates.</p>
<table><tr><th>Historical batch</th><th>Matching historical event</th><th>Historical lag to start</th><th>Implied ch. 421 start</th></tr>
<tr><td>47</td><td>Ch. 391 manuscript complete, 2022-07-27</td><td>89 days</td><td>2026-08-23</td></tr>
<tr><td>48</td><td>Ch. 401 manuscript complete, 2023-03-09</td><td>578 days</td><td>2027-12-25</td></tr>
<tr><td>49</td><td>Ch. 411 manuscript complete, 2025-12-14</td><td>197 days</td><td>2026-12-09</td></tr></table>
<p>All three historical events also have \(\Delta C=0.1\), so their coordinate weight for this one current event is \(w=\exp(0)=1\). For batch 49, for example, the event proposes \(m=\text{{2026-05-26}}+197\text{{ days}}=\text{{2026-12-09}}\). The method does <em>not</em> select one of these dates. It adds this event&rsquo;s many pair-derived kernels into \(K_{{e,49}}(s)\), combines that with kernels from every other current event into \(Q_{{49}}(s)\), and only then averages \(Q_{{47}},Q_{{48}},Q_{{49}}\).</p>
<p>This example also exposes the practical difficulty. The same visibly positive event produces implications ranging from August 2026 to December 2027 because the historical event-to-start lags vary enormously. The all-pairs method is a translation-and-averaging procedure over those lags; it is not a rule saying &ldquo;manuscript complete means publish after 197 days.&rdquo;</p>
<h4>What the functions look like after the worked event is combined</h4>
<p>A <strong>date-shaped likelihood</strong> is a non-negative function of a candidate publication date \(s\). Its height means relative compatibility with the production evidence: a date where \(L(s)=2\) is twice as compatible as one where \(L(s)=1\), before combination with Level 1. It is <em>not</em> a probability distribution, so it does not have to sum to one. It becomes a probability distribution only after multiplying by the prior and normalizing:</p>
\[P(s\mid\text{{prior, pairs}})=\frac{{P_0(s)L_{{\mathrm{{pairs}}}}(s)}}{{\sum_u P_0(u)L_{{\mathrm{{pairs}}}}(u)}}.\]
<p>\(K_{{e,h}}(s)\) is the curve for one current event against one historical batch. \(Q_h(s)\) is the average of all such event curves for that historical batch. The table records how many current events found at least one compatible pair, and how many coordinate-weighted historical pairs were used across those events.</p>
<h4>How \(\sigma_h\) is calculated</h4>
<p>For one historical batch \(h\), collect every translated date \(m_{{ehr}}\) from every retained current-event/pair match, before the \(K\) and \(Q\) averages. Let their median be \(c_h\). The column \(\sigma_h\) is the robust within-component date spread:</p>
\[c_h=\operatorname{{median}}_{{e,r}}(m_{{ehr}}),\qquad \sigma_h=\max\left(1.4826\operatorname{{median}}_{{e,r}}|m_{{ehr}}-c_h|,\;21\text{{ days}}\right).\]
<p>It is not the uncertainty of a sample mean and is not divided by \(\sqrt n\). Its job is to make every pair-derived kernel in \(K_{{e,h}}\) broad enough to reflect disagreement among the translated dates. The &ldquo;centre&rdquo; column below is \(c_h\).</p>
<h4>How the fade \(\alpha_h\) is calculated</h4>
<p>Let \(A_t\) be the issue-date used as the analog-fade boundary. For every current event, calculate the weighted probability that its matched historical kernels still lie after that boundary:</p>
\[R_{{e,h}}=\sum_{{r\in R_{{eh}}}}\widetilde w_{{ehr}}\,\overline\Phi\!\left(\frac{{A_t-m_{{ehr}}}}{{\sigma_h}}\right).\]
<p>Average that survival quantity over matched current events, then map it to a fade weight:</p>
\[R_h=\frac{{1}}{{|E_h|}}\sum_{{e\in E_h}}R_{{e,h}},\qquad \alpha_h=\frac{{R_h}}{{R_h+0.05}}.\]
<p>Thus \(\alpha_h\) is near 1 when that historical analog still places substantial kernel mass after \(A_t\), and near 0 when it is mostly overdue. In the latter case \(L_h(s)\) becomes nearly flat instead of concentrating support on a date that has already passed.</p>
<table><tr><th>Historical batch \(h\)</th><th>Centre \(c_h\)</th><th>Matched current events</th><th>Weighted pair matches</th><th>\(\sigma_h\)</th><th>Fade \(\alpha_h\)</th><th>Batch likelihood \(L_h\)</th></tr>
{all_pairs_rows}</table>
<p>Finally, the three displayed \(L_h(s)\) curves are pointwise averaged:</p>
\[L_{{\mathrm{{pairs}}}}(s)=\frac{{L_{{47}}(s)+L_{{48}}(s)+L_{{49}}(s)}}{{3}},\]
<p>then rescaled by a common positive constant for numerical convenience. That rescaling changes neither the relative likelihood across dates nor the posterior after normalization.</p>
<p>The all-pairs experiment combines this date-shaped likelihood with Level 1 as \(P_0(s)L_{{\mathrm{{pairs}}}}(s)\). A newly reported ch. 421 page can move the resulting distribution earlier or later, depending on the historical lag patterns represented in the matched pairs.</p>
<h4>Direct-target likelihood history for ch. 421</h4>
<p class="note">This plot starts on 2026-06-29, when ch. 421 first became the direct next-batch target. At each of these {pairs_n} dates, \(L_{{\mathrm{{pairs}}}}\) is normalized over still-possible WSJ issues only so that its median and central 80% date range can be shown. Level 1 is not multiplied in. Before 2026-06-29, the model&rsquo;s all-pairs likelihood concerned the preceding batch rather than ch. 421.</p>
{pairs_chart}
<h3>Selected method: two-sided ordered-readiness likelihood</h3>
<p>Work within a chapter is represented on the existing linear stage scale, while different chapters may overlap heavily. Retouch is excluded because it is rework rather than a stable forward position. Let \(p_c(t)\) be the furthest explicit non-retouch coordinate for chapter \(c\), \(A_c(t)\) indicate any such production report, and \(M_c(t)\) indicate an explicit manuscript-complete report. The order-adjusted lower bound is</p>
\[
q_c(t)=\min\left\{{1,\max\left[p_c(t),\;0.5I\!\left(\exists j>c:A_j(t)\right),\;I\!\left(\exists j>c:M_j(t)\right),\;I(c=430)M_{{430}}(t)\right]\right\}}.
\]
<p>A later chapter report therefore puts every earlier chapter at least at inking complete; a later manuscript completion puts every earlier chapter at 1. Direct observations and these inferred floors are stored separately. Batch readiness is the sum, measured in chapter-equivalents:</p>
\[B(t)=\sum_{{c=421}}^{{430}}q_c(t),\qquad 0\le B(t)\le10.\]
<p>For historical batch \(h\), define the threshold-crossing date \(T_h(b)=\inf\{{t:B_h(t)\ge b\}}\) and observed remaining time \(R_h(b)=S_h-T_h(b)\). If the current run reached \(b=B(t)\) at \(T_{{\mathrm{{now}}}}(b)\), analog \(h\) supplies the centre</p>
\[m_h(t)=T_{{\mathrm{{now}}}}(b)+R_h(b).\]
<p>The three centres enter as broad Gaussian components with a declared 120-day scale:</p>
\[L_{{\mathrm{{ready}}}}(s)=\frac1{{|H|}}\sum_{{h\in H}}\exp\left[-\frac12\left(\frac{{s-m_h(t)}}{{120\text{{ days}}}}\right)^2\right].\]
<p>One analog contributes one component and the components are averaged, not multiplied. Unlike V10&rsquo;s one-sided floor, this likelihood makes both dates that are implausibly early and dates far beyond every comparable readiness trajectory less compatible. The 120-day width is deliberately broad because only three independent production-era analogs exist.</p>
<h4>Readiness diagnostics</h4>
<p class="note">These {feasibility_diag_n} snapshots show the ordered readiness input on a 0&ndash;10 scale and the corresponding V10 floor dates retained for comparison. The selected V11 likelihood uses two-sided components centred on the analog-implied dates rather than the displayed one-sided ramps.</p>
{feasibility_floor_chart}
{readiness_chart}
<h3>Reader-facing batch-progress chart</h3>
<p>The homepage timeline uses the same ordered coordinates \(q_c(t)\) as the statistical model. For display as a percentage only, it normalizes the batch sum:</p>
\[
B_{{\mathrm{{chart}}}}(t)=\frac{{B(t)}}{{10}}=\frac1{{10}}\sum_{{c=421}}^{{430}}q_c(t).
\]
<p>The daily trace begins <em>after</em> the first available report has been incorporated. For example, the first retained ch. 391&ndash;400 report is a page log for ch. 397; it therefore begins with ch. 391&ndash;396 inferred to (0.5), rather than at zero. That early batch remains incomplete: the first report is not necessarily the true beginning of its production.</p>
<h2>7. Selected posterior</h2>
<p>The selected posterior combines the historical prior, the two-sided ordered-readiness likelihood, and the factual non-publication floor:</p>
\[P(S_{{421}}=s\mid\mathcal D_t)\propto P_0(s)L_{{\mathrm{{ready}}}}(s\mid B(t))I(s>F_t).\]
<p>The distribution can move when readiness changes and when an eligible issue passes without ch. 421. A missed issue is publication information, not a claim that production slowed.</p>
<h3>Final prediction history for ch. 421</h3>
<p class="note">This fixed-target replay shows the final combined V11 posterior at {posterior_history_n} historical forecast dates. It includes Level 1, the two-sided ordered-readiness likelihood, and the non-publication floor. The teal line is the median predicted publication date; the shaded band is the central 80% interval.</p>
{posterior_history_chart}
<h2>8. Later chapters</h2>
<p>Once the start issue is estimated, ch. 422&ndash;430 are derived from a shared batch-level cadence regime. Fourteen of fifteen completed modeling-era batches were consecutive. The only disrupted batch contained both exceptional intervals: one extra issue before its sixth chapter and another before its ninth. The model therefore draws one regular-or-disrupted regime for the whole batch rather than nine independent skip events.</p>
\[P(Z_b=\mathrm{{disrupted}})=1/15,\qquad P(Z_b=\mathrm{{regular}})=14/15.\]
<p>Conditional on the regular regime, chapter \(k\) appears \(k-1\) eligible issue slots after the start. Conditional on the disrupted regime, the observed shared delay pattern is applied. Nearly all marginal uncertainty still comes from the unknown batch start.</p>
<p>Ch. 431 and later require a further, unobserved batch gap. That secondary forecast is intentionally kept broad. Production events for ch. 431&ndash;440 are not reused as a date likelihood without a separately validated model for that question.</p>
<h2>9. The 200-issue horizon</h2>
<p><strong>This is a pragmatic computation bound, not a fitted claim.</strong> The largest observed positive gap is 184 issues; 200 adds a 16-issue margin. Once a hiatus exceeds the observed range, the model is explicitly extrapolating. A future revision should replace this cutoff with a tested tail model or a separately stated long-hiatus assumption.</p>
</main></body></html>'''
    path = D("site", "research-methods.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(page)
    return path


if __name__ == "__main__":
    print("site: %s" % os.path.relpath(build(), D()))
