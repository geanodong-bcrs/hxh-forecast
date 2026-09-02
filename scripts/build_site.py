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

from build_readiness import progress_of, ordered_trace

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

    def is_live(f):
        """The site reports the CURRENT forecast, never a reconstructed one."""
        try:
            with open(f, encoding="utf-8") as fh:
                return json.load(fh).get("provenance") != "replay"
        except Exception:
            return False
    files = [f for f in files if is_live(f)]
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

    Cumulative, and paired with `pdf_chart` below. Per-issue a density really is
    one spike and a hundred invisible bars — half the mass sits on a single
    issue — but binned by month the spike is only ~8x its neighbour and the tail
    reads fine, so both views are now shown. This one answers "have we got there
    yet"; the density answers "where is the mass".

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


def pdf_chart(pmf, median, i80, spike=None, width=720, height=210, clip=0.99):
    """Probability density: where the mass actually sits, by month.

    Same x-axis as `cdf_chart` — same source pmf, same 0.99 clip — so the two
    charts stack and read as one picture. Binned by calendar month because the
    raw pmf is per weekly issue, and per-issue bars are unreadable: the first
    eligible issue alone carries ~50% while the other 115 issues average 0.4%,
    a 126:1 range that leaves the tail at one pixel. Monthly bins bring that to
    about 8:1, which a linear axis shows honestly.

    The spike is still the story, so the month holding it is labelled with the
    single-issue probability rather than letting the bin hide it.
    """
    if not pmf:
        return ""
    acc, cum = 0.0, []
    for d, p in pmf:
        acc += p
        cum.append((d, p, acc))
    cutoff = next((i for i, (_, _, c) in enumerate(cum) if c >= clip), len(cum) - 1)
    cum = cum[:cutoff + 1]

    bins = OrderedDict()
    for d, p, _ in cum:
        k = d[:7]
        bins[k] = bins.get(k, 0.0) + p
    if not bins:
        return ""

    pad_l, pad_r, pad_t, pad_b = 44, 16, 16, 40
    W, H = width - pad_l - pad_r, height - pad_t - pad_b
    x0 = date.fromisoformat(cum[0][0]).toordinal()
    x1 = date.fromisoformat(cum[-1][0]).toordinal()
    span = max(x1 - x0, 1)
    X = lambda o: pad_l + W * (min(max(o, x0), x1) - x0) / span
    top = max(bins.values())
    Y = lambda p: pad_t + H * (1 - p / top)

    g = []
    step = .1 if top > .25 else .02
    v = 0.0
    while v <= top + 1e-9:
        g.append('<line class="grid" x1="%d" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                 '<text class="ax" x="%d" y="%.1f" text-anchor="end">%d%%</text>'
                 % (pad_l, Y(v), pad_l + W, Y(v), pad_l - 6, Y(v) + 4, round(v * 100)))
        v += step
    for d, label in month_ticks(x0, x1):
        xx = X(d.toordinal())
        g.append('<line class="grid%s" x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>'
                 % (" yr" if d.month == 1 else "", xx, pad_t, xx, pad_t + H))
        if label:
            g.append('<text class="ax" x="%.1f" y="%d" text-anchor="middle">%s</text>'
                     % (xx, height - 22, d.strftime("%b")))
    for yr in range(date.fromordinal(x0).year, date.fromordinal(x1).year + 1):
        lo, hi = max(x0, date(yr, 1, 1).toordinal()), min(x1, date(yr, 12, 31).toordinal())
        if hi <= lo or X(hi) - X(lo) < 34:
            continue
        g.append('<text class="ax yr" x="%.1f" y="%d" text-anchor="middle">%d</text>'
                 % ((X(lo) + X(hi)) / 2, height - 7, yr))

    bars, spike_lbl = [], ""
    for k, p in bins.items():
        y, m = int(k[:4]), int(k[5:7])
        b0 = max(x0, date(y, m, 1).toordinal())
        b1 = min(x1, (date(y + (m == 12), (m % 12) + 1, 1) - timedelta(days=1)).toordinal())
        xa, xb = X(b0), X(b1)
        w = max(xb - xa - 1.5, 1)
        bars.append('<rect class="bar" x="%.1f" y="%.1f" width="%.1f" height="%.1f">'
                    '<title>%s — %s</title></rect>'
                    % (xa + .75, Y(p), w, max(pad_t + H - Y(p), .5),
                       date(y, m, 1).strftime("%B %Y"), pct(p)))
        if spike and spike[0][:7] == k:
            # The spike month is the tallest bar, so a label above it would sit
            # outside the plot. Put it beside the bar instead, at the bar's top.
            spike_lbl = ('<text class="ax spk" x="%.1f" y="%.1f">'
                         '%s of it is %s alone</text>'
                         % (xa + w + 7, max(Y(p) + 11, pad_t + 11),
                            pct(spike[1]), fmt(spike[0], True)))

    lo, hi = (date.fromisoformat(i80[0]).toordinal(),
              date.fromisoformat(i80[1]).toordinal())
    med = date.fromisoformat(median).toordinal()
    return """<svg viewBox="0 0 %d %d" class="chart" role="img"
   aria-label="Probability chapter is published in each month">
  <rect class="band" x="%.1f" y="%d" width="%.1f" height="%d"/>
  %s
  %s
  <line class="med" x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>
  %s
</svg>""" % (width, height, X(lo), pad_t, max(X(hi) - X(lo), 1), H,
             "\n  ".join(g), "".join(bars), X(med), pad_t, X(med), pad_t + H,
             spike_lbl)


def posterior_series(chapter, direct_only=False):
    """Every posterior snapshot's forecast FOR ONE CHAPTER, oldest first.

    Not the batch-start forecast. Over a two-year replay chapter 421 sits first
    in the batch after next, then in the next batch, and only lately IS the batch
    start — so the series has to be pulled per chapter, from whichever
    ten-chapter forecast contains it, and the probabilities from
    `p_by_chapter`. Reading `median` / `p_started_by` off the snapshot instead
    would silently switch to a different chapter partway along the axis.
    """
    out = []
    for path in glob.glob(D("data", "forecasts", "*_posterior.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            continue
        rid = d.get("run_id")
        if not rid:
            continue
        t = None
        for f in ("%Y%m%dT%H%M%SZ", "%Y-%m-%d"):
            try:
                t = datetime.strptime(rid, f)
                break
            except ValueError:
                pass
        if t is None:
            continue
        row = None
        for src in ((d.get("ten_chapter_forecast") or []),
                    ((d.get("next_batch") or {}).get("ten_chapter_forecast") or [])):
            for r in src:
                if r.get("chapter") == chapter:
                    row = r
        if not row:
            continue
        direct = ("publication of ch %d" % chapter) in (d.get("target") or "")
        out.append({"t": t, "median": row["median"], "i80": row.get("i80"),
                    "p_by": (d.get("p_by_chapter") or {}).get(str(chapter)) or {},
                    "replay": d.get("provenance") == "replay",
                    "model": d.get("level2_design") or "legacy_v1",
                    "asof": d.get("replay_asof") or d.get("forecast_timestamp"),
                    "target": d.get("target") or "", "direct": direct,
                    "exhausted": d.get("exhausted_analogs") or []})
    if direct_only:
        out = [r for r in out if r["direct"]]
    # Revision snapshots are append-only, so preserve the old record on disk
    # but do not draw two incompatible models as one apparent time series.
    for model in ("ordered_readiness_two_sided_mixture_v11",
                  "ordered_readiness_feasibility_floor_v10",
                  "readiness_feasibility_floor_v9",
                  "all_pairs_coordinate_likelihood_v9_mixture_level1",
                  "all_pairs_coordinate_likelihood_v8_parametric_level1_frozen_fade",
                  "all_pairs_coordinate_likelihood_v7_smooth_zero_gaps_censored",
                  "all_pairs_coordinate_likelihood_v7_direct_two_gap_censored",
                  "all_pairs_coordinate_likelihood_v7_direct_two_gap",
                  "all_pairs_coordinate_likelihood_v6_buffer_mixture",
                  "all_pairs_coordinate_likelihood_v6_predecessor_gated",
                  "all_pairs_coordinate_likelihood_v6_continuous_no_start",
                  "all_pairs_coordinate_likelihood_v5",
                  "readiness_coordinate_context_record_hiatus_v4",
                  "readiness_coordinate_context_analog_v3",
                  "readiness_coordinate_analog_v2"):
        if any(r["model"] == model for r in out):
            out = [r for r in out if r["model"] == model]
            break
    out.sort(key=lambda r: r["t"])
    return out


def _pmf_quantile(pmf, q):
    """Return a date quantile from a (date-string, probability) PMF."""
    total = sum(p for _, p in pmf)
    if total <= 0:
        return None
    running = 0.0
    for d, p in pmf:
        running += p / total
        if running >= q:
            return d
    return pmf[-1][0]


def level1_prior_series():
    """Historical Level-1-only forecast, with already-passed issues censored.

    This deliberately reads `prior_pmf`, before the production-event likelihood
    is applied.  The truncation is not Level 2: an issue before the replay date
    cannot still be the next publication, so its mass is removed and the
    remaining Level-1 distribution is renormalized.
    """
    out = []
    for path in glob.glob(D("data", "forecasts", "*_posterior.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            continue
        rid = d.get("run_id")
        if not rid:
            continue
        try:
            t = datetime.strptime(rid, "%Y%m%dT%H%M%SZ")
        except ValueError:
            continue
        pmf = d.get("prior_pmf") or []
        floor = d.get("truncation_floor")
        if not pmf or not floor:
            continue
        # Saved priors are over candidate publication dates.  Dropping past
        # dates produces the usable prior at that moment, without consulting
        # any Togashi production event or the Level-2 posterior.
        usable = [(dte, float(p)) for dte, p in pmf if dte >= floor]
        median = _pmf_quantile(usable, .5)
        if not median:
            continue
        out.append({"t": t, "median": median,
                    "i80": [_pmf_quantile(usable, .1), _pmf_quantile(usable, .9)],
                    "replay": d.get("provenance") == "replay",
                    "model": d.get("level2_design") or "legacy_v1",
                    "target": d.get("target") or ""})
    # These diagnostics deliberately replay the currently published model
    # (V4), not an experimental local revision.  The 20:55 IDs are append-only
    # diagnostic replays of that exact public code and public input state.
    out = [r for r in out if r["model"] == "readiness_coordinate_context_record_hiatus_v4"
           and r["t"].strftime("%H%M%S") == "205500"]
    out.sort(key=lambda r: r["t"])
    return out


def level1_prior_chart():
    rows = level1_prior_series()
    if len(rows) < 2:
        return []
    return [
        '<h2>Level 1 in isolation</h2>',
        '<h3>Prior median over time — no production evidence</h3>',
        '<p class=note>This is the median of the historical publication prior '
        'alone. Already-passed issues are removed, but no Togashi update, chapter '
        'coordinate, or other Level 2 likelihood is used. The target is whichever '
        'next batch was being forecast on that date.</p>',
        zoomed(lambda rr: fan_chart(rr, annotations=None), rows, name="level1-prior"),
    ]


def level2_likelihood_series():
    """Exact Level-2 likelihood from the published-model diagnostic replay."""
    out = []
    for path in glob.glob(D("data", "forecasts", "*_posterior.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            continue
        try:
            t = datetime.strptime(d.get("run_id", ""), "%Y%m%dT%H%M%SZ")
        except ValueError:
            continue
        floor = d.get("truncation_floor")
        candidates = [(dte, float(p)) for dte, p in (d.get("level2_likelihood_pmf") or [])
                      if dte >= (floor or "9999-12-31")]
        if not candidates:
            continue
        median = _pmf_quantile(candidates, .5)
        if not median:
            continue
        out.append({"t": t, "median": median,
                    "i80": [_pmf_quantile(candidates, .1), _pmf_quantile(candidates, .9)],
                    "replay": d.get("provenance") == "replay",
                    "model": d.get("level2_design") or "legacy_v1"})
    out = [r for r in out if r["model"] == "readiness_coordinate_context_record_hiatus_v4"
           and r["t"].strftime("%H%M%S") == "205500"]
    out.sort(key=lambda r: r["t"])
    return out


def level2_likelihood_chart():
    rows = level2_likelihood_series()
    if len(rows) < 2:
        return []
    return [
        '<h2>Level 2 in isolation</h2>',
        '<h3>Production-likelihood median over time — no publication prior</h3>',
        '<p class=note>This normalizes the production-evidence likelihood by '
        'itself after removing already-passed issues; it does not multiply in '
        'the Level 1 publication prior. It is an exact replay of the current '
        'published model, rather than a reconstructed approximation.</p>',
        zoomed(lambda rr: fan_chart(rr, annotations=None), rows, name="level2-likelihood"),
    ]


def history_changes(rows, threshold_days=45):
    """Large median moves, labelled by the evidence available that day."""
    events = {}
    path = D("data", "processed", "production_events.csv")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for e in csv.DictReader(fh):
                if e.get("event_class") in {"chapter_stage", "batch_scope", "disruption"}:
                    events.setdefault(e.get("event_date"), []).append(e)
    stage = {"character_inking": "inking", "panel_layout": "panel layout",
             "bg_spec": "background specification", "bg_work": "background work",
             "dialogue": "dialogue", "retouch": "retouch",
             "manuscript_complete": "manuscript complete", "name": "name work"}
    out = []
    for before, after in zip(rows, rows[1:]):
        delta = date.fromisoformat(after["median"]).toordinal() - date.fromisoformat(before["median"]).toordinal()
        target_changed = before["target"] != after["target"]
        exhausted_changed = before["exhausted"] != after["exhausted"]
        if abs(delta) < threshold_days and not target_changed and not exhausted_changed:
            continue
        es = events.get(after.get("asof"), [])
        if target_changed:
            label, kind = "batch 49 begins", "publication"
        elif es:
            e = es[0]
            if e.get("event_class") == "chapter_stage":
                label = "ch. %s: %s %s" % (e.get("chapter"), stage.get(e.get("stage"), e.get("stage")), e.get("status") or "reported")
            elif e.get("event_class") == "batch_scope":
                label = "batch-level %s" % stage.get(e.get("stage"), "work")
            else:
                label = "production disruption"
            kind = "tweet"
        elif exhausted_changed:
            label, kind = "no start: analog status changes", "conditioning"
        else:
            label, kind = "no start: floor advances", "conditioning"
        out.append({"t": after["t"], "median": after["median"], "label": label,
                    "kind": kind, "delta": delta})
    return out


def manuscript_completion_annotations(rows):
    """Major, hoverable evidence marks for a prediction-history chart.

    The line may move after any production report, and manuscript completion is
    not irreversible (a retake can follow it).  To avoid pretending every move
    has an obvious single cause, mark only this late, reader-legible milestone.
    """
    dates = {r.get("asof"): r for r in rows}
    out, seen = [], set()
    with open(D("data", "processed", "production_events.csv"), encoding="utf-8") as fh:
        for e in csv.DictReader(fh):
            if (e.get("event_class") != "chapter_stage" or
                    e.get("stage") != "manuscript_complete" or
                    e.get("status") != "complete" or
                    not e.get("chapter") or e.get("event_date") not in dates):
                continue
            key = (e["event_date"], e["chapter"])
            if key in seen:
                continue
            seen.add(key)
            r = dates[e["event_date"]]
            out.append({"t": r["t"], "median": r["median"],
                        "label": "Chapter %s: manuscript complete" % e["chapter"]})
    return out


def event_only_series(rows):
    """Hold production evidence fixed between events for a decomposition chart.

    The full series still conditions on every issue known not to contain the
    batch.  The dashed line instead holds the last event-time posterior, making
    the remaining movement attributable to that factual no-start update.
    """
    event_days = set()
    path = D("data", "processed", "production_events.csv")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for e in csv.DictReader(fh):
                if e.get("event_class") in {"chapter_stage", "page_completed", "batch_scope", "disruption"}:
                    event_days.add(e.get("event_date"))
    out, held, previous_target = [], None, None
    for r in rows:
        update = r.get("asof") in event_days or r.get("target") != previous_target
        if held is None or update:
            held = r
        x = dict(r)
        x["event_only_median"] = held["median"]
        out.append(x)
        previous_target = r.get("target")
    return out


def time_ticks(t0, t1):
    """Ticks across a datetime span. Every label carries a four-digit year:
    "Sep 26" reads as a day in September, which is exactly the ambiguity to
    avoid on a chart whose other axis is also dates."""
    days = (t1 - t0).total_seconds() / 86400.0
    out = []
    if days > 70:
        every = 3 if days > 400 else (2 if days > 200 else 1)
        d, n = date(t0.year, t0.month, 1), 0
        while d <= t1.date():
            if d >= t0.date() and n % every == 0:
                out.append((d, d.strftime("%b %Y")))
            d = date(d.year + (d.month == 12), (d.month % 12) + 1, 1)
            n += 1
    else:
        d = t0.date()
        d += timedelta(days=(7 - d.weekday()) % 7)
        while d <= t1.date():
            out.append((d, d.strftime("%-d %b %Y")))
            d += timedelta(days=14 if days > 40 else 7)
    return out


def readiness_path(first_chapter, end_date, extend_to_end=False):
    """Ordered, reported batch progress for the factual comparison chart.

    This is intentionally separate from the forecasting model's readiness
    coordinate. It encodes the user-facing observation that chapters overlap,
    but the same stage moves forward in chapter order.
    """
    events = []
    with open(D("data", "processed", "production_events.csv"), encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if not row.get("chapter") or not row.get("event_date"):
                continue
            try:
                chapter = int(float(row["chapter"]))
            except ValueError:
                continue
            if not first_chapter <= chapter < first_chapter + 10:
                continue
            when = date.fromisoformat(row["event_date"])
            if when > end_date:
                continue
            events.append(row)
    if not events:
        return None
    traced = ordered_trace(events, range(first_chapter, first_chapter + 10), end_date)
    if not traced:
        return None
    origin = traced[0][0]
    path = [((when - origin).days, total / 10.0) for when, total, _ in traced]
    end_elapsed = (end_date - origin).days
    if extend_to_end and path[-1][0] != end_elapsed:
        path.append((end_elapsed, path[-1][1]))
    return {"origin": origin, "end": end_date, "path": path}


def resolved_batch_runs():
    """Publication dates for each 2007-onward, numbered batch."""
    batches = {}
    with open(D("data", "processed", "chapters.csv"), encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if not row.get("batch_id") or not row.get("publication_date_jp"):
                continue
            batch = int(row["batch_id"])
            chapter = int(row["chapter"])
            when = date.fromisoformat(row["publication_date_jp"])
            position = int(row.get("position_in_batch") or 1)
            batches.setdefault(batch, []).append((chapter, position, when))
    out = {}
    for batch, rows in batches.items():
        rows.sort(key=lambda r: r[1])
        out[batch] = {"first": min(r[0] for r in rows),
                      "publication": [(r[1], r[2]) for r in rows],
                      "end": max(r[2] for r in rows)}
    return out


def readiness_comparison_chart(post):
    """Public progress paths, aligned at each run's first observed event."""
    first = int(post["target"].split("ch ")[-1])
    asof = date.fromisoformat(post["forecast_timestamp"])
    runs = resolved_batch_runs()
    series = []
    for batch, css in ((47, "r47"), (48, "r48"), (49, "r49")):
        if batch not in runs:
            continue
        run = runs[batch]
        # Batch 49 is still publishing. Extend its production trace through
        # the current date, while its publication trace uses only issues that
        # have actually appeared.
        end = asof if batch == 49 else run["end"]
        path = readiness_path(run["first"], end)
        if path:
            series.append({"label": "ch. %d–%d" % (run["first"], run["first"] + 9),
                           "css": css, "path": path, "publication": run["publication"],
                           "legend_suffix": " · publishing now" if batch == 49 else " · published"})
    live = readiness_path(first, asof)
    if not live:
        return []
    series.append({"label": "ch. %d–%d" % (first, first + 9),
                   "css": "rlive", "path": live, "publication": [],
                   "legend_suffix": " (working)"})
    xmax = max(
        [s["path"]["path"][-1][0] for s in series] +
        [(when - s["path"]["origin"]).days for s in series for _, when in s["publication"]]
    )
    xmax = max(180, int((xmax + 89) // 90) * 90)

    width, height = 720, 300
    pad_l, pad_r, pad_t, pad_b = 52, 16, 30, 54
    W, H = width - pad_l - pad_r, height - pad_t - pad_b
    X = lambda day: pad_l + W * day / xmax
    # This is a display scale, not a replacement for the model's coordinate.
    # Manuscript-complete is 0.90 in the source coordinate, so map it to the
    # visible upper edge of the Togashi-work phase (1.00). The publication
    # process occupies the separate 1.00–1.10 band.
    Y = lambda value: pad_t + H * (1 - value / 1.10)
    grid = []
    # The 1.00-1.10 band is WSJ publication, a separate phase rather than
    # progress past 100%. Shade it, and draw it first so the rules sit on top.
    grid.append('<rect class="pubband" x="%d" y="%.1f" width="%d" height="%.1f"/>'
                % (pad_l, Y(1.10), W, Y(1.00) - Y(1.10)))
    grid.append('<text class="ax" x="%.1f" y="%.1f">publishing phase</text>'
                % (pad_l + 8, (Y(1.00) + Y(1.10)) / 2 + 4))
    for value in (0, .25, .5, .75):
        grid.append('<line class="grid" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>'
                    '<text class="ax" x="%d" y="%.1f" text-anchor="end">%d%%</text>'
                    % (pad_l, Y(value), pad_l + W, Y(value), pad_l - 6,
                       Y(value) + 4, round(value * 100)))
    # 100% is labelled but deliberately not ruled: a full-width line at 1.00 ran
    # along the ch. 391-400 plateau, and the shaded band's edge already marks it.
    grid.append('<text class="ax" x="%d" y="%.1f" text-anchor="end">100%%</text>'
                % (pad_l - 6, Y(1.00) + 4))
    tick = 0
    while tick <= xmax:
        grid.append('<line class="grid" x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>'
                    '<text class="ax" x="%.1f" y="%d" text-anchor="middle">%d</text>'
                    % (X(tick), pad_t, X(tick), pad_t + H, X(tick), height - 27, tick))
        tick += 180
    if xmax % 180:
        grid.append('<line class="grid" x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>'
                    '<text class="ax" x="%.1f" y="%d" text-anchor="middle">%d</text>'
                    % (X(xmax), pad_t, X(xmax), pad_t + H, X(xmax), height - 27, xmax))

    paths, publication_paths, legend = [], [], []
    for s in series:
        points = [(day, min(value / .90, 1.0)) for day, value in s["path"]["path"]]
        d = ["M%.1f,%.1f" % (X(points[0][0]), Y(points[0][1]))]
        previous_day, previous_value = points[0]
        for day, value in points[1:]:
            d.append("L%.1f,%.1f L%.1f,%.1f" %
                     (X(day), Y(previous_value), X(day), Y(value)))
            previous_day, previous_value = day, value
        paths.append('<path class="rline %s" d="%s"/>' % (s["css"], " ".join(d)))
        publication = [(position, (when - s["path"]["origin"]).days)
                       for position, when in s["publication"]]
        if publication:
            pub_points = [(day, 1.00 + .10 * (position - 1) / 9.0)
                          for position, day in publication]
            d = ["M%.1f,%.1f" % (X(pub_points[0][0]), Y(pub_points[0][1]))]
            prev_day, prev_value = pub_points[0]
            for day, value in pub_points[1:]:
                d.append("L%.1f,%.1f L%.1f,%.1f" %
                         (X(day), Y(prev_value), X(day), Y(value)))
                prev_day, prev_value = day, value
            publication_paths.append('<path class="pline %s" d="%s"/>' % (s["css"], " ".join(d)))
        legend.append('<span><i class="dot %s"></i>%s%s</span>' %
                      (s["css"], s["label"], s["legend_suffix"]))

    chart = '''<svg viewBox="0 0 %d %d" class="chart" role="img" aria-label="Observed production and publication progress of Hunter x Hunter batches">
%s
%s%s
<text class="ax" x="%d" y="%d" text-anchor="middle">days since the first production tweet of a batch</text>
<text class="ax" x="14" y="%d" transform="rotate(-90 14 %d)" text-anchor="middle">Togashi&rsquo;s working progress</text>
</svg>''' % (width, height, "\n".join(grid), "".join(paths), "".join(publication_paths),
              pad_l + W / 2, height - 7, pad_t + H / 2, pad_t + H / 2)
    return [
        '<style>.rline,.pline{fill:none;stroke-linejoin:miter;stroke-linecap:butt;shape-rendering:crispEdges}'
        '.pubband{fill:var(--soft)}'
        '.rline{stroke-width:2.2}.pline{stroke-width:3}.rline.r47,.pline.r47{stroke:#8a5a44}.rline.r48,.pline.r48{stroke:#775b9c}'
        '.rline.r49,.pline.r49{stroke:#2c7a7b}.rline.rlive{stroke:var(--accent);stroke-width:3}'
        '.rline.rnext{stroke:#c05c22}'
        '.dot.r47{background:#8a5a44;border-color:#8a5a44}'
        '.dot.r48{background:#775b9c;border-color:#775b9c}.dot.r49{background:#2c7a7b;border-color:#2c7a7b}'
        '.dot.rlive{background:var(--accent);border-color:var(--accent)}.dot.rnext{background:#c05c22;border-color:#c05c22}.dot.pub{background:#b34070;border-color:#b34070}'
        '</style>',
        '<h2>Production progress compared with earlier batches</h2>',
        '<h3>Publicly reported production and publication progress</h3>',
        chart,
        '<div class=legend>%s</div>' % "".join(legend),
        '<p class=note><strong>Ch. 391&ndash;400 is incomplete:</strong> Togashi began '
        'posting after production of that batch had already started, so its '
        'displayed duration is a lower bound.</p>',
    ]


def _frame(rows, width, height, pad):
    pad_l, pad_r, pad_t, pad_b = pad
    W, H = width - pad_l - pad_r, height - pad_t - pad_b
    t0, t1 = rows[0]["t"], rows[-1]["t"]
    span = max((t1 - t0).total_seconds(), 1.0)
    X = lambda t: pad_l + W * (t - t0).total_seconds() / span
    g = []
    for d, label in time_ticks(t0, t1):
        xx = X(datetime(d.year, d.month, d.day))
        g.append('<line class="grid" x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>'
                 % (xx, pad_t, xx, pad_t + H))
        g.append('<text class="ax" x="%.1f" y="%d" text-anchor="middle">%s</text>'
                 % (xx, height - 8, label))
    return (pad_l, pad_r, pad_t, pad_b, W, H, X, g)


def fan_chart(rows, annotations=None, width=720, height=250):
    """Predicted publication date for one chapter, as the forecast has moved.

    One line: the median predicted date.  The y axis is inverted on purpose —
    further into the future sits LOWER, so a line rising means the forecast
    moved nearer, the same reading as a price chart.
    """
    rows = [r for r in rows if r.get("i80")]
    if len(rows) < 2:
        return ""
    # Keep the plotting frame as wide as the other figures.  The one remaining
    # series label sits inside the right edge rather than consuming a wide gutter.
    pad = (62, 16, 14, 26)
    pad_l, pad_r, pad_t, pad_b, W, H, X, g = _frame(rows, width, height, pad)

    O = lambda ds: date.fromisoformat(ds).toordinal()
    vals = [O(r["median"]) for r in rows]
    y0, y1 = min(vals), max(vals)
    pad_y = max((y1 - y0) * 0.07, 3)
    y0, y1 = y0 - pad_y, y1 + pad_y
    Y = lambda o: pad_t + H * (o - y0) / max(y1 - y0, 1)

    for frac in (0, .25, .5, .75, 1):
        o = y0 + (y1 - y0) * frac
        g.append('<line class="grid" x1="%d" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                 '<text class="ax" x="%d" y="%.1f" text-anchor="end">%s</text>'
                 % (pad_l, Y(o), pad_l + W, Y(o), pad_l - 6, Y(o) + 4,
                    date.fromordinal(int(o)).strftime("%b %Y")))

    body, labels = [], []
    for key, cls, name in ((lambda r: r["median"], "cdfline", "median"),):
        pts = [(X(r["t"]), Y(O(key(r)))) for r in rows]
        body.append('<path class="%s" d="M%s"/>'
                    % (cls, " L".join("%.1f,%.1f" % p for p in pts)))
        labels.append([pts[-1][1], "%s &middot; %s" % (name, fmt(key(rows[-1])))])

    for a in annotations or []:
        if not (rows[0]["t"] <= a["t"] <= rows[-1]["t"]):
            continue
        xx, yy = X(a["t"]), Y(O(a["median"]))
        body.append('<circle cx="%.1f" cy="%.1f" r="6" fill="var(--pend)" '
                    'stroke="var(--bg)" stroke-width="2"><title>%s</title></circle>'
                    % (xx, yy, esc(a["label"])))

    labels.sort()
    if len(labels) > 1 and labels[1][0] - labels[0][0] < 13:
        labels[1][0] = labels[0][0] + 13
    for y, txt in labels:
        body.append('<text class="ax lbl" x="%.1f" y="%.1f" text-anchor="end">%s</text>'
                    % (pad_l + W - 6, y + 4, txt))

    live = next((r for r in rows if not r["replay"]), None)
    if live and live is not rows[0]:
        xx = X(live["t"])
        body.append('<line class="boundary" x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>'
                    '<text class="ax bd" x="%.1f" y="%d" text-anchor="end">'
                    'live record &#8594;</text>'
                    % (xx, pad_t, xx, pad_t + H, xx - 5, pad_t + H - 5))
    return ('<svg viewBox="0 0 %d %d" class="chart" role="img" aria-label='
            '"Median predicted publication date over time">'
            '%s%s</svg>' % (width, height, "\n".join(g), "".join(body)))


def decomposition_chart(rows, width=720, height=230):
    """Full median versus the same history frozen between evidence updates."""
    if len(rows) < 2:
        return ""
    pad = (62, 132, 14, 26)
    pad_l, pad_r, pad_t, pad_b, W, H, X, g = _frame(rows, width, height, pad)
    O = lambda ds: date.fromisoformat(ds).toordinal()
    vals = [O(r["median"]) for r in rows] + [O(r["event_only_median"]) for r in rows]
    y0, y1 = min(vals), max(vals)
    extra = max((y1 - y0) * .07, 3)
    y0, y1 = y0 - extra, y1 + extra
    Y = lambda o: pad_t + H * (o - y0) / max(y1 - y0, 1)
    for frac in (0, .25, .5, .75, 1):
        o = y0 + (y1 - y0) * frac
        g.append('<line class="grid" x1="%d" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                 '<text class="ax" x="%d" y="%.1f" text-anchor="end">%s</text>'
                 % (pad_l, Y(o), pad_l + W, Y(o), pad_l - 6, Y(o) + 4,
                    date.fromordinal(int(o)).strftime("%b %Y")))
    body = []
    for n, (key, stroke, dash, label) in enumerate((("event_only_median", "var(--mut)", "4 3", "event-only"),
                                                     ("median", "var(--accent)", "", "full real-time"))):
        pts = [(X(r["t"]), Y(O(r[key]))) for r in rows]
        dash_attr = ' stroke-dasharray="%s"' % dash if dash else ""
        body.append('<path d="M%s" fill="none" stroke="%s" stroke-width="2"%s/>'
                    % (" L".join("%.1f,%.1f" % p for p in pts), stroke, dash_attr))
        body.append('<text class="ax lbl" x="%.1f" y="%.1f">%s</text>'
                    % (pad_l + W + 6, pts[-1][1] + 4 + (12 if n else 0), label))
    return ('<svg viewBox="0 0 %d %d" class="chart" role="img" aria-label='
            '"Full real-time forecast compared with forecast frozen between public evidence updates">'
            '%s%s</svg>' % (width, height, "\n".join(g), "".join(body)))


def prob_chart(rows, horizons, width=720, height=230):
    """P(chapter published by <quarter end>), as it has moved over time.

    The horizons are nested, so the series are ordered, not categorical: a
    single-hue ramp, highest contrast against the surface for the nearest
    horizon. The lines cannot cross, so position plus a direct label carries
    identity without relying on colour.
    """
    rows = [r for r in rows if r.get("p_by")]
    if len(rows) < 2:
        return ""
    pad = (44, 124, 14, 26)
    pad_l, pad_r, pad_t, pad_b, W, H, X, g = _frame(rows, width, height, pad)
    Y = lambda p: pad_t + H * (1 - p)

    for p in (0, .25, .5, .75, 1):
        g.append('<line class="grid" x1="%d" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                 '<text class="ax" x="%d" y="%.1f" text-anchor="end">%d%%</text>'
                 % (pad_l, Y(p), pad_l + W, Y(p), pad_l - 6, Y(p) + 4, int(p * 100)))

    body, labels = [], []
    for i, hz in enumerate(horizons):
        pts = [(X(r["t"]), Y(r["p_by"][hz])) for r in rows if hz in r["p_by"]]
        if len(pts) < 2:
            continue
        body.append('<path class="qline q%d" d="M%s"/>'
                    % (i + 1, " L".join("%.1f,%.1f" % p for p in pts)))
        last = next(r for r in reversed(rows) if hz in r["p_by"])
        labels.append([pts[-1][1], "by %s &middot; %s"
                       % (date.fromisoformat(hz).strftime("%b %Y"),
                          pct(last["p_by"][hz]))])
    labels.sort()
    for j in range(1, len(labels)):
        if labels[j][0] - labels[j - 1][0] < 13:
            labels[j][0] = labels[j - 1][0] + 13
    for y, txt in labels:
        body.append('<text class="ax lbl" x="%.1f" y="%.1f">%s</text>'
                    % (pad_l + W + 6, min(y + 4, pad_t + H + 4), txt))

    live = next((r for r in rows if not r["replay"]), None)
    if live and live is not rows[0]:
        xx = X(live["t"])
        body.append('<line class="boundary" x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>'
                    % (xx, pad_t, xx, pad_t + H))
    return ('<svg viewBox="0 0 %d %d" class="chart" role="img" aria-label='
            '"Probability of publication by each quarter end, over time">'
            '%s%s</svg>' % (width, height, "\n".join(g), "".join(body)))


def gap_prior_chart(pri, width=720, height=280, clip=200):
    """The Level 1 prior in GAP space — the object the model constructs.

    Not the same picture as the CDF/PDF on the front page: those are the prior
    and posterior mapped onto calendar dates. This is P(gap = g issues) before
    any of that, which is the view for reviewing the prior itself, because the
    point mass and the smoothed component stay separable.

    y is scaled to the smoothed component. The point mass is 22x the density
    peak, so drawing both to scale would leave the curve at a few pixels; the
    bar is clipped with a break and labelled instead. The rug underneath is the
    sixteen observations, drawn at their cluster weight — the three zeros are
    two effective observations, which is where pi0 comes from.
    """
    pmf = pri.get("gap_pmf") or []
    obs = pri.get("gap_observations") or []
    if not pmf:
        return ""
    pi0 = float(pri.get("pi0") or 0.0)
    bw = pri.get("bandwidth_issues")
    dens = [(g, p) for g, p in pmf if 1 <= g <= clip]
    if not dens:
        return ""

    pad_l, pad_r, pad_t, pad_b = 52, 20, 22, 46
    W, H = width - pad_l - pad_r, height - pad_t - pad_b
    rug_h = 14
    PH = H - rug_h                      # plot height above the rug strip
    X = lambda g: pad_l + W * min(g, clip) / float(clip)
    top = max(p for _, p in dens) * 1.15
    Y = lambda p: pad_t + PH * (1 - p / top)

    g = []
    step = 0.002
    v = 0.0
    while v <= top:
        g.append('<line class="grid" x1="%d" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                 '<text class="ax" x="%d" y="%.1f" text-anchor="end">%.1f%%</text>'
                 % (pad_l, Y(v), pad_l + W, Y(v), pad_l - 6, Y(v) + 4, v * 100))
        v += step
    for gg in range(0, clip + 1, 25):
        g.append('<line class="grid" x1="%.1f" y1="%d" x2="%.1f" y2="%.1f"/>'
                 '<text class="ax" x="%.1f" y="%d" text-anchor="middle">%d</text>'
                 % (X(gg), pad_t, X(gg), pad_t + PH, X(gg), height - 26, gg))
    g.append('<text class="ax" x="%.1f" y="%d" text-anchor="middle">'
             'gap before the next batch, in Jump issues skipped</text>'
             % (pad_l + W / 2, height - 8))

    area = ["M%.1f,%.1f" % (X(dens[0][0]), Y(0))]
    area += ["L%.1f,%.1f" % (X(gg), Y(p)) for gg, p in dens]
    area.append("L%.1f,%.1f Z" % (X(dens[-1][0]), Y(0)))
    body = ['<path class="area" d="%s"/>' % " ".join(area),
            '<path class="cdfline" d="M%s"/>'
            % " L".join("%.1f,%.1f" % (X(gg), Y(p)) for gg, p in dens)]

    # the point mass, clipped with a break rather than drawn to scale
    bx, bw_px = X(0), 13.0
    body.append('<rect class="bar pi0" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
                % (bx - bw_px / 2, pad_t + 8, bw_px, pad_t + PH - pad_t - 8))
    body.append('<path class="brk" d="M%.1f,%.1f l%.1f,-4 l%.1f,8 l%.1f,-4"/>'
                % (bx - bw_px / 2, pad_t + 14, bw_px / 3, bw_px / 3, bw_px / 3))
    body.append('<text class="ax spk" x="%.1f" y="%d">'
                '&#960;&#8320; = %s on gap 0 &mdash; the next batch follows with no '
                'break at all</text>' % (bx + bw_px, pad_t + 10, pct(pi0)))

    # rug: one tick per observation, height by cluster weight
    ry = pad_t + PH
    for b, gg, wgt in obs:
        if gg > clip:
            continue
        h = 5 + 8 * float(wgt)
        body.append('<line class="rug" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f">'
                    '<title>batch %s &middot; gap %s issues &middot; weight %s</title>'
                    '</line>' % (X(gg), ry + rug_h - h, X(gg), ry + rug_h, b, gg, wgt))
    if bw:
        body.append('<text class="ax" x="%.1f" y="%d" text-anchor="end">'
                    'kernel bandwidth %g issues</text>'
                    % (pad_l + W, pad_t - 8, bw))

    return ('<svg viewBox="0 0 %d %d" class="chart" role="img" aria-label='
            '"Level 1 prior over the gap in issues before the next batch">'
            '%s%s</svg>' % (width, height, "\n".join(g), "".join(body)))


def zoomed(render, rows, weeks=4, name="z"):
    """Two pre-rendered views of the same chart, toggled by a CSS radio.

    No JavaScript: the site is static HTML regenerated every run and published
    through an allowlist, and a chart toggle is not worth changing that.
    """
    cut = rows[-1]["t"] - timedelta(weeks=weeks)
    recent = [r for r in rows if r["t"] >= cut]
    full_svg = render(rows)
    if not full_svg:
        return ""
    if len(recent) < 2:
        return full_svg
    return (
        '<div class="zoom">'
        '<input type="radio" name="%s" id="%s-a" checked><input type="radio" '
        'name="%s" id="%s-b">'
        '<div class="zt"><label for="%s-a">whole run</label>'
        '<label for="%s-b">last %d weeks</label></div>'
        '<div class="za">%s</div><div class="zb">%s</div></div>'
        % (name, name, name, name, name, name, weeks, full_svg, render(recent)))


CSS = """
:root{--bg:#fff;--fg:#14161a;--mut:#697079;--line:#e4e7ec;--card:#f7f8fa;
 --accent:#2f6fd0;--band:#2f6fd01f;--ok:#1f7a4d;--pend:#c8901a;--soft:#e9edf3;
 --q1:#12408f;--q2:#2f6fd0;--q3:#6b9ce0;--q4:#8fb4e8}
@media(prefers-color-scheme:dark){:root{--bg:#0f1115;--fg:#e8eaed;--mut:#98a1ac;
 --line:#272b33;--card:#161920;--accent:#6fa8ff;--band:#6fa8ff26;--ok:#5fd39a;
 --pend:#e0b44a;--soft:#1d222b;
 --q1:#cfe0ff;--q2:#6fa8ff;--q3:#4b7fd0;--q4:#35598f}}
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
.bar{fill:var(--accent);opacity:.82}
.bar.pi0{opacity:.5}
.brk{fill:none;stroke:var(--bg);stroke-width:3}
.rug{stroke:var(--fg);stroke-width:2;opacity:.55}
.fan80{fill:var(--accent);opacity:.13;stroke:none}
.fan50{fill:var(--accent);opacity:.16;stroke:none}
.boundary{stroke:var(--mut);stroke-width:1;stroke-dasharray:2 3;opacity:.65}
.ax.bd{font-size:10px}
.ax.lbl{font-size:10.5px}
.qline{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.q1{stroke:var(--q1)}.q2{stroke:var(--q2)}.q3{stroke:var(--q3)}.q4{stroke:var(--q4)}
.zoom input{position:absolute;opacity:0;pointer-events:none}
.zoom .zt{display:flex;gap:6px;margin:12px 0 -4px}
.zoom .zt label{font-size:11.5px;padding:3px 10px;border-radius:99px;
 background:var(--soft);color:var(--mut);cursor:pointer;-webkit-user-select:none;user-select:none}
.zoom .zb{display:none}
.zoom input:nth-of-type(1):checked~.zt label[for$="-a"],
.zoom input:nth-of-type(2):checked~.zt label[for$="-b"]{
 background:var(--band);color:var(--accent);font-weight:600}
.zoom input:nth-of-type(2):checked~.za{display:none}
.zoom input:nth-of-type(2):checked~.zb{display:block}
.ax.spk{fill:var(--accent);font-weight:600}
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


def history_charts(first, post, primary=True, secondary=True, probabilities=True,
                   companion=None, direct_only=False):
    """The preserved prediction history for one chapter.

    Completion markers are deliberately evidence markers, not causal labels:
    production can be revised or retaken, so more reported completion does not
    logically guarantee an earlier publication forecast.
    """
    ser = posterior_series(first, direct_only=direct_only)
    if len(ser) < 2:
        return []
    h = []
    complete = manuscript_completion_annotations(ser)
    if primary:
        h.append('<h2>How the forecast for chapter %d has moved</h2>' % first)
        h.append('<h3>Predicted publication date over time</h3>')
        h.append(zoomed(lambda rr: fan_chart(rr, complete), ser, name="hf%d" % first))
        h.append('<p class=note>The predicted publication date for chapter %d. '
                 'Later dates sit <em>lower</em>, so a line rising means a shorter '
                 'expected wait. Amber dots are manuscript-completion reports; '
                 'hover them for the chapter. They are evidence, not guarantees: '
                 'production can be revisited or retaken, and scheduling remains '
                 'an editorial decision.</p>' % first)
    if secondary:
        decomp = event_only_series(ser)
        h.append('<h3>Forecast revisions by public evidence</h3>')
        h.append(zoomed(decomposition_chart, decomp, name="hd%d" % first))
        h.append('<p class=note>The solid line conditions on every issue publicly '
                 'known not to contain the batch. The dashed line holds the '
                 'production evidence fixed at its last update. Their separation '
                 'is the necessary effect of continued non-publication, not a '
                 'new claim that production has slowed.</p>')
        hz = [q for q in sorted((post.get("p_by_chapter") or {}).get(str(first)) or {})][:4]
        if probabilities and hz:
            h.append('<h3>Chance of publication by each quarter-end</h3>')
            h.append(zoomed(lambda rr: prob_chart(rr, hz), ser, name="hp%d" % first))
            h.append('<p class=note>The same history as probabilities: the chance '
                     'chapter %d has been published by each quarter-end.</p>' % first)
    n_rep = sum(1 for r in ser if r["replay"])
    if n_rep:
        prefix = ('The history begins once this batch became the direct next-run '
                  'forecast. ' if direct_only else '')
        h.append('<p class=note>%sThe first %d points are reconstructed from the '
                 'information public on each date; the dashed boundary marks the '
                 'live record. See <a href="method.html">method</a>.</p>' % (prefix, n_rep))
    if companion:
        href, chapter = companion
        h.append('<p class=note>Also see the preserved prediction history for '
                 '<a href="%s">chapter %d &rarr;</a></p>' % (href, chapter))
    return h


def forecast_tables(post, first, nfirst, current=True, following=True):
    """Repeat the two forecast tables on both reader-facing forecast pages."""
    h = []
    if current:
        h += ['<h2>Chapters %s</h2>' % rng(first),
              '<p class=note>These are not ten separate predictions. Once the run '
              'starts, chapters usually come out one per week, so nearly all the '
              'uncertainty is the start date.</p>',
              chapter_table(post["ten_chapter_forecast"], highlight=first)]
    nb = post.get("next_batch") or {}
    if following and nb:
        h += ['<h2>Chapters %s</h2>' % rng(nfirst),
              '<p class=note>This is the following run. Its timing is a rough '
              'horizon based mostly on publication history.</p>',
              chapter_table(nb["ten_chapter_forecast"], highlight=nfirst)]
    return h


def distribution_charts(chapter, pmf, median, i80):
    """Current release-date distribution, reused on the two chapter pages."""
    spike = max(pmf, key=lambda x: x[1]) if pmf else None
    h = ['<h3>Chance chapter %d has been published by a given date</h3>' % chapter,
         cdf_chart(pmf, median, i80),
         '<p class=note>Each step is one weekly Jump issue; the shaded band is the '
         '80%% range.</p>',
         '<h3>Probability distribution by month</h3>',
         pdf_chart(pmf, median, i80, spike),
         '<p class=note>The same distribution as monthly probability mass, which '
         'makes the likely dates and the long tail easier to compare.</p>']
    return h


def togashi_drawn_section(first, nfirst):
    """Shared current-production section for both reader-facing pages."""
    grid = production_status(first, 20)
    h = ['<h2>What Togashi has drawn</h2>',
         '<p class=note>Togashi posts his own progress on X. Each chapter below '
         'sits at the furthest point he has actually reported.</p>',
         '<div class=strip>']
    for c, stages in grid.items():
        t = tier_of(stages)
        cls = dict((n, k) for n, k, _, _ in TIERS)[t]
        newest = max(stages.values(), key=lambda r: r["event_date"]) if stages else None
        tip = ("%s — %s" % (fmt(newest["event_date"], True),
                            esc(newest["source_text_ja"])) if newest
               else "nothing reported yet")
        h.append('<span class="chip %s" title="%s">%d</span>' % (cls, tip, c))
    h.append('</div><div class=legend>')
    for _, k, en, ja in TIERS:
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
    h.append('<h3>Stage by stage</h3><div class=tblwrap><table><tr><th>Ch.</th>')
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
    h.append('</table></div><div class=legend>'
             '<span><i class="dot done"></i>reported by Togashi</span>'
             '<span><i class="dot assumed"></i>assumed done</span>'
             '<span><i class=dot></i>no information</span></div>')
    h.append('<h3>What the stages mean</h3><div class=tblwrap><table><tr><th>Stage</th>'
             '<th>Japanese</th><th>What happens</th></tr>')
    for _, en, ja, desc in STAGES:
        h.append('<tr><td>%s</td><td class=jp>%s</td><td class=note>%s</td></tr>'
                 % (en, ja, desc))
    h.append('</table></div>')
    return h


def build_index(post, l2, pri, snap_path):
    first = int(post["target"].split("ch ")[-1])
    nb = post.get("next_batch") or {}
    nfirst = nb.get("first_chapter", first + 10)
    pmf = post.get("posterior_pmf") or []
    spike = max(pmf, key=lambda x: x[1]) if pmf else None
    i = post["intervals"]
    anns, counts = announcements(), corpus_counts()

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

    h += readiness_comparison_chart(post)
    h += history_charts(first, post, primary=True, secondary=False,
                        probabilities=False,
                        companion=("chapter-431.html", nfirst))
    h += distribution_charts(first, pmf, post["median"], i["80"])

    h += forecast_tables(post, first, nfirst, current=True, following=False)

    if post.get("p_started_by"):
        h.append('<h3>Chance it has started by</h3><table>')
        for d, p in sorted(post["p_started_by"].items()):
            h.append('<tr><td>%s</td><td class=num>%s</td></tr>' % (fmt(d), pct(p)))
        h.append('</table>')

    h += togashi_drawn_section(first, nfirst)

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

    ser = posterior_series(first)

    h.append('<p class=note>%d forecast%s in the record, updated daily and again '
             'whenever Togashi posts. Nothing here is ever edited or deleted after '
             'the fact &mdash; including when it turns out wrong.</p>'
             % (len(ser), "" if len(ser) == 1 else "s"))

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


def build_chapter_431(post, l2, pri, snap_path):
    """A dedicated history page for the first chapter of the following run."""
    first = int(post["target"].split("ch ")[-1])
    nb = post.get("next_batch") or {}
    nfirst = nb.get("first_chapter", first + 10)
    counts = corpus_counts()
    h = ['<div class=wrap>',
         '<h1><a href="index.html">&larr; Hunter &times; Hunter forecast</a></h1>',
         '<div class=hero><div class=ch>Following run &mdash; chapter %d</div>' % nfirst]
    h += ['<div class=date>%s</div>' % fmt(nb.get("median", post["median"])),
          '<div class=sub>forecast history and current probability distribution</div></div>']
    h += history_charts(nfirst, post, primary=True, secondary=False, probabilities=False,
                        companion=("index.html", first))
    if nb:
        h += distribution_charts(nfirst, nb.get("pmf") or [],
                                 nb.get("median", post["median"]),
                                 nb.get("intervals", {}).get("80", post["intervals"]["80"]))
    h += forecast_tables(post, first, nfirst, current=False, following=True)
    h += togashi_drawn_section(first, nfirst)

    h.append('<footer><p>Built from %d chapters, %d posts by Togashi and %d '
             'production events. <a href="method.html">Method and limitations '
             '&rarr;</a></p>'
             % (counts["chapters"], counts["tweets"], counts["events"]))
    h.append('<p><a href="index.html">&larr; Back to the chapter %d forecast</a></p>'
             % first)
    h.append('</footer></div>')
    title = "Hunter × Hunter — chapter %d prediction history" % nfirst
    desc = "Historical forecast evolution and current forecast for Hunter x Hunter chapter %d." % nfirst
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
    smooth_zero = post.get("level2_design") in {
        "all_pairs_coordinate_likelihood_v7_smooth_zero_gaps_censored",
        "all_pairs_coordinate_likelihood_v8_parametric_level1_frozen_fade",
    }
    if smooth_zero:
        prior_note = ('There are %d gaps between runs since 2007, including three '
                      'zero-gap continuations and positive waits of 9 to 184 issues. '
                      'This sensitivity version smooths them as <em>one</em> broad '
                      'distribution, so it does not retain an immediate-continuation '
                      'point mass.')
    else:
        prior_note = ('There are %d gaps between runs since 2007, and they are '
                      '<em>bimodal</em>: three times the next run began with no wait at all, '
                      'the rest after waits of 9 to 184 issues. A single smooth curve would '
                      'describe neither case, so the model uses a mixture.')
    h.append('<div class=card><h3>1 &mdash; what history alone suggests</h3>'
             '<p class=note>Built from publication records only, never from '
             'Togashi&rsquo;s posts &mdash; otherwise the next step would not be an '
             'update. %s <a href="research-methods.html">See the full '
             'statistical-methods paper and its plot &rarr;</a></p></div>'
             % (prior_note % ((pri or {}).get("n_observations") or 16)))
    if pri and pri.get("gap_pmf") and not smooth_zero:
        h.append(gap_prior_chart(pri))
        chart_note = ('That single-process prior, drawn. The tick marks along the '
                      'bottom are the %d observations it is built from; zero gaps '
                      'are smoothed into the same curve as positive gaps. With a '
                      '60-issue kernel over this small record, the prior says little '
                      'about <em>how long</em> a wait will be.' if smooth_zero else
                      'That mixture, drawn. The tick marks along the bottom are the '
                      '%d observations the whole prior is built from, at the weight '
                      'each carries &mdash; the three zeros count as two, because two '
                      'of them are the same run continuing rather than two separate '
                      'decisions to carry straight on. The bar at gap 0 is clipped: '
                      'it is about twenty times the height of the curve, and drawing '
                      'it to scale would flatten everything else to nothing. The curve '
                      'itself is close to flat from 1 to 100 &mdash; with a 60-issue '
                      'kernel over sixteen points, the prior says little about '
                      '<em>how long</em> a wait will be once there is a wait at all.')
        h.append('<p class=note>%s</p>' %
                 (chart_note % ((pri or {}).get("n_observations") or 16)))
    elif smooth_zero:
        h.append('<p class=note>The full fitted shifted-lognormal prior is plotted '
                 'on the <a href="research-methods.html">statistical-methods page</a>. '
                 'It is kept separate here because this page&rsquo;s older gap chart '
                 'is designed for a point-mass mixture.</p>')
    if post.get("analogs"):
        h.append('<div class=card><h3>2 &mdash; what Togashi&rsquo;s posts add</h3>'
                 '<p class=note>Production data covers only %d past runs. That is '
                 'far too few to fit a curve to, but enough to compare the current '
                 'batch&rsquo;s chapter-readiness states with what was publicly '
                 'reported before each past run began. The model asks: <em>if this '
                 'batch behaves like that one, when would it start?</em></p>'
                 '<table><tr><th>If it behaves like&hellip;</th>'
                 '<th>&hellip;chapter %d comes out</th></tr>'
                 % (len(post.get("analogs") or []), first))
        bfc = batch_first_chapter()
        for k, v in sorted((post.get("implied_by_analog") or {}).items()):
            label = ("the run starting at chapter %d" % bfc[int(k)]) \
                if int(k) in bfc else ("run %s" % esc(k))
            h.append('<tr><td>%s</td><td>%s</td></tr>' % (label, fmt(v)))
        exhausted = post.get("exhausted_analogs") or []
        if exhausted:
            note = ('%d analog%s already implied a start inconsistent with the '
                    'observed non-start. They are neutral rather than being '
                    'allowed to create a false next-issue spike.'
                    % (len(exhausted), "s" if len(exhausted) != 1 else ""))
        else:
            note = ('The table is based on one readiness summary per chapter, not '
                    'on treating every tweet as a separate timing signal.')
        h.append('</table><p class=note>%s</p></div>' % note)
    n_ready = post.get("n_chapters_with_current_readiness") or 0
    h.append('<div class=card><h3>Putting them together</h3><p class=note>'
             'The current run has readiness evidence for %d chapters. Those are '
             '<strong>not</strong> %d independent pieces of evidence &mdash; they '
             'are one person&rsquo;s working process observed across a batch. Treating '
             'every tweet as independent would produce a forecast about a week '
             'wide: very impressive, and wrong. So each <em>past run</em> counts '
             'once, and the confidence scales with how many comparable runs exist, '
             'not how many posts there are.</p></div>' % (n_ready, n_ready))
    feas = post.get("feasibility") or {}
    if post.get("level2_design") in {"ordered_readiness_two_sided_mixture_v11",
                                     "ordered_readiness_feasibility_floor_v10",
                                     "readiness_feasibility_floor_v9"}:
        lvl = feas.get("level")
        if post.get("level2_design") == "ordered_readiness_two_sided_mixture_v11":
            centres = (post.get("readiness_mixture") or {}).get("centres") or {}
            centre_text = ", ".join(centres[k] for k in sorted(centres))
            h.append('<div class=card><h3>How production evidence is used</h3><p class=note>'
                     'The run is at %.2f of 10.00 ordered chapter-equivalents. '
                     'At that same readiness, the three resolved production-era '
                     'runs imply start dates of %s. Each supplies one broad '
                     '120-day component; the components are averaged, not '
                     'multiplied. This makes dates far beyond every comparable '
                     'readiness trajectory less likely while preserving a wide '
                     'tail for Shueisha&rsquo;s independent scheduling decision.</p></div>'
                     % (lvl or 0.0, centre_text or 'unavailable'))
        else:
            h.append('<div class=card><h3>How production evidence is used</h3><p class=note>'
                 'The run is summarised by one number: the summed ordered readiness '
                 'across its ten chapters. Later-chapter reports provide conservative '
                 'floors for earlier chapters, while retouch is excluded. Direct and '
                 'inferred progress remain separately recorded. That number can only go '
                 'up, so a new post can only move '
                 'the forecast earlier or leave it alone &mdash; it can never make a '
                 'finished page into bad news.%s The three resolved runs began at '
                 '9.1, 9.5, and 10.0 chapter-equivalents, so '
                 'the model uses production as a <em>floor</em> &mdash; how much work '
                 'is still required &mdash; and lets the publication history say how '
                 'long the wait above that floor is likely to be. When the required '
                 'work is already done, production stops constraining the date and '
                 'says so, rather than inventing a start date from three past runs.'
                 '</p></div>'
                 % ('' if lvl is None else ' It currently stands at %.2f of 10.00.' % lvl))
        h.append('<div class=card><h3>How continued non-publication is handled</h3><p class=note>'
                 'Each forecast rules out issues already known not to contain '
                 'the batch. This is a factual update, applied continuously. '
                 'It can gradually move the forecast later during a hiatus, '
                 'but does not treat silence as a new production milestone.</p></div>')
    if post.get("level2_design") in {"all_pairs_coordinate_likelihood_v5",
                                     "all_pairs_coordinate_likelihood_v9_mixture_level1",
                                     "all_pairs_coordinate_likelihood_v8_parametric_level1_frozen_fade",
                                     "all_pairs_coordinate_likelihood_v6_continuous_no_start",
                                     "all_pairs_coordinate_likelihood_v6_predecessor_gated",
                                     "all_pairs_coordinate_likelihood_v6_buffer_mixture",
                                     "all_pairs_coordinate_likelihood_v7_direct_two_gap",
                                     "all_pairs_coordinate_likelihood_v7_direct_two_gap_censored",
                                     "all_pairs_coordinate_likelihood_v7_smooth_zero_gaps_censored"}:
        h.append('<div class=card><h3>How production evidence is combined</h3><p class=note>'
                 'Every usable page-log or stage event is represented by its '
                 'chapter-progress coordinate and date. The model compares its '
                 'distance from the target chapter with all comparable historical '
                 'event-to-batch-start pairs. This admits evidence from preceding, '
                 'target, and following chapters, but still averages at the '
                 'historical-batch level so thousands of pairs do not pretend to be '
                 'thousands of independent scheduling decisions.</p></div>')
        if post.get("level2_design") in {"all_pairs_coordinate_likelihood_v9_mixture_level1",
                                         "all_pairs_coordinate_likelihood_v8_parametric_level1_frozen_fade",
                                         "all_pairs_coordinate_likelihood_v6_continuous_no_start",
                                         "all_pairs_coordinate_likelihood_v6_predecessor_gated",
                                         "all_pairs_coordinate_likelihood_v6_buffer_mixture",
                                         "all_pairs_coordinate_likelihood_v7_direct_two_gap",
                                         "all_pairs_coordinate_likelihood_v7_direct_two_gap_censored",
                                         "all_pairs_coordinate_likelihood_v7_smooth_zero_gaps_censored"}:
            h.append('<div class=card><h3>How continued non-publication is handled</h3><p class=note>'
                     'Each forecast rules out issues already known not to contain '
                     'the batch. This is a factual update, applied continuously. '
                     'It can gradually move the forecast later during a hiatus, '
                     'but does not treat silence as a new production milestone.</p></div>')
        buf = ((post.get("next_batch") or {}).get("continuation_buffer") or {})
        if buf:
            h.append('<div class=card><h3>Why production can move the following run</h3><p class=note>'
                     'The following-run prior is a mixture of an immediate '
                     'continuation and a later hiatus. Public work on those '
                     'chapters changes the continuation weight from %.0f%% to %.0f%%. '
                     'That is evidence of a production buffer, not a claim that '
                     'Weekly Shonen Jump has committed to a schedule.</p></div>'
                     % (100 * buf.get("baseline_continuation_weight", 0),
                        100 * buf.get("continuation_weight", 0)))
        hprior = ((post.get("next_batch") or {}).get("two_gap_prior") or {})
        if hprior:
            h.append('<div class=card><h3>How the following run is forecast</h3><p class=note>'
                     'Before its predecessor starts, the following run uses the '
                     'historical distribution of <em>two adjacent gaps together</em>, '
                     'rather than multiplying two independent one-gap forecasts. '
                     'The current forecast is conditioned on the first gap already '
                     'lasting at least %d issue%s; %d of %d historical two-gap '
                     'pairs remain comparable.</p></div>'
                     % (hprior.get("elapsed_first_gap", 0),
                        "" if hprior.get("elapsed_first_gap", 0) == 1 else "s",
                        hprior.get("n_eligible_pairs", 0), hprior.get("n_pairs", 0)))
    elif post.get("level2_design") not in {"ordered_readiness_two_sided_mixture_v11",
                                           "ordered_readiness_feasibility_floor_v10"}:
        ctx = (post.get("preceding_batch_context") or {}).get("weight")
        h.append('<div class=card><h3>How silence is handled</h3><p class=note>'
                 'The batch being forecast supplies the direct production evidence. '
                 'The preceding batch is only a weak context signal%s. Ordinary '
                 'calendar time with no new public production report does not move the '
                 'forecast. Only after a gap exceeds every observed modern hiatus does '
                 'the model enter a record-hiatus rule: 20%% on the next eligible issue '
                 'and 80%% on the historical long tail.</p></div>'
                 % ((" (%.0f%% of the timing likelihood)" % (100 * ctx))
                    if ctx is not None else ""))

    first_ch_m = int(post["target"].split("ch ")[-1])
    ser = posterior_series(first_ch_m)
    n_rep = sum(1 for r in ser if r["replay"])
    if n_rep:
        h.append('<h2>The forecast history, and which of it is reconstructed</h2>')
        h.append('<div class=card><h3>%d of %d points were re-run afterwards</h3>'
                 '<p class=note>The model started producing forecasts on %s, but '
                 'the interesting stretch is the whole of the run that produced '
                 'the evidence it uses. So it was replayed: for each earlier date '
                 'it was re-run seeing only the chapters published, the issues on '
                 'sale and the production posts made <em>by that date</em>. Those '
                 'points are marked <code>provenance: replay</code> in the stored '
                 'snapshot and the charts rule off where the live record '
                 'begins.</p>'
                 '<p class=note>One honest caveat. An event enters the replay on '
                 'the day it happened, not the day it was known &mdash; some '
                 'readings come from images transcribed and human-checked later, '
                 'and some posts were only found through the Wayback Machine. The '
                 'replay is therefore very slightly better informed than a live '
                 'run would have been. The batch&rsquo;s length is treated the '
                 'same way throughout, as an assumption rather than as evidence '
                 'that arrived on some date.</p></div>'
                 % (n_rep, len(ser),
                    fmt(next((r["t"].date().isoformat() for r in ser
                              if not r["replay"]), ""))))

    h.append('<h2>Where it is weakest</h2>')
    if smooth_zero:
        h.append('<div class=card><h3>The parametric tail is the least defensible part</h3>'
                 '<p class=note>The shifted-lognormal prior is fitted to only a '
                 'handful of heterogeneous publication gaps. Its long tail is a '
                 'deliberate conservative extrapolation, not a measured biological '
                 'or editorial process. It must be judged by leakage-free scoring '
                 'once more resolved batches exist.</p></div>')
    else:
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
    h.append('<li><strong>Silence is deliberately mostly neutral.</strong> The '
             'forecast holds between public production or publication updates. '
             'That avoids arbitrary date drift, but it also means an ordinary long '
             'silence contributes little information until it becomes a record '
             'hiatus.</li>')
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
             'production events. <a href="index.html">Chapter %d forecast</a> '
             '&middot; <a href="chapter-431.html">chapter %d forecast history</a></p>'
             % (counts["chapters"], counts["tweets"], counts["events"], first,
                nb.get("first_chapter", first + 10)))
    h.append('</footer></div>')

    return (HEAD % ("How the Hunter × Hunter forecast works",
                    "Method and limitations behind the Hunter x Hunter "
                    "publication forecast.", CSS)) + "\n".join(h) + "</html>"


def main():
    post, l2, pri, snap_path = latest_snapshot()
    os.makedirs(SITE, exist_ok=True)
    for name, doc in (("index.html", build_index(post, l2, pri, snap_path)),
                      ("chapter-431.html", build_chapter_431(post, l2, pri, snap_path)),
                      ("method.html", build_method(post, l2, pri, snap_path))):
        with open(os.path.join(SITE, name), "w", encoding="utf-8") as fh:
            fh.write(doc)
        print("site: site/%-12s %.1f KB" % (name, len(doc) / 1024.0))
    from build_chapter421_workings import build as build_chapter421_workings
    steps, pmf, _readme, n = build_chapter421_workings()
    print("working: %s (%d forecast dates)" % (os.path.relpath(steps, D()), n))
    print("working: %s" % os.path.relpath(pmf, D()))
    from build_prior_explainer import build as build_prior_explainer
    prior_path = build_prior_explainer()
    print("site: %s" % os.path.relpath(prior_path, D()))


if __name__ == "__main__":
    main()
