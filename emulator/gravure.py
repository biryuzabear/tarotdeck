"""The gravure ornament, in the vocabulary of biryuzabear.github.io.

What the reference actually does, and what this reproduces:

- **One big sigil, open, not a web.** Outer circle, a second circle well inside
  it, an inscribed diamond with its two diagonals, and at the centre a star-cog
  ringed by bolt holes. Few elements, far apart.
- **Traces hug the frame.** Orthogonal runs in bundles of two or three, cornered
  at 45 degrees, terminating in a small ring via. They travel along the edges;
  they do not radiate from the sigil.
- **Depth by layer.** Background sigils and long runs sit a grey lighter than the
  foreground, which is what the reference gets from opacity.

Two rules keep it legible on glass rather than a browser:

- **Nothing thinner or closer than the panel can separate.** Radii are checked
  against each other, polygons are refused when an edge would fall below
  MIN_EDGE, dots have a floor. At 0.169 mm a pixel, closer than MIN_GAP is one
  smudge.
- **No antialiasing.** Drawn at final size with one-pixel strokes. A resampled
  line lands as mid-grey on a four-level panel, which is the mush this replaces.
"""

import math

from PIL import Image, ImageDraw

PAPER = 0xFF
FAINT = 0xC0
ORNAMENT = 0x80
INK = 0x00

MIN_GAP = 7
MIN_EDGE = 12
MIN_DOT = 2


def rng(seed):
    state = seed & 0xFFFFFFFF

    def next_float():
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        t = state
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t ^ (t + ((t ^ (t >> 7)) * (t | 61) & 0xFFFFFFFF))) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return next_float


def _poly(rad, sides, rot_deg=0.0):
    rot = math.radians(rot_deg)
    return [
        (rad * math.cos(2 * math.pi * k / sides + rot), rad * math.sin(2 * math.pi * k / sides + rot))
        for k in range(sides)
    ]


def _star(outer, inner, points, rot_deg=0.0):
    rot = math.radians(rot_deg)
    pts = []
    for k in range(points * 2):
        rad = outer if k % 2 == 0 else inner
        a = math.pi * k / points + rot
        pts.append((rad * math.cos(a), rad * math.sin(a)))
    return pts


def _max_sides(rad):
    if rad < MIN_EDGE:
        return 0
    return int(math.pi / math.asin(min(1.0, MIN_EDGE / (2 * rad))))


def sigil(radius, seed, hub=True):
    """Outer ring, inner ring, inscribed diamond with diagonals, star-cog core."""
    r = rng(seed)
    out = []

    if radius < MIN_GAP * 2:
        return [("circle", (0, 0), radius)]

    out.append(("circle", (0, 0), radius))

    ring = radius * (0.80 + r() * 0.06)
    if radius - ring >= MIN_GAP:
        out.append(("circle", (0, 0), ring))

    sides = 4 if r() < 0.6 else 6
    if _max_sides(radius) >= sides:
        pts = _poly(radius, sides, 90 if sides == 4 else 0)
        out.append(("poly", pts))
        for i in range(sides // 2):
            out.append(("line", pts[i], pts[i + sides // 2]))

    core = radius * (0.40 + r() * 0.08)
    if ring - core >= MIN_GAP * 1.5 and core >= MIN_EDGE:
        points = 5 + int(r() * 7)
        while points > 4 and 2 * math.pi * core / (points * 2) < MIN_EDGE * 0.55:
            points -= 1
        out.append(("poly", _star(core, core * 0.74, points, r() * 0.4)))

        bolt = core * 0.52
        if hub and bolt >= MIN_GAP and core - bolt >= MIN_GAP:
            out.append(("circle", (0, 0), bolt))
            dot = max(MIN_DOT, bolt * 0.20)
            hole = bolt * 0.60
            count = 5 + int(r() * 2)
            if 2 * math.pi * hole / count >= dot * 3.0:
                out.append(("circle", (0, 0), dot * 1.8))
                for k in range(count):
                    a = 2 * math.pi * k / count - math.pi / 2
                    out.append(("circle", (hole * math.cos(a), hole * math.sin(a)), dot))
    return out


def _bundle(prims, pts, lanes, spacing, via_r):
    for lane in range(lanes):
        off = (lane - (lanes - 1) / 2) * spacing
        shifted = []
        for i, (x, y) in enumerate(pts):
            prev, nxt = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
            dx, dy = nxt[0] - prev[0], nxt[1] - prev[1]
            n = math.hypot(dx, dy) or 1.0
            shifted.append((x - dy / n * off, y + dx / n * off))
        for a, b in zip(shifted, shifted[1:]):
            prims.append(("line", a, b))
        prims.append(("circle", shifted[-1], via_r))


def _run(x0, y0, x1, y1, jog):
    """Straight, one 45-degree corner, straight — the way a trace is routed."""
    d = min(abs(x1 - x0), abs(y1 - y0), jog)
    pts = [(x0, y0)]
    if abs(x1 - x0) > d:
        pts.append((x1 - math.copysign(d, x1 - x0), y0))
    pts.append((x1, y1 if abs(y1 - y0) <= d else y0 + math.copysign(d, y1 - y0)))
    if pts[-1] != (x1, y1):
        pts.append((x1, y1))
    return pts


def ornament(w, h, seed):
    """Returns an L image: FAINT background layer, ORNAMENT foreground."""
    img = Image.new("L", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    r = rng(seed)

    cx, cy = w * 0.5, h * 0.46
    core = min(w * 0.26, h * 0.38)
    via = max(MIN_DOT + 1, core * 0.06)
    lane_gap = max(MIN_GAP, via * 2.2)

    back = []
    for side in range(2):
        left = side == 0
        x = (0.05 + r() * 0.06) * w if left else (0.95 - r() * 0.06) * w
        if abs(x - cx) < core + lane_gap * 3:
            continue
        y_end = (0.24 + r() * 0.52) * h
        pts = _run(x, -lane_gap, x, y_end, core * 0.4)
        _bundle(back, pts, 2 + int(r() * 2), lane_gap, via)

    clear = core + lane_gap * 2
    for corner in range(4):
        left = corner % 2 == 0
        top = corner < 2
        y = (0.08 + r() * 0.08) * h if top else (0.92 - r() * 0.08) * h
        x_end = (0.07 + r() * 0.11) * w if left else (0.93 - r() * 0.11) * w
        drop = (12 + r() * 20) * (1 if top else -1)
        crosses = abs(y - cy) < clear or abs(y + drop - cy) < clear
        reaches = x_end > cx - clear if left else x_end < cx + clear
        if crosses and reaches:
            continue
        pts = _run(-lane_gap if left else w + lane_gap, y, x_end, y + drop, core * 0.5)
        _bundle(back, pts, 2 + int(r() * 2), lane_gap, via)

    small = []
    for i in range(2):
        a = math.pi * (0.25 + i * 0.9) + r() * 0.5
        rad = core * (0.30 + r() * 0.12)
        sx = cx + math.cos(a) * (core + rad + lane_gap * 4)
        sy = cy + math.sin(a) * (core + rad + lane_gap * 2) * 0.7
        if rad + 2 < sx < w - rad - 2 and rad + 2 < sy < h - rad - 2:
            small.append((sx, sy, rad))

    render(d, back, (0, 0), FAINT)
    for sx, sy, rad in small:
        render(d, sigil(rad, int(r() * 999999), hub=False), (sx, sy), FAINT)
    render(d, sigil(core, seed), (cx, cy), ORNAMENT)
    return img


def render(draw, prims, origin, ink=ORNAMENT, width=1):
    ox, oy = origin

    def box(c, rad):
        return [round(ox + c[0] - rad), round(oy + c[1] - rad), round(ox + c[0] + rad), round(oy + c[1] + rad)]

    for prim in prims:
        kind = prim[0]
        if kind == "circle":
            draw.ellipse(box(prim[1], prim[2]), outline=ink, width=width)
        elif kind == "line":
            (x1, y1), (x2, y2) = prim[1], prim[2]
            draw.line([round(ox + x1), round(oy + y1), round(ox + x2), round(oy + y2)], fill=ink, width=width)
        elif kind == "poly":
            pts = [(round(ox + x), round(oy + y)) for x, y in prim[1]]
            draw.line(pts + [pts[0]], fill=ink, width=width)
