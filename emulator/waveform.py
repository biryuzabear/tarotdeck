"""Reads an SSD1677 LUT and says how long the refresh takes and what it looks like.

Layout, from the SSD1677 datasheet section 6.7: bytes 0-49 are VS[nX-LUTm], ten
groups of four phases packed two bits each, five LUTs; bytes 50-99 are
TP[nA..nD] and RP[n] per group; bytes 100-104 set the frame rate.
"""

FRAME_HZ = 25.0

HOLD, WHITE, BLACK, WHITE2 = 0, 1, 2, 3


def _phases(lut, group, plane=0):
    v = lut[plane * 10 + group]
    return [(v >> (6 - 2 * i)) & 0x3 for i in range(4)]


def parse(lut):
    if lut is None or len(lut) < 105:
        return 0.0, []
    steps = []
    frames = 0
    for group in range(10):
        tp = lut[50 + group * 5 : 55 + group * 5]
        durations, repeat = tp[:4], tp[4] + 1
        if not any(durations):
            continue
        frames += sum(durations) * repeat
        levels = _phases(lut, group)
        for _ in range(repeat):
            for level, span in zip(levels, durations):
                if span:
                    steps.append((level, span / FRAME_HZ))
    return frames / FRAME_HZ, steps


def _merge(steps):
    out = []
    for level, span in steps:
        if out and out[-1][0] == level:
            out[-1][1] += span
        else:
            out.append([level, span])
    return [(level, span) for level, span in out]


def flash(lut):
    """The inversions a viewer sees, minus the final settle where the image forms."""
    _, steps = parse(lut)
    visible = _merge([s for s in steps if s[0] in (WHITE, BLACK)])
    return visible[:-1] if len(visible) > 1 else []
