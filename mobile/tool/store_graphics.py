"""Builds the Google Play listing graphics from the app icon.

    python mobile/tool/store_graphics.py

Writes mobile/store/icon-512.png (hi-res icon) and mobile/store/feature-graphic.png (1024x500).
"""

import pathlib

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "store"
GREEN, GREEN_DARK, TOMATO, WHITE = (3, 174, 17), (21, 128, 61), (220, 38, 38), (255, 255, 255)


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    for name in (("arialbd.ttf", "segoeuib.ttf") if bold else ("arial.ttf", "segoeui.ttf")):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    icon = Image.open(ROOT / "assets/icon/app_icon.png").convert("RGB")
    icon.resize((512, 512), Image.LANCZOS).save(OUT / "icon-512.png")

    g = Image.new("RGB", (1024, 500), GREEN_DARK)
    d = ImageDraw.Draw(g)
    # Soft diagonal band in the brighter green, and the produce-label stripe along the bottom.
    d.polygon([(690, 0), (1024, 0), (1024, 500), (530, 500)], fill=GREEN)
    for x0, x1, c in ((0, 512, (22, 163, 74)), (512, 717, (234, 179, 8)), (717, 870, (234, 88, 12)), (870, 1024, TOMATO)):
        d.rectangle([x0, 488, x1, 500], fill=c)
    mask = Image.new("L", (300, 300), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 299, 299], radius=66, fill=255)
    g.paste(icon.resize((300, 300), Image.LANCZOS), (660, 90), mask)
    d.text((56, 112), "Food omniScan", font=font(70), fill=WHITE)
    d.text((58, 206), "Know what's inside.", font=font(40, bold=False), fill=WHITE)
    d.text((58, 262), "Scan any barcode or label: ingredients,", font=font(28, bold=False), fill=WHITE)
    d.text((58, 300), "allergens, recalls and smarter swaps.", font=font(28, bold=False), fill=WHITE)
    d.rounded_rectangle([58, 362, 330, 420], radius=29, fill=WHITE)
    d.text((86, 373), "Scan for free", font=font(30), fill=GREEN_DARK)
    g.save(OUT / "feature-graphic.png")
    print("wrote", OUT / "icon-512.png", "and", OUT / "feature-graphic.png")


if __name__ == "__main__":
    main()
