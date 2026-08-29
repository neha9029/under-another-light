"""
UNDER ANOTHER LIGHT -- composite
Same seed, same geometry, same spectra. Only the light changes.

Renders the piece under three illuminants and joins them side by side,
so the argument of the work is visible in a single image: the palette
was never in the artwork, it was in the room.

Run:  python composite.py
Out:  under_another_light_composite.png
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import under_another_light as art

# (illuminant, caption) -- tungsten lamp, daylight, north sky
PANELS = [
    (2856, "tungsten  2856 K"),
    ("D65", "daylight  D65"),
    (12000, "shade  12000 K"),
]
GUTTER = 40
CAPTION_HEIGHT = 90
BACKGROUND = (12, 12, 12)


def render_panel(light):
    """Full pipeline from under_another_light, rendered to a PIL image."""
    rng = np.random.default_rng(art.SEED)
    points, mesh = art.build_mesh(rng)
    centroids = points[mesh.simplices].mean(axis=1)

    spectra = art.reflectance_spectra(centroids, rng)
    spd = art.illuminant(light)

    xyz = art.spectra_to_xyz(spectra, spd)
    white = np.ones((1, len(art.WAVELENGTHS)))
    source_white = art.spectra_to_xyz(white, spd)[0]
    target_white = art.spectra_to_xyz(white, art.D65_SPD)[0]
    colours = art.xyz_to_srgb(art.adapt(xyz, source_white, target_white, art.ADAPTATION))

    polygons = points[mesh.simplices] * [art.WIDTH, art.HEIGHT]

    scale = art.SUPERSAMPLE
    canvas = Image.new("RGB", (art.WIDTH * scale, art.HEIGHT * scale), "black")
    brush = ImageDraw.Draw(canvas)
    for polygon, colour in zip(polygons, colours):
        brush.polygon([(x * scale, y * scale) for x, y in polygon], fill=tuple(colour))
    return canvas.resize((art.WIDTH, art.HEIGHT), Image.LANCZOS)


def caption_font(size):
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",              # macOS
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Debian/Ubuntu
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",           # Fedora
        "C:/Windows/Fonts/arial.ttf",                       # Windows
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    # Pillow >= 10.1: scalable built-in font, honours the requested size
    return ImageFont.load_default(size)


def main():
    panels = [(render_panel(light), caption) for light, caption in PANELS]

    total_width = art.WIDTH * len(panels) + GUTTER * (len(panels) + 1)
    total_height = art.HEIGHT + GUTTER + CAPTION_HEIGHT
    composite = Image.new("RGB", (total_width, total_height), BACKGROUND)
    brush = ImageDraw.Draw(composite)
    font = caption_font(38)

    for index, (panel, caption) in enumerate(panels):
        x = GUTTER + index * (art.WIDTH + GUTTER)
        composite.paste(panel, (x, GUTTER))
        anchor_x = x + art.WIDTH // 2
        anchor_y = art.HEIGHT + GUTTER + CAPTION_HEIGHT // 2
        brush.text((anchor_x, anchor_y), caption, fill=(180, 180, 180),
                   font=font, anchor="mm")

    composite.save("under_another_light_composite.png")
    print(f"under_another_light_composite.png  {total_width}x{total_height}")


if __name__ == "__main__":
    main()
