import micropython
import time
from display_drivers.nt35510 import NT35510, cx_bright, color565
import machine
machine.freq(240_000_000)
d = NT35510()


# ------------------------------------------------------------------
# Precomputed quarter-curve point tables
# Format:
#   first item = radius
#   remaining items = (x, y) offsets for top-left quarter
# ------------------------------------------------------------------

_CURVES = {
    1:  (1,  (0, 0)),
    2:  (2,  (-1, 0), (-1, -1), (0, -1)),
    3:  (3,  (-2, 0), (-2, -1), (-2, -2), (-1, -2), (0, -2)),
    4:  (4,  (-3, 0), (-3, -1), (-3, -2), (-2, -2), (-2, -3), (-1, -3), (0, -3)),
    5:  (5,  (-4, 0), (-4, -1), (-4, -2), (-3, -3), (-2, -4), (-1, -4), (0, -4)),
    6:  (6,  (-5, 0), (-5, -1), (-5, -2), (-5, -3), (-4, -3), (-4, -4),
            (-3, -4), (-3, -5), (-2, -5), (-1, -5), (0, -5)),
    7:  (7,  (-6, 0), (-6, -1), (-6, -2), (-6, -3), (-5, -3), (-5, -4),
            (-4, -4), (-4, -5), (-3, -5), (-3, -6), (-2, -6), (-1, -6), (0, -6)),
    8:  (8,  (-7, 0), (-7, -1), (-7, -2), (-7, -3), (-6, -3), (-6, -4),
            (-6, -5), (-5, -5), (-5, -6), (-4, -6), (-3, -6), (-3, -7),
            (-2, -7), (-1, -7), (0, -7)),
    9:  (9,  (-8, 0), (-8, -1), (-8, -2), (-8, -3), (-8, -4), (-7, -4),
            (-7, -5), (-6, -5), (-6, -6), (-5, -6), (-5, -7), (-4, -7),
            (-3, -8), (-2, -8), (-1, -8), (0, -8)),
    10: (10, (-9, 0), (-9, -1), (-9, -2), (-9, -3), (-9, -4), (-8, -4),
            (-8, -5), (-7, -6), (-7, -7), (-6, -7), (-5, -8), (-4, -8),
            (-4, -9), (-3, -9), (-2, -9), (-1, -9), (0, -9)),
}

# ------------------------------------------------------------------
# Public wrapper
# Convert color and fetch curve table OUTSIDE viper
# ------------------------------------------------------------------

def round_rect(fb, x, y, w, h, color, fill=True, curve=5):
    if isinstance(color, tuple):
        color = color565(*color)

    x = int(x)
    y = int(y)
    w = int(w)
    h = int(h)
    curve = int(curve)

    if w <= 0 or h <= 0:
        return

    # clamp radius so it cannot exceed half the box
    max_curve = (w if w < h else h) >> 1
    if curve < 0:
        curve = 0
    elif curve > max_curve:
        curve = max_curve

    if curve == 0:
        if fill:
            fb.fill_rect(x, y, w, h, color)
        else:
            fb.rect(x, y, w, h, color)
        return

    pts = _CURVES.get(curve)
    if pts is None:
        # fallback if you ever want >10: generate once, cache globally
        pts = build_curve(curve)
        _CURVES[curve] = pts

    if fill:
        _round_rect_fill(fb, x, y, w, h, int(color), pts)
    else:
        _round_rect_outline(fb, x, y, w, h, int(color), pts)

@micropython.viper
def _round_rect_fill(fb: object, x: int, y: int, w: int, h: int, color: int, pts: object):
    # convert width/height to inclusive edge values
    w1 = w - 1
    h1 = h - 1
    r = int(pts[0])

    # center body
    inner_w = w - (r << 1)
    if inner_w > 0:
        fb.fill_rect(x + r, y, inner_w, h, color)

    # side columns + rounded vertical fills
    left_x = x
    right_x = x + w1

    mid_h = h - (r << 1)
    if mid_h > 0:
        fb.vline(left_x,  y + r, mid_h, color)
        fb.vline(right_x, y + r, mid_h, color)

    n = int(len(pts))
    i = 1
    while i < n:
        pt = pts[i]
        px = int(pt[0])
        py = int(pt[1])

        yy = y + r + py
        ll = h - ((r + py) << 1)
        if ll > 0:
            fb.vline(x + r + px,      yy, ll, color)
            fb.vline(x + w1 - r - px, yy, ll, color)

        i += 1


@micropython.viper
def _round_rect_outline(fb: object, x: int, y: int, w: int, h: int, color: int, pts: object):
    w1 = w - 1
    h1 = h - 1
    r = int(pts[0])

    # straight edges
    inner_w = w - (r << 1)
    inner_h = h - (r << 1)

    if inner_w > 0:
        fb.hline(x + r, y,      inner_w, color)
        fb.hline(x + r, y + h1, inner_w, color)

    if inner_h > 0:
        fb.vline(x,      y + r, inner_h, color)
        fb.vline(x + w1, y + r, inner_h, color)

    # corner pixels
    n = int(len(pts))
    i = 1
    while i < n:
        pt = pts[i]
        px = int(pt[0])
        py = int(pt[1])

        # top-left
        fb.pixel(x + r + px,      y + r + py,      color)
        # top-right
        fb.pixel(x + w1 - r - px, y + r + py,      color)
        # bottom-left
        fb.pixel(x + r + px,      y + h1 - r - py, color)
        # bottom-right
        fb.pixel(x + w1 - r - px, y + h1 - r - py, color)

        i += 1


p = 0
t0 = time.ticks_ms()
while p < 1:#_000:
    round_rect(d, 10, 10, 400, 500, (200,255,180), fill=False, curve=10)
    round_rect(d, 11, 11, 398, 498, (200,215,130), fill=False, curve=9)
    round_rect(d, 12, 12, 396, 496, (0,55,180), fill=True, curve=8)
    p += 1
t1 = time.ticks_ms()
print(f"Time taken: {t1 - t0} ms")

# import os

# def list_modules(path="/", prefix=""):
#     try:
#         entries = list(os.ilistdir(path))
#     except OSError:
#         return

#     for name, typ, *rest in entries:
#         full = path.rstrip("/") + "/" + name if path != "/" else "/" + name

#         # Directory: treat as a package if it has __init__.py or __init__.mpy
#         if typ == 0x4000:
#             pkg = False
#             try:
#                 child_names = {e[0] for e in os.ilistdir(full)}
#                 if "__init__.py" in child_names or "__init__.mpy" in child_names:
#                     pkg = True
#             except OSError:
#                 pass

#             if pkg:
#                 modname = (prefix + "." + name) if prefix else name
#                 print("package ", modname)

#             # Recurse so nested packages also show up
#             next_prefix = (prefix + "." + name) if prefix else name
#             list_modules(full, next_prefix)

#         # File: show .py and .mpy as importable modules
#         else:
#             if name.endswith(".py") and name != "__init__.py":
#                 modname = name[:-3]
#                 print("module  ", (prefix + "." + modname) if prefix else modname)
#             elif name.endswith(".mpy") and name != "__init__.mpy":
#                 modname = name[:-4]
#                 print("module  ", (prefix + "." + modname) if prefix else modname)

# list_modules("/")