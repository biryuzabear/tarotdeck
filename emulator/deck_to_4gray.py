"""Convert a deck of PNGs to the panel's 4-gray palette (0x00/0x80/0xC0/0xFF).

Usage: python3 deck_to_4gray.py <source_dir> <dest_dir>
Walks source_dir recursively, maps each pixel to its nearest of the four gray
levels (no dithering — flat pixel-art fills stay flat), and writes it to
dest_dir under the same relative path. Alpha is preserved as-is (thresholded
to fully opaque/transparent).
"""

import sys
from pathlib import Path

from PIL import Image

LEVELS = [0x00, 0x80, 0xC0, 0xFF]
_NEAREST = [min(LEVELS, key=lambda level: abs(level - v)) for v in range(256)]


def convert(src_path, dst_path):
    im = Image.open(src_path).convert("RGBA")
    out = im.convert("L").point(_NEAREST)

    alpha = im.split()[3].point(lambda a: 255 if a >= 128 else 0)

    merged = Image.merge("LA", (out, alpha))
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    merged.save(dst_path)


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    pngs = sorted(src.rglob("*.png"))
    for p in pngs:
        convert(p, dst / p.relative_to(src))
    print(f"{len(pngs)} cards converted -> {dst}")


if __name__ == "__main__":
    main()
