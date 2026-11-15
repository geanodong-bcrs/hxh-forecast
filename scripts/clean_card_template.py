#!/usr/bin/env python3
"""Clean a hand-drawn card template scan for use as the card background.

    python3 scripts/clean_card_template.py

Pencil placeholders (lighter than ink) are removed only where the data layer
draws: the plot area, the burst bubble and the month row. The chapter plate
keeps the artist's own pencil "NO.421".
Pencil shading elsewhere is kept. The page margin is cropped off.
Coordinates are in the scan's own pixels.
"""
import os

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
SRC = D("private", "story", "image_working", "weekly_forecast_template.jpeg")
OUT = D("data", "cards", "assets", "weekly_forecast_template_clean.png")
CROP = (540, 72, 2800, 2400)          # left, top, right, bottom


def main():
    a = np.array(Image.open(SRC).convert("L")).astype(np.uint8)
    S = lambda v: int(v * 1.44)       # measured on a 1/1.44 preview
    # Burst interior: the open region around its centre, pencil holes filled.
    lab, _ = nd.label(a >= 140)
    inside = nd.binary_fill_holes(lab == lab[S(520), S(1360)])
    a[nd.binary_erosion(inside, iterations=2)] = 255
    r = a[S(346):S(1161), S(402):S(1900)]
    r[r > 110] = 255                  # plot interior: pencil only
    a[S(1060):S(1110), S(402):S(1900)] = 255   # pencil month row
    a[a > 232] = 255                  # paper to white
    Image.fromarray(a).crop(CROP).save(OUT)
    print("template ->", os.path.relpath(OUT, D()))


if __name__ == "__main__":
    main()
