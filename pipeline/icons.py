#!/usr/bin/env python3
"""Make one 16x16 Yoto display icon per story from Noto Color Emoji, plus a cover.

Needs Pillow and the Noto Color Emoji font. Output: assets/icons/NN-slug.png,
assets/cover.png and build/icon-sheet.png (an enlarged contact sheet for review).
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
EMOJI = {
    1: "🌍", 2: "🌷", 3: "🐍", 4: "💔", 5: "🌈", 6: "🧱", 7: "✨", 8: "🍼", 9: "🐏", 10: "🥣",
    11: "🧥", 12: "🐄", 13: "🤝", 14: "🧺", 15: "🔥", 16: "🚪", 17: "🌊", 18: "🍞", 19: "📜", 20: "🎺",
    21: "🏺", 22: "🌾", 23: "👂", 24: "👑", 25: "🪨", 26: "🏛", 27: "⚡", 28: "💧", 29: "🐋", 30: "🌋",
    31: "🦁", 32: "👸", 33: "🕯", 34: "👼", 35: "👶", 36: "🎁", 37: "🕊", 38: "🎣", 39: "🏠", 40: "⛵",
    41: "🛏", 42: "🐟", 43: "👣", 44: "🩹", 45: "🐑", 46: "🏡", 47: "🌧", 48: "🧒", 49: "🌳", 50: "🙌",
    51: "🌿", 52: "🍷", 53: "✝", 54: "🌅", 55: "✋", 56: "☁", 57: "🌬", 58: "💥", 59: "⛓", 60: "🏞",
}


def glyph(ch, px=109):
    font = ImageFont.truetype(FONT, px)
    im = Image.new("RGBA", (px * 2, px * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((px // 2, px // 2), ch, font=font, embedded_color=True)
    box = im.getbbox()
    if box is None:
        raise SystemExit(f"font has no glyph for {ch!r}")
    im = im.crop(box)
    side = max(im.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    return sq


def icon(ch):
    small = glyph(ch).resize((16, 16), Image.LANCZOS)
    flat = Image.new("RGB", (16, 16), (0, 0, 0))
    flat.paste(small, mask=small.split()[3])
    flat = ImageEnhance.Color(flat).enhance(1.5)
    return ImageEnhance.Contrast(flat).enhance(1.2)


def main():
    stories = sorted((ROOT / "stories").glob("*.md"))
    out = ROOT / "assets" / "icons"
    out.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (10 * 110 + 10, 6 * 110 + 10), (40, 40, 40))
    for path in stories:
        n = int(path.stem[:2])
        ic = icon(EMOJI[n])
        ic.save(out / f"{path.stem}.png")
        big = ic.resize((96, 96), Image.NEAREST)
        sheet.paste(big, (10 + (n - 1) % 10 * 110, 10 + (n - 1) // 10 * 110))
    (ROOT / "build").mkdir(exist_ok=True)
    sheet.save(ROOT / "build" / "icon-sheet.png")

    # Cover: portrait card art, 638 x 1011.
    W, H = 638, 1011
    cover = Image.new("RGB", (W, H), (22, 34, 68))
    d = ImageDraw.Draw(cover)
    bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    for text, size, y in [("Bible", 120, 90), ("Stories", 120, 220)]:
        f = ImageFont.truetype(bold, size)
        d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=(255, 221, 120))
    f = ImageFont.truetype(bold, 34)
    sub = "from creation to new creation"
    d.text(((W - d.textlength(sub, font=f)) / 2, 380), sub, font=f, fill=(235, 235, 245))
    picks = [1, 5, 15, 17, 24, 31, 29, 35, 40, 42, 45, 54]
    for i, n in enumerate(picks):
        g = glyph(EMOJI[n]).resize((120, 120), Image.LANCZOS)
        cover.paste(g, (64 + i % 3 * 195, 470 + i // 3 * 132), g)
    cover.save(ROOT / "assets" / "cover.png")
    print(len(stories), "icons written")


if __name__ == "__main__":
    main()
