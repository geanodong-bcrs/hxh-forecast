#!/usr/bin/env python3
"""TEST: the forecast-update card in a manga style (ink on paper, speed lines,
speech bubbles). Not wired into the reply bot; build_card.py is still the live card.

    python3 scripts/build_card_manga.py              # ch. 421 card, latest snapshot
    python3 scripts/build_card_manga.py --demo -21   # pretend the median moved 21 days earlier

Rendered as HTML/SVG and captured with headless Chrome, so the style can later
be shared with the site.

Style rules:
  - Black ink on white, no grey fills; secondary marks are dashes and screentone.
  - The data lines stay exact; the manga feel is in the frame and lettering only.
  - Speed lines scale with the news: light on a quiet update, full 集中線 when
    the median moves a lot.
  - Generic manga vocabulary only: no Togashi art, logo or characters.
"""
import argparse
import json
import math
import os
import random
import subprocess
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
D = lambda *p: os.path.join(HERE, "..", *p)
OUT = D("data", "cards", "manga_test")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

W, H = 1600, 900
CX, CY = W / 2, H / 2


def fmt(d):
    return d.strftime("%-d %b %Y")


def fmt_short(d):
    return d.strftime("%-d %b ’%y")


# ------------------------------------------------------------------ data

def card_data(chapter, demo=None):
    import build_card as bc
    import forecast_delta as fd
    from build_site import latest_snapshot
    post, *_ = latest_snapshot()
    nb = post.get("next_batch") or {}
    if chapter == int(post["target"].split("ch ")[-1]):
        pmf, median, i80 = post["posterior_pmf"], post["median"], post["intervals"]["80"]
        view = "Next"
    else:
        pmf, median, i80 = nb.get("pmf") or [], nb["median"], nb["intervals"]["80"]
        view = "Following"
    spike = max(pmf, key=lambda x: x[1])
    delta = fd.compute(target="current" if view == "Next" else "next") or {}
    shift = delta.get("shift_days", 0)
    if demo is not None:
        shift = demo
    level, _, _ = bc.readiness_state(chapter)
    return {
        "chapter": chapter, "view": view,
        "median": date.fromisoformat(median),
        "i80": [date.fromisoformat(x) for x in i80],
        "spike": (date.fromisoformat(spike[0]), spike[1]),
        "shift": shift,
        "drawn": (level or 0) / 10.0,
        "paths": bc.readiness_paths(chapter),
        "updated": datetime.strptime(post["run_id"], "%Y%m%dT%H%M%SZ").date(),
    }


# ------------------------------------------------------------------ drawing

def speed_lines(intensity, seed=7):
    """Radial wedges from the edges toward a clear rounded-rectangle centre.

    intensity 0..1 sets how many lines there are and how far in they reach.
    The clear area is a superellipse so the corners, where the content sits
    closest to the edge, stay readable.
    """
    rnd = random.Random(seed)
    a, b, n = 745, 405, 4.0
    out = []
    count = int(110 + 260 * intensity)
    for _ in range(count):
        th = rnd.uniform(0, 2 * math.pi)
        c, s = math.cos(th), math.sin(th)
        # radius of the clear superellipse along this direction
        r_clear = (abs(c / a) ** n + abs(s / b) ** n) ** (-1 / n)
        # each line stops somewhere between the edge and the clear area
        reach = rnd.random() ** (1.6 - intensity)       # higher intensity -> deeper
        r_in = r_clear + (1 - reach) * 260 * (1.15 - intensity)
        r_out = 1400
        half = rnd.uniform(.0025, .010) * (1 + intensity)
        p_in = (CX + c * r_in, CY + s * r_in)
        p1 = (CX + math.cos(th - half) * r_out, CY + math.sin(th - half) * r_out)
        p2 = (CX + math.cos(th + half) * r_out, CY + math.sin(th + half) * r_out)
        out.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f"/>'
                   % (p_in + p1 + p2))
    return '<g class="speed">%s</g>' % "".join(out)


def bubble(cx, cy, rx, ry, tip, html, cls=""):
    """An oval speech bubble whose tail points at `tip`, text centred inside."""
    ang = math.atan2((tip[1] - cy) / ry, (tip[0] - cx) / rx)
    spread = .16
    a1, a2 = ang + spread, ang - spread
    p = lambda t: (cx + rx * math.cos(t), cy + ry * math.sin(t))
    (x1, y1), (x2, y2) = p(a1), p(a2)
    path = ("M%.1f,%.1f A%.1f,%.1f 0 1 1 %.1f,%.1f L%.1f,%.1f Z"
            % (x1, y1, rx, ry, x2, y2, tip[0], tip[1]))
    return ('<path class="bub %s" d="%s"/>'
            '<foreignObject x="%.1f" y="%.1f" width="%.1f" height="%.1f">'
            '<div xmlns="http://www.w3.org/1999/xhtml" class="btxt %s"><div>%s</div></div>'
            '</foreignObject>'
            % (cls, path, cx - rx * .78, cy - ry * .72, rx * 1.56, ry * 1.44, cls, html))


def burst(cx, cy, rx, ry, tip, html, spikes=22, seed=3):
    """A jagged shout bubble, with one long spike as its tail."""
    rnd = random.Random(seed)
    tip_ang = math.atan2((tip[1] - cy) / ry, (tip[0] - cx) / rx)
    pts = []
    for i in range(spikes * 2):
        t = 2 * math.pi * i / (spikes * 2)
        d = (t - tip_ang + math.pi) % (2 * math.pi) - math.pi
        if i % 2 == 0 and abs(d) < math.pi / spikes:
            pts.append(tip)
            continue
        k = (1.18 + rnd.uniform(-.04, .08)) if i % 2 == 0 else (.97 + rnd.uniform(-.02, .02))
        pts.append((cx + rx * k * math.cos(t), cy + ry * k * math.sin(t)))
    # Pull the two points either side of the tail in close, so the tail is a
    # narrow spike rather than a wedge the width of two spikes.
    i = pts.index(tip)
    for j, sgn in ((i - 1, -1), ((i + 1) % len(pts), 1)):
        t = tip_ang + sgn * .13
        pts[j] = (cx + rx * math.cos(t), cy + ry * math.sin(t))
    poly = " ".join("%.1f,%.1f" % q for q in pts)
    return ('<polygon class="bub burst" points="%s"/>'
            '<foreignObject x="%.1f" y="%.1f" width="%.1f" height="%.1f">'
            '<div xmlns="http://www.w3.org/1999/xhtml" class="btxt"><div>%s</div></div>'
            '</foreignObject>'
            % (poly, cx - rx * .8, cy - ry * .75, rx * 1.6, ry * 1.5, html))


def chart_panel(paths, x0, y0, w, h):
    """Production progress per run, in ink. Returns (svg, tip of the live run)."""
    pl, pr, pt, pb = 62, 40, 92, 52
    ix, iy, iw, ih = x0 + pl, y0 + pt, w - pl - pr, h - pt - pb
    xmax = max(max(d for d, _ in p) for _, p, _, _ in paths)
    xmax = max(180, int(math.ceil(xmax / 180.0)) * 180)
    X = lambda d: ix + iw * d / xmax
    Y = lambda v: iy + ih * (1 - min(v, 1.0))
    g = ['<rect class="panel" x="%d" y="%d" width="%d" height="%d"/>' % (x0, y0, w, h),
         '<text class="ptitle" x="%d" y="%d">TOGASHI&#8217;S PROGRESS, RUN BY RUN</text>'
         % (x0 + 22, y0 + 38)]
    for v in (0, .5, 1):
        g.append('<line class="tick" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                 '<text class="axl" x="%.1f" y="%.1f" text-anchor="end">%d%%</text>'
                 % (ix, Y(v), ix + iw, Y(v), ix - 10, Y(v) + 6, v * 100))
    d = 0
    while d <= xmax:
        g.append('<text class="axl" x="%.1f" y="%.1f" text-anchor="middle">%d</text>'
                 % (X(d), iy + ih + 26, d))
        d += 180
    g.append('<text class="axl" x="%.1f" y="%.1f" text-anchor="middle">days since each run&#8217;s first post</text>'
             % (ix + iw / 2, y0 + h - 8))
    dashes = {391: "2 7", 401: "12 7", 411: "5 5"}
    tip = None
    for ch0, pts, current, started in paths:
        seg = ["M%.1f,%.1f" % (X(pts[0][0]), Y(pts[0][1]))]
        pv = pts[0][1]
        for dd, v in pts[1:]:
            seg.append("L%.1f,%.1f L%.1f,%.1f" % (X(dd), Y(pv), X(dd), Y(v)))
            pv = v
        dpath = " ".join(seg)
        ex, ey = X(pts[-1][0]), Y(pts[-1][1])
        if current:
            area = dpath + " L%.1f,%.1f L%.1f,%.1f Z" % (ex, Y(0), X(pts[0][0]), Y(0))
            g.append('<path class="tone" d="%s"/>' % area)
            g.append('<path class="live" d="%s"/>' % dpath)
            g.append('<circle class="dot" cx="%.1f" cy="%.1f" r="7"/>' % (ex, ey))
            tip = (ex, ey)
        else:
            g.append('<path class="old" stroke-dasharray="%s" d="%s"/>'
                     % (dashes.get(ch0, "4 4"), dpath))
            if started:
                g.append('<circle class="odot" cx="%.1f" cy="%.1f" r="4.5"/>' % (ex, ey))
            # Runs that all end near 100% would stack their labels at the
            # end, so each sits where its line is alone: 391 at its end, 411
            # above its 100% plateau, 401 under its end dot.
            if pts[-1][1] >= 1.0:
                fx = next(dd for dd, v in pts if v >= 1.0)
                lx, ly, anchor = X(fx) - 6, ey - 12, "end"
            elif ch0 == 401 or pts[-1][1] > .9:
                lx, ly, anchor = ex + 4, ey + 30, "middle"
            else:
                lx, ly, anchor = ex, ey - 14, "middle"
            g.append('<text class="rl" x="%.1f" y="%.1f" text-anchor="%s">CH. %d</text>'
                     % (lx, ly, anchor, ch0))
    return "\n".join(g), tip


def render(d, html_path, png_path):
    big = abs(d["shift"])
    intensity = .45 if big == 0 else min(1.0, .45 + big / 40.0)
    ch, ch_end = d["chapter"], d["chapter"] + 9

    chart, tip = chart_panel(d["paths"], 905, 118, 545, 420)

    parts = [speed_lines(intensity)]
    # narration box, top left
    parts.append('<rect class="narr" x="150" y="112" width="520" height="52"/>'
                 '<text class="narrt" x="170" y="148">HUNTER &#215; HUNTER &#183; %s 10 CHAPTERS</text>'
                 % d["view"].upper())
    # headline
    parts.append('<text class="kicker" x="152" y="232">CH. %d WILL COME OUT AROUND&#8230;</text>' % ch)
    parts.append('<text class="hero" x="146" y="388">%s</text>' % fmt(d["median"]).upper())
    parts.append('<text class="kicker sm" x="152" y="432">(THE MEDIAN FORECAST)</text>')

    if big:
        word = "EARLIER" if d["shift"] < 0 else "LATER"
        arrow = "&#9660;" if d["shift"] < 0 else "&#9650;"
        parts.append(burst(1180, 735, 245, 92, (1060, 560),
                           '%s %d DAYS %s<br/><span class="sm">THAN BEFORE THIS POST</span>'
                           % (arrow, big, word)))
        drawn_tip = None
    # 80% range bubble: tail up at the headline
    parts.append(bubble(420, 560, 270, 82, (330, 452),
                        '80%% CHANCE BETWEEN<br/><b>%s</b> AND <b>%s</b>'
                        % (fmt_short(d["i80"][0]).upper(), fmt_short(d["i80"][1]).upper())))
    # most likely week bubble
    parts.append(bubble(580, 742, 250, 74, (690, 640),
                        'MOST LIKELY SINGLE WEEK:<br/><b>%s</b> (%.0f%%)'
                        % (fmt(d["spike"][0]).upper(), d["spike"][1] * 100)))
    # progress: a shout when the run is fully drawn, a normal bubble otherwise
    if not big:
        if d["drawn"] >= 1.0:
            parts.append(burst(1185, 690, 235, 92, tip,
                               'CH. %d&#8211;%d<br/><b>ALL 10 DRAWN!</b>' % (ch, ch_end)))
        else:
            parts.append(bubble(1185, 690, 235, 80, tip,
                                'CH. %d&#8211;%d<br/><b>%.0f%% DRAWN</b>' % (ch, ch_end, d["drawn"] * 100)))
    parts.append(chart)
    # footer stickers
    parts.append('<rect class="tag" x="60" y="836" width="200" height="40"/>'
                 '<text class="tagt" x="160" y="864" text-anchor="middle">@HxHforecast</text>')
    parts.append('<rect class="tag" x="1290" y="836" width="250" height="40"/>'
                 '<text class="tagt" x="1415" y="864" text-anchor="middle">UPDATED %s</text>'
                 % fmt(d["updated"]).upper())

    html = """<!doctype html><html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Patrick+Hand+SC&display=block" rel="stylesheet">
<style>
html,body{margin:0;background:#fff}
svg{display:block}
.speed polygon{fill:#000}
.narr{fill:#000}
.narrt{fill:#fff;font:26px 'Bebas Neue';letter-spacing:3px}
.hero{font:168px 'Bebas Neue';fill:#000;letter-spacing:1px}
.kicker{font:34px 'Patrick Hand SC';fill:#000}
.kicker.sm{font-size:26px}
.bub{fill:#fff;stroke:#000;stroke-width:4.5;stroke-linejoin:round}
.btxt{width:100%%;height:100%%;display:flex;align-items:center;justify-content:center;
  text-align:center;font:30px/1.12 'Patrick Hand SC';color:#000}
.btxt b{font-family:'Bebas Neue';font-weight:400;font-size:40px;letter-spacing:1px}
.btxt .sm{font-size:22px}
.panel{fill:#fff;stroke:#000;stroke-width:5}
.ptitle{font:24px 'Patrick Hand SC';fill:#000}
.tick{stroke:#000;stroke-width:1;stroke-dasharray:1 5}
.axl{font:19px 'Patrick Hand SC';fill:#000}
.old{fill:none;stroke:#000;stroke-width:2.4}
.live{fill:none;stroke:#000;stroke-width:6;stroke-linejoin:miter}
.tone{fill:url(#tone)}
.dot{fill:#000}.odot{fill:#fff;stroke:#000;stroke-width:2.5}
.rl{font:20px 'Patrick Hand SC';fill:#000}
.tag{fill:#fff;stroke:#000;stroke-width:3}
.tagt{font:24px 'Patrick Hand SC';fill:#000}
</style></head><body>
<svg width="%d" height="%d" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">
<defs><pattern id="tone" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
<circle cx="4.5" cy="4.5" r="1.6" fill="#000"/></pattern></defs>
<rect width="100%%" height="100%%" fill="#fff"/>
%s
<rect x="2" y="2" width="%d" height="%d" fill="none" stroke="#000" stroke-width="4"/>
</svg></body></html>""" % (W, H, W, H, "\n".join(parts), W - 4, H - 4)

    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", "--window-size=%d,%d" % (W, H),
                    "--virtual-time-budget=8000", "--screenshot=%s" % png_path,
                    "file://" + os.path.abspath(html_path)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", type=int, default=421)
    ap.add_argument("--demo", type=int, default=None,
                    help="pretend the median moved N days (negative = earlier)")
    args = ap.parse_args()
    d = card_data(args.chapter, args.demo)
    stem = "%s_ch%d_manga%s" % (d["updated"].strftime("%Y%m%d"), args.chapter,
                                "" if args.demo is None else "_demo%+d" % args.demo)
    html_path = os.path.join(OUT, stem + ".html")
    png_path = os.path.join(OUT, stem + ".png")
    render(d, html_path, png_path)
    print("card -> %s" % os.path.relpath(png_path, D()))


if __name__ == "__main__":
    main()
