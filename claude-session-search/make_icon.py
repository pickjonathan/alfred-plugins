#!/usr/bin/env python3
"""Generate a Claude-style sunburst icon (icon.png) for the Alfred workflow.

Draws the radial-burst mark in white on Claude's clay background, supersampled
4x then downscaled for clean anti-aliased edges. No external assets needed.
"""
import math
from PIL import Image, ImageDraw

OUT = "icon.png"
SIZE = 512
SS = 4  # supersample factor
S = SIZE * SS

CLAY = (217, 119, 87, 255)      # Claude clay / terracotta
WHITE = (250, 248, 245, 255)    # warm white

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# Rounded-square background.
radius = int(S * 0.235)
d.rounded_rectangle([0, 0, S - 1, S - 1], radius=radius, fill=CLAY)

cx = cy = S / 2.0

# The Claude mark reads as a radial burst of tapered spokes of slightly
# varying length. Use an odd-ish count and alternating lengths for organic feel.
N = 12
R_long = S * 0.345
R_short = S * 0.285
half_w = S * 0.030   # half-width of each spoke at its widest (near center)
bulge = 0.42         # where along the spoke it is widest (0=center,1=tip)

for i in range(N):
    ang = (2 * math.pi * i / N) - math.pi / 2.0
    R = R_long if i % 2 == 0 else R_short

    # Unit vectors along the spoke and perpendicular to it.
    ux, uy = math.cos(ang), math.sin(ang)
    px, py = -uy, ux

    tip = (cx + ux * R, cy + uy * R)
    base = (cx + ux * (S * 0.012), cy + uy * (S * 0.012))
    mid_r = R * bulge
    left = (cx + ux * mid_r + px * half_w, cy + uy * mid_r + py * half_w)
    right = (cx + ux * mid_r - px * half_w, cy + uy * mid_r - py * half_w)

    d.polygon([base, left, tip, right], fill=WHITE)

# Small solid hub so the spokes read as joined at the center.
hub = S * 0.052
d.ellipse([cx - hub, cy - hub, cx + hub, cy + hub], fill=WHITE)

img = img.resize((SIZE, SIZE), Image.LANCZOS)
img.save(OUT)
print("wrote", OUT, img.size)
