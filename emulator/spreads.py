"""Where one, two or three cards sit on 280 x 480 of glass.

A tarot card is 1:1.714. Three of them side by side across 280 px leaves 78 px
each, which is 13 mm — a card the size of a fingernail. The screen is portrait and
tall, so the honest question is whether the cards must be wholly visible at once or
whether they may overlap the way a real spread on a table does.

Each function returns plates back-to-front: `(x, y, w, h)`, later ones drawn over
earlier ones.
"""

W, H = 280, 480
ASPECT = 1.714
MARGIN = 12


def _fit(width=None, height=None):
    if width is not None:
        return int(width), int(width * ASPECT)
    return int(height / ASPECT), int(height)


def row(count):
    """Side by side, whole, equal. Nothing hidden and nothing overlapping.

    The plain answer, and the weakest use of a tall screen: three across is bound
    by width alone, so two thirds of the glass is left empty above and below.
    """
    gap = 6
    width = (W - 2 * MARGIN - (count - 1) * gap) // count
    w, h = _fit(width=min(width, int((H - 2 * MARGIN) / ASPECT)))
    total = count * w + (count - 1) * gap
    x = (W - total) // 2
    y = (H - h) // 2
    return [(x + i * (w + gap), y, w, h) for i in range(count)]


def cascade(count):
    """Overlapped down and across, the way a hand is fanned on a table.

    Each card hides part of the one behind it, so all three can be half again as
    large as in a row. What stays visible of the buried cards is their left edge
    and their top — which, on these faces, is where the suit sign is not, so it
    trades size against recognising the lower cards at a glance.
    """
    if count == 1:
        return row(1)
    step_x, step_y = 46, 74
    w, h = _fit(width=(W - 2 * MARGIN - (count - 1) * step_x))
    while h + (count - 1) * step_y > H - 2 * MARGIN:
        w, h = _fit(width=w - 4)
    total_w = w + (count - 1) * step_x
    total_h = h + (count - 1) * step_y
    x = (W - total_w) // 2
    y = (H - total_h) // 2
    return [(x + i * step_x, y + i * step_y, w, h) for i in range(count)]


def ladder(count):
    """Stacked down the screen, each card overlapping the one above.

    Uses the height rather than the width, so the cards are the widest of any
    layout here. Only a band of each buried card shows, but that band is the top of
    the plate, where the card's number and the top of its figure are.
    """
    if count == 1:
        return row(1)
    step = 118
    w, h = _fit(width=W - 2 * MARGIN)
    while h + (count - 1) * step > H - 2 * MARGIN:
        w, h = _fit(width=w - 6)
    total = h + (count - 1) * step
    x = (W - w) // 2
    y = (H - total) // 2
    return [(x, y + i * step, w, h) for i in range(count)]


def hero(count):
    """One card large, the rest small beside it.

    For a spread whose positions are not equal — situation over action over
    outcome — and for the reveal, where the card being turned is the only one that
    matters at that moment.
    """
    if count == 1:
        return row(1)
    small_w, small_h = _fit(height=(H - 2 * MARGIN - (count - 2) * 8) // (count - 1))
    small_w = min(small_w, 74)
    small_h = int(small_w * ASPECT)
    big_w, big_h = _fit(width=W - 2 * MARGIN - small_w - 10)
    big_h = min(big_h, H - 2 * MARGIN)
    big_w = int(big_h / ASPECT)
    plates = []
    y = (H - ((count - 1) * small_h + (count - 2) * 8)) // 2
    for i in range(count - 1):
        plates.append((W - MARGIN - small_w, y + i * (small_h + 8), small_w, small_h))
    plates.append((MARGIN, (H - big_h) // 2, big_w, big_h))
    return plates


LAYOUTS = [("row", row), ("cascade", cascade), ("ladder", ladder), ("hero", hero)]
