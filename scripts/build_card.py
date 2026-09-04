#!/usr/bin/env python3
"""The reply image: what this post did to the forecast.

    python3 scripts/build_card.py                 # newest pair of snapshots
    python3 scripts/build_card.py --demo -21      # synthesise a shift, to see it

Design follows the data-viz contract rather than taste:

  FORM      A hero figure plus one emphasis chart. The card's job is a single
            headline number and its delta, which is a stat tile, not a chart —
            so the date is the hero and the curve is supporting context.
  EMPHASIS  Two curves, but they are not two categories: the new forecast is the
            point and the previous one is context. Accent + de-emphasis gray,
            never two categorical hues.
  COLOR     Dark surface, because X is mostly read dark and a PNG cannot adapt.
            Palette values are the validated dark steps; the accent-vs-status
            pairs that can appear together were run through the validator and
            pass all six checks.
  STATUS    "earlier" green and "later" red fail CVD separation against each
            other (deutan ΔE 4.1) — as red/green always will. Mitigated the way
            the spec requires: they never appear together (a card is one or the
            other), and the colour is always redundant with an arrow glyph AND
            the word, so nothing rests on hue.
"""
import argparse
import glob
import json
import os
from datetime import date, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

import forecast_delta as fd

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
OUT = D("data", "cards")

SURFACE = "#1a1a19"
INK = "#ffffff"
INK2 = "#c3c2b7"
MUTED = "#898781"
GRID = "#2c2c2a"
ACCENT = "#3987e5"
GOOD = "#0ca30c"
CRIT = "#d03b3b"
HANDLE = "@HxHforecast"


def fmt(d):
    return d.strftime("%-d %b %Y")


def cdf(pmf, clip=0.99):
    """Step points, opened with a zero so the first jump is actually drawn.

    Without the leading (first_date, 0) the curve starts at ~50% and the single
    most important feature of this distribution — half the probability landing on
    one issue — is invisible, because there is no riser to see.
    """
    xs, ys, acc = [], [], 0.0
    for iso, p in pmf:
        d0 = date.fromisoformat(iso)
        if not xs:
            xs.append(d0)
            ys.append(0.0)
        acc += p
        xs.append(d0)
        ys.append(acc)
        if acc >= clip:
            break
    return xs, ys


def history(design, chapter):
    """(as_of, p10, p50, p90, live) per snapshot of THIS model design, oldest first.

    Same series the site's "Predicted publication date over time" chart draws.
    Only the current design is included: older ones would draw the model's own
    revisions as if they were movement in the evidence.

    Almost all of it is `provenance: replay` — the model re-run at past dates
    with chapters, production events and WSJ issues filtered to what was public
    then. That is not a track record, so the card marks where the live record
    starts rather than presenting the whole line as predictions actually made.
    """
    out = []
    for f in sorted(glob.glob(D("data", "forecasts", "*_posterior.json"))):
        if "T" not in os.path.basename(f).split("_")[0]:
            continue
        with open(f, encoding="utf-8") as fh:
            snap = json.load(fh)
        if (snap.get("level2_design") or "") != design:
            continue
        # The per-CHAPTER row, not the snapshot median. While batch 49 was the
        # target the median is batch 49's start; ch. 421 still has a value, in
        # the following batch's ten-chapter forecast. Same source the site uses.
        row = None
        for src in ((snap.get("ten_chapter_forecast") or []),
                    ((snap.get("next_batch") or {}).get("ten_chapter_forecast") or [])):
            for r in src:
                if r.get("chapter") == chapter:
                    row = r
        asof = snap.get("replay_asof") or snap.get("forecast_timestamp")
        if not row or not row.get("median") or not row.get("i80") or not asof:
            continue
        out.append((date.fromisoformat(asof),
                    date.fromisoformat(row["i80"][0]),
                    date.fromisoformat(row["median"]),
                    date.fromisoformat(row["i80"][1]),
                    snap.get("provenance") != "replay"))
    out.sort(key=lambda r: r[0])
    # one point per as_of date, latest run for that date wins
    dedup = {}
    for r in out:
        dedup[r[0]] = r
    return [dedup[k] for k in sorted(dedup)]


BATCH_STARTS = {47: "2022-10-24", 48: "2024-10-07", 49: "2026-06-29"}


def _events():
    import csv as _csv
    with open(D("data", "processed", "production_events.csv"), encoding="utf-8") as fh:
        return list(_csv.DictReader(fh))


def readiness_paths(first_chapter):
    """Progress curves for this run and every run before it.

    A run that has STARTED publishing is traced only up to the day it started,
    so its curve ends exactly where the question is: how much was drawn when the
    publisher let it go, marked with a dot. A run that has not started yet runs
    to today and gets no dot, because it has no answer yet -- on the ch. 431
    card that is ch. 421-430, which is context rather than a resolved case.

    x is days since that run's own first public production report, which is the
    only alignment available -- Togashi's posting began mid-way through
    ch. 391-400, so that curve is a lower bound on its true duration.
    """
    import build_readiness as br
    ev = _events()
    target_batch = 47 + (first_chapter - 391) // 10
    out = []
    for batch in range(47, target_batch + 1):
        ch0 = 391 + (batch - 47) * 10
        start_iso = BATCH_STARTS.get(batch)
        upto = date.fromisoformat(start_iso) if start_iso else date.today()
        trace = br.ordered_trace(ev, list(range(ch0, ch0 + 10)), upto)
        if trace:
            out.append((ch0, trace, ch0 == first_chapter, start_iso is not None))
    return [(ch0, [((w - t[0][0]).days, v / 10.0) for w, v, _ in t], cur, started)
            for ch0, t, cur, started in out]


def readiness_state(first_chapter):
    """(level 0-10, {batch: days from that level to its start}) for any run."""
    import build_feasibility as bf
    import build_readiness as br
    ev = _events()
    trace = br.ordered_trace(ev, list(range(first_chapter, first_chapter + 10)),
                             date.today())
    if not trace:
        return None, {}
    level = trace[-1][1]
    rem = {}
    for batch, start_iso in sorted(BATCH_STARTS.items()):
        ch0 = 391 + (batch - 47) * 10
        if ch0 >= first_chapter:
            continue
        start = date.fromisoformat(start_iso)
        # None is kept, not dropped: "we never observed that run at this level"
        # is information, and silently omitting the row would imply the batch
        # was not comparable rather than not measurable.
        rem[str(batch)] = bf.remaining(
            bf.trace(ev, list(range(ch0, ch0 + 10)), start), start, level)
    return level, rem


def chapter_pub_date(ch):
    """On-sale date of one chapter, or None. Used to window the history chart."""
    try:
        import csv
        with open(D("data", "processed", "chapters.csv"), encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("chapter") == str(ch) and r.get("publication_date_jp"):
                    return date.fromisoformat(r["publication_date_jp"])
    except Exception:
        pass
    return None


def render(d, path):
    d = dict(d)
    d.setdefault("readiness_paths", readiness_paths(d["chapter"]))
    if d.get("readiness_level") is None or not d.get("analog_remaining"):
        # The snapshot records readiness only for the run it forecasts, so the
        # following run's state is derived here from the same event table.
        lvl, rem = readiness_state(d["chapter"])
        d["readiness_level"], d["analog_remaining"] = lvl, rem
    fig = plt.figure(figsize=(8, 4.5), dpi=200)
    fig.patch.set_facecolor(SURFACE)

    up_is_bad = d["shift_days"] > 0
    if d["shift_days"] != 0:
        colour = CRIT if up_is_bad else GOOD
        glyph = "▲" if up_is_bad else "▼"
        word = "later" if up_is_bad else "earlier"
        n = abs(d["shift_days"])
        delta_txt = "%s  %d day%s %s" % (glyph, n, "" if n == 1 else "s", word)
    else:
        # The date did not move, so the news is the PROBABILITY on the nearest
        # candidate issue. "points" alone reads as days on a card about dates,
        # so the chip says what got more or less likely, and on which issue.
        # Deliberately does NOT name an issue. spike_date is the argmax of the
        # posterior, and with the front of the distribution flat to within
        # 0.02pp that argmax is noise - it sat on 1 Jan while the hero date
        # (the median) was 22 Jan, which reads as a contradiction. The size of
        # the move is real; which single issue happens to hold the peak is not.
        pp = d["spike_pp"]
        if pp == 0:
            # Only reachable via --force; gate 2 blocks a card with no news.
            colour, glyph, delta_txt = MUTED, "▬", "▬  no change"
        else:
            colour = GOOD if pp > 0 else CRIT
            glyph = "▲" if pp > 0 else "▼"
            delta_txt = "%s  %.1f pts more likely" % (glyph, pp) if pp > 0 else \
                        "%s  %.1f pts less likely" % (glyph, abs(pp))

    # ---------------- left: the figure ----------------
    # matplotlib has no letter-spacing property, so the tracked-caps eyebrow is
    # spaced by hand
    fig.text(.055, .885, " ".join("HUNTER × HUNTER"), color=MUTED, fontsize=8,
             fontweight="bold")
    fig.text(.055, .805, "Chapter %d — most likely release" % d["chapter"],
             color=INK2, fontsize=11)
    # hero figure: exactly one per view, >=48px equivalent
    footnoted = d.get("target_view") == "next"
    fig.text(.055, .625,
             fmt(date.fromisoformat(d["median"])) + ("*" if footnoted else ""),
             color=INK, fontsize=34, fontweight="semibold", va="baseline")

    # A card with nothing to report shows no chip at all. A grey "no change"
    # pill is a headline saying there is no headline, and on the following run's
    # card that is its permanent state -- its forecast cannot move on production
    # evidence. The chip returns of its own accord as soon as something moves,
    # which for ch. 431 means once ch. 421-430 is publishing.
    quiet = d["shift_days"] == 0 and d["spike_pp"] == 0
    if not quiet:
        ax_chip = fig.add_axes([.055, .47, .42, .085])
        ax_chip.set_axis_off()
        ax_chip.add_patch(FancyBboxPatch(
            (0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=.16",
            transform=ax_chip.transAxes, facecolor=colour, alpha=.16,
            edgecolor="none", zorder=0))
        ax_chip.text(.5, .5, delta_txt, transform=ax_chip.transAxes, color=colour,
                     fontsize=13, fontweight="bold", ha="center", va="center")

    # "was X" only when the date actually moved — on a probability-only card the
    # previous median is the same date, and repeating it reads as a mistake
    if d["shift_days"] != 0:
        fig.text(.055, .375, "was %s" % fmt(date.fromisoformat(d["prev_median"])),
                 color=MUTED, fontsize=10.5)
    elif not quiet:
        fig.text(.055, .375, "date unchanged", color=MUTED, fontsize=10.5)
    fig.text(.055, .30,
             "80%% range  %s – %s"
             % (date.fromisoformat(d["i80"][0]).strftime("%-d %b %y"),
                date.fromisoformat(d["i80"][1]).strftime("%-d %b %y")),
             color=INK2, fontsize=10.5)

    # ---------------- readiness meter ----------------
    # This card is posted under a PRODUCTION tweet, so "how much of the run is
    # drawn" is the fact the reader is already looking at. It is given the accent
    # and a meter rather than a second large number: a bar reads instantly and
    # does not compete typographically with the hero date, which is still the
    # answer to the question being asked.
    lvl = d.get("readiness_level")
    if lvl is not None:
        frac = max(0.0, min(1.0, lvl / 10.0))
        fig.text(.055, .205, "Batch %d–%d progress" % (d["chapter"], d["chapter"] + 9),
                 color=INK2, fontsize=10.5)
        fig.text(.475, .205, "%.0f%%" % (frac * 100), color=ACCENT, fontsize=13,
                 fontweight="bold", ha="right", va="baseline")
        ax_bar = fig.add_axes([.055, .142, .42, .026])
        ax_bar.set_axis_off()
        ax_bar.set_xlim(0, 1)
        ax_bar.set_ylim(0, 1)
        ax_bar.add_patch(Rectangle((0, 0), 1, 1, facecolor=GRID,
                                   edgecolor="none", zorder=0))
        if frac > 0:
            ax_bar.add_patch(Rectangle((0, 0), frac, 1, facecolor=ACCENT,
                                       edgecolor="none", zorder=1))

    # ---------------- right: emphasis chart ----------------
    # Under a PRODUCTION tweet the on-topic question is "is this run ahead or
    # behind?", not "how has our prediction wobbled". Progress is monotone, so
    # this can only ever look like progress -- where the forecast-history chart
    # was dominated by a downward step caused by WSJ's schedule, which under his
    # post would read as his finished chapter pushing the date back.
    #
    # Accent for this run, graduated grays for context, per the card's palette
    # rule. The three grays are not categories to decode: each is labelled at the
    # dot where that run actually began.
    ax = fig.add_axes([.575, .40, .37, .42])
    ax.set_facecolor(SURFACE)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8, length=0, pad=4)
    ax.set_ylim(0, 1.06)
    ax.set_yticks([0, .5, 1])
    ax.set_yticklabels(["0%", "50%", "100%"])
    ax.grid(axis="y", color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)

    paths = d.get("readiness_paths") or []
    grays = ["#4e4c48", "#63615c", "#7a7872", "#918f88"]
    gi = 0
    for ch0, pts, is_current, started in paths:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if is_current:
            ax.step(xs, ys, where="post", color=ACCENT, linewidth=2.6, zorder=4)
            ax.plot(xs[-1], ys[-1], "o", color=ACCENT, markersize=5, zorder=5)
        else:
            col = grays[min(gi, len(grays) - 1)]
            gi += 1
            ax.step(xs, ys, where="post", color=col, linewidth=1.5, zorder=2)
            if started:
                # the dot is where that run began publishing; a run still
                # waiting has no such point and must not be given one
                ax.plot(xs[-1], ys[-1], "o", color=col, markersize=4, zorder=3)
            ax.text(xs[-1] + 14, ys[-1], "ch. %d" % ch0, color=col, fontsize=8,
                    va="center", ha="left")
    if paths:
        cur = [p for p in paths if p[2]]
        if cur:
            xs = [p[0] for p in cur[0][1]]
            ax.text(xs[-1] + 14, cur[0][1][-1][1], "ch. %d" % cur[0][0],
                    color=ACCENT, fontsize=8, fontweight="bold", va="center",
                    ha="left")
        allx = [p[0] for _, pts, _, _ in paths for p in pts]
        ax.set_xlim(0, max(allx) * 1.26)
        step = 180
        ax.set_xticks(list(range(0, int(max(allx)) + 1, step)))
    ax.set_xlabel("Days since Togashi's first post of this batch", color=MUTED,
                  fontsize=7.5, labelpad=3)
    ax.set_ylabel("Togashi's production progress", color=MUTED, fontsize=7.5,
                  labelpad=4)

    # ---------------- previous runs ----------------
    rem = d.get("analog_remaining") or {}
    prev = [b for b in sorted(BATCH_STARTS) if 391 + (b - 47) * 10 < d["chapter"]]
    if prev:
        fig.text(.575, .295,
                 "At this readiness, previous batches began in", color=INK,
                 fontsize=8.5)
        for row, batch in enumerate(prev):
            first_ch = 391 + (batch - 47) * 10
            y = .225 - row * .05
            days = rem.get(str(batch))
            fig.text(.575, y, "ch. %d–%d" % (first_ch, first_ch + 9),
                     color=INK2, fontsize=9.5)
            fig.text(.945, y, "%d days" % days if days is not None else "—",
                     color=INK if days is not None else MUTED, fontsize=9.5,
                     ha="right")

    # ---------------- caveat ----------------
    # On the following run's card the dominant uncertainty is not this batch's
    # own production at all: it is that the run before it has no schedule yet.
    # Saying so is the difference between a wide interval and a misleading one.
    # It sits in the delta chip's slot, which on this card is empty by
    # definition -- the following run's forecast cannot move on production
    # evidence, so there is never a chip to displace. Geometry is unchanged:
    # when a chip does appear, there is no footnote to collide with it.
    if footnoted:
        for i, line in enumerate(
                ("*Chapter %d–%d has not been scheduled yet," % (d["chapter"] - 10,
                                                                 d["chapter"] - 1),
                 "so this estimate inherits all of that uncertainty.")):
            fig.text(.055, .535 - i * .042, line, color=MUTED, fontsize=8)

    # ---------------- footer ----------------
    fig.text(.055, .058, HANDLE, color=MUTED, fontsize=9)
    fig.text(.945, .058, "updated %s" % date.today().strftime("%-d %b %Y"),
             color=MUTED, fontsize=9, ha="right")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, facecolor=SURFACE, edgecolor="none")
    plt.close(fig)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", type=int, default=None,
                    help="shift the median by N days to preview the card")
    ap.add_argument("--out", default=None)
    ap.add_argument("--next", action="store_true",
                    help="build the card for the FOLLOWING run (ch. 431-440)")
    args = ap.parse_args()

    d = fd.compute(target="next" if args.next else "current")
    if not d:
        return print("no comparable baseline: %s" % fd.pick_pair()[2]) or 1
    if args.demo is not None:
        shift = args.demo
        d["prev_median"] = (date.fromisoformat(d["median"])
                            - timedelta(days=shift)).isoformat()
        d["shift_days"] = shift
        d["prev_pmf"] = [[(date.fromisoformat(i) + timedelta(days=-shift)).isoformat(), p]
                         for i, p in d["pmf"]]
        d["spike_prev_p"] = max(d["spike_p"] - .078, 0.0)

    path = args.out or os.path.join(OUT, "%s_ch%d.png" % (d["run_id"], d["chapter"]))
    render(d, path)
    print("card -> %s" % os.path.relpath(path, D()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
