#!/usr/bin/env python3
"""Clean the hand-drawn card template scan for use as the card background.

    python3 scripts/clean_card_template.py

The artist inked everything that stays (title, NO.421 plate, burst, building
windows, magazines, dog). Inside the plot panel, everything except the inked
burst outline is a pencil placeholder (axes, months, "Most probable: Feb 5")
and is erased; the data layer redraws it. The building top that floats over
the panel is left alone. Elsewhere only the paper is whitened, gently: the
artist has already cleaned the lower panel.
The scan is upscaled SCALE x so the vector data layer has room; coordinates in
build_card_manga.py are in the upscaled pixels.
"""
import os

import numpy as np
from PIL import Image
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
SRC = D("private", "story", "image_working", "weekly_forecaste_template.jpg")
OUT = D("data", "cards", "assets", "weekly_forecast_template_clean.png")
SCALE = 3
PLOT = (158, 595, 19, 830)           # y0, y1, x0, x1: plot panel interior, scan px
# The Shueisha building's top floats over the middle panel; never touch it.
BUILDING_TOP = (560, 600, 340, 520)  # y0, y1, x0, x1, scan px


def main():
    a = np.array(Image.open(SRC).convert("L")).astype(np.float32)
    y0, y1, x0, x1 = PLOT
    r = a[y0:y1, x0:x1]
    # Ink strokes (burst, panel border, the building top poking in) reach near
    # black; pencil never goes below ~80. Keep only components with real ink.
    lab, n = nd.label(r < 150)
    idx = range(1, n + 1)
    size = nd.sum(np.ones_like(r), lab, idx)
    darkest = nd.minimum(r, lab, idx)
    ink = [i for i, sz, mn in zip(idx, size, darkest) if sz >= 15 and mn < 70]
    keep = nd.binary_dilation(np.isin(lab, ink), iterations=2)   # with the anti-aliased edge
    by0, by1, bx0, bx1 = BUILDING_TOP
    keep[by0 - y0:by1 - y0, bx0 - x0:bx1 - x0] = True
    r[~keep] = 255
    a[y0:y1, x0:x1] = r
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    im = im.resize((im.width * SCALE, im.height * SCALE), Image.LANCZOS)
    b = np.asarray(im).astype(np.float32)
    # gentle levels: paper to white, the artist's grey tones kept
    b = ((b - 25) / (232 - 25) * 255).clip(0, 255)
    Image.fromarray(b.astype(np.uint8)).save(OUT)
    print("template ->", os.path.relpath(OUT, D()), im.size)


if __name__ == "__main__":
    main()
