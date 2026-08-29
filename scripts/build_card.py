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
import os
from datetime import date, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

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
SITE = "geanodong-bcrs.github.io/hxh-forecast"


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


def render(d, path):
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
        pp = d["spike_pp"]
        colour = GOOD if pp > 0 else CRIT if pp < 0 else MUTED
        glyph = "▲" if pp > 0 else "▼" if pp < 0 else "▬"
        delta_txt = "%s  %+.1f points on %s" % (
            glyph, pp, date.fromisoformat(d["spike_date"]).strftime("%-d %b"))

    # ---------------- left: the figure ----------------
    # matplotlib has no letter-spacing property, so the tracked-caps eyebrow is
    # spaced by hand
    fig.text(.055, .885, " ".join("HUNTER × HUNTER"), color=MUTED, fontsize=8,
             fontweight="bold")
    fig.text(.055, .805, "Chapter %d — most likely release" % d["chapter"],
             color=INK2, fontsize=11)
    # hero figure: exactly one per view, >=48px equivalent
    fig.text(.055, .625, fmt(date.fromisoformat(d["median"])), color=INK,
             fontsize=34, fontweight="semibold", va="baseline")

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
        fig.text(.055, .35, "was %s" % fmt(date.fromisoformat(d["prev_median"])),
                 color=MUTED, fontsize=10.5)
    else:
        fig.text(.055, .35, "date unchanged", color=MUTED, fontsize=10.5)
    fig.text(.055, .265,
             "80%% range  %s – %s"
             % (date.fromisoformat(d["i80"][0]).strftime("%-d %b %y"),
                date.fromisoformat(d["i80"][1]).strftime("%-d %b %y")),
             color=INK2, fontsize=10.5)
    fig.text(.055, .18, "P(%s)  %.0f%% → %.0f%%"
             % (date.fromisoformat(d["spike_date"]).strftime("%-d %b"),
                d["spike_prev_p"] * 100, d["spike_p"] * 100),
             color=INK2, fontsize=10.5)

    # ---------------- right: emphasis chart ----------------
    ax = fig.add_axes([.545, .215, .40, .60])
    ax.set_facecolor(SURFACE)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8, length=0, pad=4)
    ax.set_ylim(0, 1.02)
    ax.set_yticks([0, .5, 1])
    ax.set_yticklabels(["0%", "50%", "100%"])
    ax.grid(axis="y", color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)

    px, py = cdf(d["prev_pmf"] or d["pmf"])
    nx, ny = cdf(d["pmf"])
    # Context first in de-emphasis gray, the point on top in the accent. NO area
    # fill: the area under a cumulative curve is not a quantity, and filling it
    # buries the line that is the actual mark.
    ax.step(px, py, where="post", color=MUTED, linewidth=1.6, zorder=2)
    ax.step(nx, ny, where="post", color=ACCENT, linewidth=2.4, zorder=3)

    # Identity for two series, placed as a small swatch legend in the dead space
    # under the curve. Direct labels were tried first and cannot work here: a
    # shift of a few weeks keeps the curves within a few points of each other for
    # their whole length, so any label pinned to a curve lands on the other one.
    for row, (col, lab, weight) in enumerate(
            ((ACCENT, "now", "bold"), (MUTED, "before", "normal"))):
        y = 0.30 - row * 0.11
        ax.plot([0.50, 0.565], [y, y], transform=ax.transAxes, color=col,
                linewidth=2.4 if weight == "bold" else 1.6,
                solid_capstyle="butt", clip_on=False)
        ax.text(0.585, y, lab, transform=ax.transAxes, color=col, fontsize=9.5,
                fontweight=weight, va="center")
    ax.set_title("chance it has been published by", color=MUTED, fontsize=9,
                 loc="left", pad=8)

    lo, hi = min(nx[0], px[0]), max(nx[-1], px[-1])
    ticks, cur = [], date(lo.year, lo.month, 1)
    while cur <= hi:
        ticks.append(cur)
        cur = date(cur.year + (cur.month // 12), cur.month % 12 + 1, 1)
    step = max(1, len(ticks) // 5)
    ticks = ticks[::step]
    ax.set_xticks(ticks)
    ax.set_xticklabels([t.strftime("%b %y") for t in ticks])

    # ---------------- footer ----------------
    fig.text(.055, .058, SITE, color=MUTED, fontsize=9)
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
    args = ap.parse_args()

    d = fd.compute()
    if not d:
        return print("need at least two snapshots") or 1
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
