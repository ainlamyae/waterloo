"""Generate the maple-leaf + location-pin logo mark (Waterloo gold & black).

All shapes are computed analytically (teardrop polygons) so the raster
(PNG, via Pillow) and vector (SVG, hand-emitted from the same point math)
versions match exactly.

Usage:
    python scripts/generate_logo.py
Writes into assets/: logo.svg, favicon.svg, favicon-32.png,
favicon-180.png, og-image.png
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

import arabic_reshaper
from bidi.algorithm import get_display


def shape_fa(text):
    return get_display(arabic_reshaper.reshape(text))

GOLD = (255, 199, 44, 255)
BLACK = (16, 16, 16, 255)
CREAM = (253, 250, 243, 255)

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")


def teardrop_polygon(cx, cy, r, theta, tip_len, arc_points=28):
    """A rounded 'pin/petal' shape: a circle of radius r centred at
    (cx, cy) merged with a triangular tip pointing along angle theta
    (image coords, y-down) at distance tip_len from the centre."""
    ux, uy = math.cos(theta), math.sin(theta)
    px, py = -uy, ux
    tip = (cx + ux * tip_len, cy + uy * tip_len)
    base_right = (cx + px * r, cy + py * r)
    base_left = (cx - px * r, cy - py * r)
    start_angle = theta + math.pi / 2
    pts = [tip, base_right]
    for i in range(1, arc_points):
        t = start_angle + math.pi * (i / arc_points)
        pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    pts.append(base_left)
    return pts


UP = -math.pi / 2
DOWN = math.pi / 2


def leaf_lobes(cx, cy, r, scale=1.0):
    """Five teardrop lobes fanned around (cx, cy), approximating a
    stylized maple leaf. Returns a list of polygons."""
    offsets_deg = [-58, -28, 0, 28, 58]
    lengths = [0.62, 0.82, 1.0, 0.82, 0.62]
    lobes = []
    for off, length in zip(offsets_deg, lengths):
        theta = UP + math.radians(off)
        lobes.append(teardrop_polygon(cx, cy, r * 0.42, theta, r * 2.35 * length * scale))
    return lobes


def build_mark(size):
    """Returns an RGBA image of the full pin+leaf mark at `size`x`size`."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pin_cx, pin_cy = size * 0.5, size * 0.40
    pin_r = size * 0.30

    # gold ring behind the black pin (uniform border)
    ring = teardrop_polygon(pin_cx, pin_cy, pin_r + size * 0.018, DOWN, pin_r * 1.72 + size * 0.018)
    draw.polygon(ring, fill=GOLD)

    pin = teardrop_polygon(pin_cx, pin_cy, pin_r, DOWN, pin_r * 1.72)
    draw.polygon(pin, fill=BLACK)

    for lobe in leaf_lobes(pin_cx, pin_cy - size * 0.02, pin_r * 0.62):
        draw.polygon(lobe, fill=GOLD)

    # small stem under the leaf
    stem_top = (pin_cx, pin_cy - size * 0.02 + pin_r * 0.20)
    stem_bottom = (pin_cx, pin_cy - size * 0.02 + pin_r * 0.62)
    draw.line([stem_top, stem_bottom], fill=GOLD, width=max(2, int(size * 0.022)))

    return img


def polygon_to_svg_points(pts, size, view=100):
    scale = view / size
    return " ".join(f"{x*scale:.2f},{y*scale:.2f}" for x, y in pts)


def build_svg(size=1000, view=100):
    pin_cx, pin_cy = size * 0.5, size * 0.40
    pin_r = size * 0.30
    ring = teardrop_polygon(pin_cx, pin_cy, pin_r + size * 0.018, DOWN, pin_r * 1.72 + size * 0.018)
    pin = teardrop_polygon(pin_cx, pin_cy, pin_r, DOWN, pin_r * 1.72)
    lobes = leaf_lobes(pin_cx, pin_cy - size * 0.02, pin_r * 0.62)
    stem_top = (pin_cx, pin_cy - size * 0.02 + pin_r * 0.20)
    stem_bottom = (pin_cx, pin_cy - size * 0.02 + pin_r * 0.62)
    s = view / size

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view} {view}">']
    parts.append(f'<polygon points="{polygon_to_svg_points(ring, size, view)}" fill="#ffc72c"/>')
    parts.append(f'<polygon points="{polygon_to_svg_points(pin, size, view)}" fill="#101010"/>')
    for lobe in lobes:
        parts.append(f'<polygon points="{polygon_to_svg_points(lobe, size, view)}" fill="#ffc72c"/>')
    parts.append(
        f'<line x1="{stem_top[0]*s:.2f}" y1="{stem_top[1]*s:.2f}" '
        f'x2="{stem_bottom[0]*s:.2f}" y2="{stem_bottom[1]*s:.2f}" '
        f'stroke="#ffc72c" stroke-width="{max(0.6, size*0.022*s):.2f}" stroke-linecap="round"/>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def build_og_image():
    W, H = 1200, 630
    img = Image.new("RGBA", (W, H), BLACK)
    mark_size = 340
    mark = build_mark(mark_size * 4).resize((mark_size, mark_size), Image.LANCZOS)
    img.alpha_composite(mark, (80, (H - mark_size) // 2))

    draw = ImageDraw.Draw(img)
    title = shape_fa("راهنمای تازه‌واردین به واترلو")
    subtitle = "Waterloo Newcomer Guide"

    font_path = None
    for candidate in (r"C:\Windows\Fonts\tahoma.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(candidate):
            font_path = candidate
            break

    text_right = W - 90
    max_width = W - 90 - 500

    title_size = 64
    while title_size > 24:
        title_font = ImageFont.truetype(font_path, title_size) if font_path else ImageFont.load_default()
        bbox = draw.textbbox((0, 0), title, font=title_font)
        if bbox[2] - bbox[0] <= max_width:
            break
        title_size -= 2

    sub_font = ImageFont.truetype(font_path, 28) if font_path else ImageFont.load_default()

    sub_bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    draw.text((text_right - (sub_bbox[2] - sub_bbox[0]), 255), subtitle, font=sub_font, fill=(255, 199, 44, 255))

    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    draw.text((text_right - (title_bbox[2] - title_bbox[0]), 305), title, font=title_font, fill=(255, 255, 255, 255))

    img.convert("RGB").save(os.path.join(ASSETS, "og-image.png"))


def main():
    os.makedirs(ASSETS, exist_ok=True)

    logo_svg = build_svg(size=1000, view=100)
    with open(os.path.join(ASSETS, "logo.svg"), "w", encoding="utf-8") as f:
        f.write(logo_svg)
    with open(os.path.join(ASSETS, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(logo_svg)

    hi_res = build_mark(1024)
    hi_res.resize((32, 32), Image.LANCZOS).save(os.path.join(ASSETS, "favicon-32.png"))
    hi_res.resize((180, 180), Image.LANCZOS).save(os.path.join(ASSETS, "favicon-180.png"))
    hi_res.resize((512, 512), Image.LANCZOS).save(os.path.join(ASSETS, "logo-512.png"))

    build_og_image()
    print("Logo assets written to", ASSETS)


if __name__ == "__main__":
    main()
