#!/usr/bin/env python3
"""Draw the Shueisha building's windows onto the cleaned card template.

    python3 scripts/draw_building_windows.py   (run after clean_card_template.py)

Reference: private/story/image_working/shueisha_building.jpeg — a worm's-eye
view: punched windows on the granite right face, a glass curtain wall on the
left. The drawing is in three-point perspective; its vertical edges meet at
VP_UP, measured from the inked lines. Floors are equally spaced in 3-D, so in
the image 1/distance-to-VP is linear in floor index; columns likewise toward
the horizontal vanishing points. Windows are clipped to the open paper of each
face, so the sign, pole, dog and books stay in front.
"""
import os

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
PATH = D("data", "cards", "assets", "weekly_forecast_template_clean.png")

VP_UP = np.array([1155.0, 984.0])
VP_R = np.array([3600.0, 3208.0])     # on the right roofline, extended
VP_L = np.array([55.0, 3208.0])       # on the left roofline, extended
Y_ROOF, Y_FLOOR12 = 1528.0, 2328.0    # line D: roof, and floor 12 down
N_FLOORS = 12

# Face polygons (template px), from the inked corner lines.
A1, A2, A3 = (998, 1553), (1053, 1535), (1103, 1528)
FACES = {
    "R": [A3, (1438, 1753), (1653, 2328), (1036, 2328)],
    "M": [A2, A3, (1036, 2328), (911, 2328)],
    "L1": [A1, A2, (975, 1978), (850, 2085)],
    "L0": [A1, (850, 2085), (975, 1978), (911, 2328), (556, 2328)],
}
SEEDS = [(1300, 1800), (1560, 2250), (1055, 1720), (975, 1800), (895, 1800),
         (1000, 2200), (1120, 2150)]


def on_d(y):
    """Point on corner line D (A3 down to the sign) at height y."""
    return np.array([1100 - 0.0875 * (y - 1600), y])


def floor_y(i):
    """Image y on line D of floor line i (0 = roof), equal 3-D spacing."""
    d0, d1 = Y_ROOF - VP_UP[1], Y_FLOOR12 - VP_UP[1]
    inv = 1 / d0 + (i / N_FLOORS) * (1 / d1 - 1 / d0)
    return VP_UP[1] + 1 / inv


def meet(p1, p2, q1, q2):
    """Intersection of line p1-p2 with line q1-q2."""
    d1, d2 = p2 - p1, q2 - q1
    t = np.cross(q1 - p1, d2) / np.cross(d1, d2)
    return p1 + t * d1


def column_point(row_a, vp_h, x_edge_a, x_edge_b, k, n):
    """Point k/n of the way across a row, equally spaced in 3-D toward vp_h.

    The row is the line through row_a toward vp_h; x_edge_a/b are the face's
    two vertical edges (each a pair of points through VP_UP)."""
    pa = meet(row_a, vp_h, *x_edge_a)
    pb = meet(row_a, vp_h, *x_edge_b)
    ea, eb = np.linalg.norm(pa - vp_h), np.linalg.norm(pb - vp_h)
    e = 1 / (1 / ea + (k / n) * (1 / eb - 1 / ea))
    return vp_h + (pa - vp_h) / ea * e


def cell(vp_h, edge_a, edge_b, n_cols, i0, i1, k0, k1):
    """Quad for floors i0..i1 and columns k0..k1 (fractional) of a face."""
    pts = []
    for i, k in ((i0, k0), (i0, k1), (i1, k1), (i1, k0)):
        row = on_d(floor_y(i))
        base = column_point(row, vp_h, edge_a, edge_b, k, n_cols)
        # the column is the line from VP_UP through `base`; it meets row i there
        pts.append(tuple(base))
    return pts


def main():
    img = Image.open(PATH).convert("L")
    a = np.array(img)
    # Open paper belonging to the building: components reached from seeds.
    lab, _ = nd.label(a > 200)
    paper = np.isin(lab, [lab[y, x] for x, y in SEEDS if lab[y, x]])
    paper = nd.binary_erosion(paper, iterations=5)

    ink = Image.new("L", img.size, 0)          # 255 = draw black
    glint = Image.new("L", img.size, 0)        # 255 = force white
    di, dg = ImageDraw.Draw(ink), ImageDraw.Draw(glint)
    edge_d = (VP_UP, on_d(2328))
    edge_r = (VP_UP, np.array([1653.0, 2328.0]))
    edge_c = (VP_UP, np.array([911.0, 2328.0]))
    edge_b = (VP_UP, np.array([850.0, 2085.0]))
    edge_far_l = (VP_UP, np.array([420.0, 2328.0]))

    # Right face: punched windows, 9 columns, dark glass with a glint.
    for i in range(0, N_FLOORS + 3):
        for k in range(9):
            q = cell(VP_R, edge_d, edge_r, 9, i + .32, i + .86, k + .2, k + .8)
            di.polygon(q, fill=255)
            # glint: a thin diagonal from upper-left toward the middle
            p0 = np.array(q[0]) * .8 + np.array(q[2]) * .2
            p1 = np.array(q[0]) * .45 + np.array(q[2]) * .55
            w = max(2, int(np.linalg.norm(np.array(q[1]) - np.array(q[0])) * .07))
            dg.line([tuple(p0 + (0, 6)), tuple(p1 + (0, 6))], fill=255, width=w)

    # Left faces: glass curtain wall, a pane per floor between thin mullions.
    for edge_a, edge_b2, n in ((edge_c, edge_d, 2), (edge_b, edge_c, 2),
                               (edge_far_l, edge_b, 5)):
        # The left faces' roofline (line A) sits above floor 0 as counted on
        # line D, so start a few floors higher; the face polygon clips them.
        for i in range(-4, N_FLOORS + 3):
            for k in range(n):
                q = cell(VP_L, edge_a, edge_b2, n, i + .12, i + .94, k + .08, k + .92)
                di.polygon(q, fill=255)
                p0 = np.array(q[0]) * .7 + np.array(q[2]) * .3
                p1 = np.array(q[0]) * .4 + np.array(q[2]) * .6
                dg.line([tuple(p0), tuple(p1)], fill=255, width=3)

    faces = Image.new("L", img.size, 0)
    for poly in FACES.values():
        ImageDraw.Draw(faces).polygon(poly, fill=255)
    where = paper & (np.array(faces) > 0)
    dark = where & (np.array(ink) > 0) & ~(np.array(glint) > 0)
    a[dark] = 20
    Image.fromarray(a).save(PATH)
    print("windows: %d px inked" % dark.sum())


if __name__ == "__main__":
    main()
