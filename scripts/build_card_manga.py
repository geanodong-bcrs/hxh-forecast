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
  - Generic manga vocabulary only: no logo or characters. The one exception is
    the `sketch` layout's progress panel, which uses Togashi's own X avatar
    (the dog he draws for himself) to stand for him — requested 2026-11-05.
    The Jump spines are drawn generic and cropped, never the real logo.
"""
import argparse
import glob
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

    # Baseline for "what changed": the forecast right after Togashi's last post,
    # i.e. what the previous reply card showed.
    base, n_posts = None, 0
    rid = delta.get("effect_run_id")
    if rid:
        path = D("data", "forecasts", "%s_batch%d_posterior.json" % (rid, post["batch"]))
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                b = json.load(fh)
            bpmf = b["posterior_pmf"] if view == "Next" else (b.get("next_batch") or {}).get("pmf") or []
            base = {"run_id": rid, "pmf": bpmf,
                    "median": date.fromisoformat(b["median"] if view == "Next"
                                                 else b["next_batch"]["median"]),
                    "asof": date.fromisoformat(b["forecast_timestamp"][:10])}
            # tweet-triggered forecasts after the baseline = new posts since then
            for f in glob.glob(D("data", "forecasts", "*_batch%d_posterior.json" % post["batch"])):
                r = os.path.basename(f).split("_")[0]
                if rid < r <= post["run_id"]:
                    with open(f, encoding="utf-8") as fh:
                        s = json.load(fh)
                    n_posts += s.get("trigger") == "tweet" and s.get("provenance") != "replay"
    return {
        "pmf": [(date.fromisoformat(x), p) for x, p in pmf],
        "asof": date.fromisoformat(post["forecast_timestamp"][:10]),
        "base": base, "new_posts": n_posts,
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

    write_card(parts, html_path, png_path)


def write_card(parts, html_path, png_path):
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
.hero2{font:250px 'Bebas Neue';fill:#000}
.note{font:26px 'Patrick Hand SC';fill:#000}
.cell{fill:#fff;stroke:#000;stroke-width:4}
.cellbar{fill:url(#tone);stroke:#000;stroke-width:2}
.cdate{font:25px 'Patrick Hand SC';fill:#000}
.cpct{font:44px 'Bebas Neue';fill:#000}
.gap{fill:url(#hatch);stroke:#000;stroke-width:3}
.gapt{font:19px 'Patrick Hand SC';fill:#000}
.cap{fill:#fff;stroke:#000;stroke-width:4}
.capt{font:25px 'Patrick Hand SC';fill:#000}
.capt b{font-family:'Bebas Neue';font-weight:400;font-size:30px;letter-spacing:1px}
.bar{fill:#fff;stroke:#000;stroke-width:3}
.bar.top{fill:url(#tone)}
.axis{stroke:#000;stroke-width:4}
.axl.lg{font-size:26px}
.btxt.sk{flex-direction:column}
.btxt.sk>div{display:flex;flex-direction:column;align-items:center;line-height:1.05}
.rk{font:44px 'Bebas Neue';letter-spacing:2px}
.mp{font:26px 'Patrick Hand SC'}.mp.s{font-size:20px}
.btxt.sk b.r1{font-size:56px}.btxt.sk b.r2{font-size:40px}.btxt.sk b.r3{font-size:30px}
.iss{font:30px 'Bebas Neue';letter-spacing:1px}.iss.r2{font-size:24px}.iss.r3{font-size:20px}
.ptl{font:40px 'Patrick Hand SC';fill:#000}
.pct{font:56px 'Bebas Neue';fill:#000}
.pbar{fill:none;stroke:#000;stroke-width:4}
.avatar{filter:grayscale(1) brightness(1.35) contrast(2.4);mix-blend-mode:multiply}
.spine{fill:#fff;stroke:#000;stroke-width:3}.spine.front{stroke-width:5}
.spt{font:bold 30px 'Hiragino Sans','Hiragino Kaku Gothic ProN',sans-serif;fill:#000;letter-spacing:4px}
.spbox{fill:#fff;stroke:#000;stroke-width:2.5}
.spno{font:30px 'Bebas Neue';fill:#000}.spno.q{font-size:52px}.spbox.front{stroke-width:4}
.nofill{fill:none}
</style></head><body>
<svg width="%d" height="%d" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg">
<defs><pattern id="tone" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
<circle cx="4.5" cy="4.5" r="1.6" fill="#000"/></pattern>
<pattern id="hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
<line x1="0" y1="0" x2="0" y2="10" stroke="#000" stroke-width="2"/></pattern></defs>
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


def window_chance(pmf, start, weeks=4):
    """Chance the run starts in [start, start + weeks): the weather-style number.

    Rolling, measured from the forecast date, so a quiet week leaves it about
    where it was. Fixed-horizon odds ("by end of 2026") fall as the date nears.
    """
    end = start + timedelta(weeks=weeks)
    return sum(p for d, p in pmf if start <= d < end)


def pmf_median(pmf):
    tot, acc = sum(p for _, p in pmf), 0.0
    for d, p in pmf:
        acc += p / tot
        if acc >= .5:
            return d


def attribution(d):
    """Split the median's move since the last post into time and the rest.

    Time-only: take the baseline forecast, drop the issues that have since
    gone by without HxH, and renormalise. Whatever that does not explain came
    from new posts or from a model change.
    """
    b = d["base"]
    if not b or not b["pmf"]:
        return None
    first_open = d["pmf"][0][0]
    kept = [(date.fromisoformat(x), p) for x, p in b["pmf"]
            if date.fromisoformat(x) >= first_open]
    passed = sum(1 for x, _ in b["pmf"] if date.fromisoformat(x) < first_open)
    t_only = pmf_median(kept)
    return {"since": b["asof"], "passed": passed,
            "time_days": (t_only - b["median"]).days,
            "rest_days": (d["median"] - t_only).days,
            "base_chance": window_chance([(date.fromisoformat(x), p) for x, p in b["pmf"]],
                                         b["asof"])}


def outlook_strip(pmf, x0, y0, w, h, n=8):
    """The next n issues as a row of panels, like a weather app's daily icons.

    A week with no regular issue (combined issue / New Year) gets its own
    narrow hatched panel, so the strip still reads as consecutive weeks.
    """
    items, prev = [], None
    for dd, p in pmf:
        if prev and (dd - prev).days > 7:
            items.append(("gap", prev + timedelta(days=7), None))
        if sum(1 for k, _, _ in items if k == "issue") == n:
            break
        items.append(("issue", dd, p))
        prev = dd
    while items and items[-1][0] == "gap":
        items.pop()
    gut, gap_w = 12, 62
    n_issue = sum(1 for k, _, _ in items if k == "issue")
    n_gap = len(items) - n_issue
    cw = (w - gut * (len(items) - 1) - gap_w * n_gap) / float(n_issue)
    scale = .05   # bar full height = 5%; fixed so the bars are comparable card to card
    g, x = [], x0
    for kind, dd, p in items:
        if kind == "gap":
            g.append('<rect class="gap" x="%.1f" y="%d" width="%d" height="%d"/>'
                     % (x, y0 + 62, gap_w, h - 62))
            g.append('<text class="gapt" x="%.1f" y="%d" text-anchor="middle">NO</text>'
                     '<text class="gapt" x="%.1f" y="%d" text-anchor="middle">ISSUE</text>'
                     % (x + gap_w / 2, y0 + 22, x + gap_w / 2, y0 + 46))
            x += gap_w + gut
            continue
        g.append('<rect class="cell" x="%.1f" y="%d" width="%.1f" height="%d"/>' % (x, y0, cw, h))
        g.append('<text class="cdate" x="%.1f" y="%d" text-anchor="middle">%s</text>'
                 % (x + cw / 2, y0 + 32, dd.strftime("%-d %b").upper()))
        bh = (h - 100) * min(p / scale, 1)
        g.append('<rect class="cellbar" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
                 % (x + 18, y0 + h - 52 - bh, cw - 36, bh))
        g.append('<text class="cpct" x="%.1f" y="%d" text-anchor="middle">%.1f%%</text>'
                 % (x + cw / 2, y0 + h - 12, p * 100))
        x += cw + gut
    return "\n".join(g)


def render_outlook(d, html_path, png_path):
    """Weather-style card: the near-term chance leads, the median follows."""
    ch, ch_end = d["chapter"], d["chapter"] + 9
    chance = window_chance(d["pmf"], d["asof"])
    att = attribution(d)
    big = abs(att["rest_days"]) if att and d["new_posts"] else 0
    intensity = .45 if big < 7 else min(1.0, .45 + big / 40.0)

    parts = [speed_lines(intensity)]
    parts.append('<rect class="narr" x="150" y="100" width="520" height="52"/>'
                 '<text class="narrt" x="170" y="136">HUNTER &#215; HUNTER &#183; %s 10 CHAPTERS</text>'
                 % d["view"].upper())
    parts.append('<text class="kicker" x="152" y="205">CHANCE CH. %d&#8211;%d STARTS</text>'
                 '<text class="kicker" x="152" y="243">IN THE NEXT 4 WEEKS</text>' % (ch, ch_end))
    parts.append('<text class="hero2" x="140" y="455">%.0f%%</text>' % (chance * 100))
    if att:
        parts.append('<text class="note" x="152" y="492">%s FROM %.0f%% ON %s</text>'
                     % ("UP" if chance > att["base_chance"] + .005 else
                        "DOWN" if chance < att["base_chance"] - .005 else "ABOUT THE SAME",
                        att["base_chance"] * 100, att["since"].strftime("%-d %b").upper()))
    parts.append(bubble(705, 330, 175, 88, (492, 395),
                        '50-50 BY<br/><b>%s</b>' % fmt(d["median"]).upper()))

    chart, tip = chart_panel(d["paths"], 905, 100, 545, 370)
    parts.append(chart)
    if d["drawn"] >= 1.0:
        # Sits on the panel's top edge like a sound effect, its short tail
        # dropping onto the end of the live line through empty space above 100%.
        parts.append(burst(1352, 92, 132, 40, (tip[0] - 4, tip[1] - 10),
                           '<b>ALL 10 DRAWN!</b>', spikes=18))

    parts.append('<text class="note" x="152" y="545">NEXT 8 ISSUES &#8212; CHANCE THE RUN STARTS IN EACH</text>')
    parts.append(outlook_strip(d["pmf"], 150, 562, 1300, 160))

    if att:
        if not d["new_posts"]:
            news = "NO NEW POSTS"
            rest = (" &#183; <b>%+d DAYS</b> FROM A MODEL UPDATE" % att["rest_days"]
                    if att["rest_days"] else "")
        else:
            news = "<b>%+d DAYS</b> FROM NEW POSTS" % att["rest_days"]
            rest = ""
        cap = ('SINCE %s: %d ISSUE%s WENT BY WITHOUT HXH (<b>%+d DAYS</b> TO THE 50-50 DATE) &#183; %s%s'
               % (att["since"].strftime("%-d %b").upper(), att["passed"],
                  "" if att["passed"] == 1 else "S", att["time_days"], news, rest))
        parts.append('<rect class="cap" x="150" y="756" width="1300" height="56"/>'
                     '<foreignObject x="160" y="756" width="1280" height="56">'
                     '<div xmlns="http://www.w3.org/1999/xhtml" class="btxt capt">'
                     '<div>%s</div></div></foreignObject>' % cap)

    parts.append('<rect class="tag" x="60" y="836" width="200" height="40"/>'
                 '<text class="tagt" x="160" y="864" text-anchor="middle">@HxHforecast</text>')
    parts.append('<rect class="tag" x="1290" y="836" width="250" height="40"/>'
                 '<text class="tagt" x="1415" y="864" text-anchor="middle">UPDATED %s</text>'
                 % fmt(d["updated"]).upper())
    write_card(parts, html_path, png_path)


# ------------------------------------------------------------------ sketch layout

AVATAR = D("data", "cards", "assets", "togashi_avatar.jpg")


def issue_label(day):
    """WSJ issue label ("2027 No.10") for an on-sale date, projected if needed.

    Projected issues carry no label, so this copies the label of the issue the
    projection was copied from: the same date a whole number of weeks nearest
    to k years earlier (build_batch_prior.project_calendar), with the year +k.
    """
    from build_batch_prior import load_calendar
    obs = {c["on_sale"]: (c["year"], c["label"]) for c in load_calendar()}
    for k in range(0, 8):
        src = day - timedelta(weeks=round(365.2425 * k / 7.0))
        if src in obs and obs[src][1]:
            y, lab = obs[src]
            return "%d No.%s" % (y + k, lab.replace("号", "").replace("・", "-"))
    return "No.?"


def bar_chart(pmf, x0, y0, w, h):
    """Weekly bars in ink. Returns (svg, {rank: (x_centre, y_top)})."""
    pl, pr, pt, pb = 70, 30, 40, 56
    ix, iy, iw, ih = x0 + pl, y0 + pt, w - pl - pr, h - pt - pb
    # Show from the earliest possible issue to the 90th percentile: the long
    # thin tail would only squash the bars that matter.
    pts, cum, shown = sorted(pmf), 0.0, []
    for d, pv in pts:
        shown.append((d, pv))
        cum += pv
        if cum >= .90:
            break
    t0, t1 = shown[0][0], shown[-1][0] + timedelta(days=7)
    span = (t1 - t0).days
    X = lambda d: ix + iw * (d - t0).days / span
    top = max(pv for _, pv in shown)
    # Bars use the lower ~60% so the bubbles have the top band to themselves.
    Y = lambda pv: iy + ih - ih * pv / (top * 1.65)
    ranked = sorted(shown, key=lambda r: -r[1])[:3]
    rank = {d: i + 1 for i, (d, _) in enumerate(ranked)}
    g = ['<rect class="panel" x="%d" y="%d" width="%d" height="%d"/>' % (x0, y0, w, h)]
    bw = iw * 7 / span
    tips = {}
    for d, pv in shown:
        x = X(d)
        cls = "bar top" if d in rank else "bar"
        g.append('<rect class="%s" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
                 % (cls, x + bw * .1, Y(pv), bw * .8, iy + ih - Y(pv)))
        if d in rank:
            tips[rank[d]] = (x + bw / 2, Y(pv))
    g.append('<line class="axis" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
             % (ix, iy + ih, ix + iw, iy + ih))
    g.append('<line class="axis" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
             % (ix, iy - 10, ix, iy + ih))
    m = date(t0.year, t0.month, 1)
    while m < t1:
        if t0 <= m and X(m) < ix + iw - 60:
            g.append('<text class="axl lg" x="%.1f" y="%.1f">%s</text>'
                     % (X(m) + 4, iy + ih + 34, m.strftime("%b").upper()
                        + (" ’%s" % m.strftime("%y") if m.month == 1 else "")))
            g.append('<line class="tick" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                     % (X(m), iy + ih, X(m), iy + ih + 12))
        m = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    g.append('<text class="axl lg" transform="translate(%.1f,%.1f) rotate(-90)" '
             'text-anchor="middle">PROBABILITY</text>' % (x0 + 40, iy + ih / 2))
    return "\n".join(g), tips, ranked


def spines_panel(x0, y0, w, h, asof):
    """Weekly Jump spines on a shelf, tilted and cropped by the panel frame.

    Only a fragment of the masthead shows, on purpose. The front spine is the
    next issue, its number a big question mark; behind it, the issues already
    out without Hunter x Hunter.
    """
    from build_batch_prior import load_calendar
    past = [c["label"].replace("号", "").replace("・", "-")
            for c in load_calendar() if c["on_sale"] <= asof][-6:][::-1]
    cid = "spclip"
    g = ['<clipPath id="%s"><rect x="%d" y="%d" width="%d" height="%d"/></clipPath>'
         % (cid, x0, y0, w, h),
         '<rect class="panel" x="%d" y="%d" width="%d" height="%d"/>' % (x0, y0, w, h),
         '<g clip-path="url(#%s)"><g transform="translate(%d,%d) rotate(-11)">'
         % (cid, x0 + 40, y0 + h - 26)]
    sw, sl = 66, 1000
    for i in range(6, -1, -1):          # back to front, so the front spine overlaps
        y = -i * (sw + 4) - sw
        front = i == 0
        g.append('<rect class="spine%s" x="%d" y="%d" width="%d" height="%d"/>'
                 % (" front" if front else "", -i * 14, y, sl, sw))
        bx = -i * 14 + 14
        g.append('<rect class="spbox%s" x="%d" y="%d" width="%d" height="%d"/>'
                 % (" front" if front else "", bx, y + 7, 70 if front else 56, sw - 14))
        g.append('<text class="spno%s" x="%d" y="%d" text-anchor="middle">%s</text>'
                 % (" q" if front else "", bx + (35 if front else 28), y + sw - 14,
                    "?" if front else (past[i - 1] if i - 1 < len(past) else "")))
        g.append('<text class="spt" x="%d" y="%d">週刊少年ジ</text>'
                 % (bx + (92 if front else 76), y + sw - 16))
    g.append('</g></g>')
    g.append('<rect class="panel nofill" x="%d" y="%d" width="%d" height="%d"/>' % (x0, y0, w, h))
    return "\n".join(g)


def progress_panel(d, x0, y0, w, h):
    first = d["chapter"] - (d["chapter"] - 1) % 10
    frac = max(0.0, min(1.0, d["drawn"]))
    bx, by, bw, bh = x0 + 36, y0 + 108, w - 300, 46
    g = ['<rect class="panel" x="%d" y="%d" width="%d" height="%d"/>' % (x0, y0, w, h),
         '<text class="ptl" x="%d" y="%d">CH.%d&#8211;%d PROGRESS</text>'
         % (x0 + 36, y0 + 70, first, first + 9),
         '<text class="pct" x="%d" y="%d" text-anchor="end">%d%%</text>'
         % (bx + bw, y0 + 76, round(frac * 100)),
         '<clipPath id="pbclip"><rect x="%d" y="%d" width="%.1f" height="%d" rx="%d"/></clipPath>'
         % (bx, by, bw * frac, bh, bh / 2),
         '<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="url(#hatch)" clip-path="url(#pbclip)"/>'
         % (bx, by, bw, bh, bh / 2),
         '<rect class="pbar" x="%d" y="%d" width="%d" height="%d" rx="%d"/>'
         % (bx, by, bw, bh, bh / 2)]
    if os.path.exists(AVATAR):
        g.append('<image class="avatar" href="file://%s" x="%d" y="%d" width="%d" height="%d"/>'
                 % (os.path.abspath(AVATAR), x0 + w - 236, y0 + 10, 200, 200))
    return "\n".join(g)


def render_sketch(d, html_path, png_path):
    """The layout from private/story/image_working/paper_sketch_manga_style.pdf:
    weekly probability bars, the top three weeks in bubbles, production progress
    with Togashi's dog, and the next issue's spine with a question mark. No
    probabilities, median or update stamp — by request."""
    parts = []
    chart, tips, ranked = bar_chart(d["pmf"], 60, 120, 1480, 500)
    parts.append(chart)
    parts.append(progress_panel(d, 60, 650, 820, 220))
    parts.append(spines_panel(910, 650, 630, 220, d["asof"]))
    # Bubbles break out of the top of the frame, No.1 biggest; 2 and 3 overlap
    # it like the sketch, and only No.1 carries a tail.
    spots = {1: (900, 150, 190, 124), 2: (1185, 196, 146, 100), 3: (1400, 236, 116, 84)}
    for r in (3, 2, 1):
        if r not in tips:
            continue
        cx, cy, rx, ry = spots[r]
        day = ranked[r - 1][0]
        html = ('<span class="rk">NO.%d</span><span class="mp%s">MOST PROBABLE</span>'
                '<b class="r%d">%s</b><span class="iss r%d">ISSUE %s</span>'
                % (r, " s" if r > 1 else "", r, fmt(day).upper(), r, issue_label(day)))
        tip = (tips[r][0], tips[r][1] - 6) if r == 1 else (cx - rx * .9, cy + ry * .55)
        parts.append(bubble(cx, cy, rx, ry, tip, html, cls="sk"))
    write_card(parts, html_path, png_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", choices=["sketch", "outlook", "median"], default="sketch",
                    help="sketch: the paper-sketch layout (default); outlook / median: earlier drafts")
    ap.add_argument("--chapter", type=int, default=421)
    ap.add_argument("--demo", type=int, default=None,
                    help="pretend the median moved N days (negative = earlier)")
    args = ap.parse_args()
    d = card_data(args.chapter, args.demo)
    stem = "%s_ch%d_manga%s%s" % (d["updated"].strftime("%Y%m%d"), args.chapter,
                                  "" if args.layout == "median" else "_" + args.layout,
                                  "" if args.demo is None else "_demo%+d" % args.demo)
    html_path = os.path.join(OUT, stem + ".html")
    png_path = os.path.join(OUT, stem + ".png")
    {"sketch": render_sketch, "outlook": render_outlook,
     "median": render}[args.layout](d, html_path, png_path)
    print("card -> %s" % os.path.relpath(png_path, D()))


if __name__ == "__main__":
    main()
