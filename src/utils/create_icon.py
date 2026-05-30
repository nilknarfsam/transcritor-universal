"""Gera assets/icon.png e assets/icon.ico para branding do CortexFlow."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 256
ICO_SIZES = (16, 32, 48, 64, 128, 256)

NAVY = (11, 29, 58)
TEAL = (20, 184, 166)
WHITE = (255, 255, 255)


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _blend(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (_lerp(c1[0], c2[0], t), _lerp(c1[1], c2[1], t), _lerp(c1[2], c2[2], t))


def _radial_gradient(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()
    cx = cy = size / 2.0
    max_r = size / 2.0
    for y in range(size):
        for x in range(size):
            dx = x - cx + 0.5
            dy = y - cy + 0.5
            dist = math.hypot(dx, dy)
            if dist > max_r:
                continue
            t = dist / max_r
            r, g, b = _blend(NAVY, TEAL, t ** 0.85)
            edge = max(0.0, min(1.0, (dist - max_r * 0.92) / (max_r * 0.08)))
            alpha = int(255 * (1.0 - edge * 0.15))
            pixels[x, y] = (r, g, b, alpha)
    return img


def _draw_mark(draw: ImageDraw.ImageDraw, size: int) -> None:
    cx = cy = size // 2
    # "C" estilizado (arco grosso)
    pad = size * 0.22
    draw.arc(
        (pad, pad, size - pad, size - pad),
        start=55,
        end=305,
        fill=WHITE,
        width=max(14, size // 14),
    )
    # Ondas de som/rádio no centro
    wave_cx = cx + size * 0.04
    for i, spread in enumerate((0.10, 0.16, 0.22)):
        r = size * spread
        draw.arc(
            (wave_cx - r, cy - r * 1.35, wave_cx + r, cy + r * 1.35),
            start=-55,
            end=55,
            fill=WHITE,
            width=max(3, size // 64 - i),
        )


def build_icon(size: int = SIZE) -> Image.Image:
    img = _radial_gradient(size).convert("RGBA")
    draw = ImageDraw.Draw(img)
    _draw_mark(draw, size)
    return img


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    master = build_icon(SIZE)
    png_path = assets / "icon.png"
    master.save(png_path, format="PNG")

    ico_path = assets / "icon.ico"
    master.save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
    )

    print(f"Gerado: {png_path}")
    print(f"Gerado: {ico_path} ({', '.join(str(s) for s in ICO_SIZES)}px)")


if __name__ == "__main__":
    main()
