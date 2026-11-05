"""Generate the 1280x640 GitHub social preview.

Run from the repository root:

    python docs/assets/make-social-preview.py

Requires Pillow. The output is intentionally kept as a normal RGB PNG so it
can be uploaded to GitHub without any extra processing.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 640
S = 3
OUT = Path(__file__).with_name("social-preview.png")

LATO_BLACK = "/usr/share/fonts/truetype/lato/Lato-Black.ttf"
LATO_BOLD = "/usr/share/fonts/truetype/lato/Lato-Bold.ttf"
LATO_SEMIBOLD = "/usr/share/fonts/truetype/lato/Lato-Semibold.ttf"
LATO_REGULAR = "/usr/share/fonts/truetype/lato/Lato-Regular.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

BG = (10, 15, 28)
TEXT = (248, 250, 252)
MUTED = (167, 180, 201)
DIM = (111, 128, 153)
MINT = (99, 230, 180)
BLUE = (114, 157, 255)
PURPLE = (189, 147, 249)
PINK = (255, 121, 198)
YELLOW = (241, 250, 140)
RED = (255, 118, 117)
CARD = (13, 21, 38)
CARD_HEADER = (17, 27, 46)
BORDER = (47, 75, 97)


def s(value: float) -> int:
    """Scale a design-space coordinate for supersampling."""
    return int(round(value * S))


def font(path: str, size: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, s(size))


def text_width(text: str, fnt: ImageFont.FreeTypeFont) -> float:
    return fnt.getlength(text) / S


def mix(fg: tuple[int, int, int], bg: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    """Opaque approximation of an alpha blend for direct RGB drawing."""
    return tuple(round(fg[c] * alpha + bg[c] * (1 - alpha)) for c in range(3))  # type: ignore[return-value]


def rounded(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float, float, float],
    radius: float,
    fill: tuple[int, int, int, int] | tuple[int, int, int] | None = None,
    outline: tuple[int, int, int, int] | tuple[int, int, int] | None = None,
    width: float = 1,
) -> None:
    x1, y1, x2, y2 = (s(v) for v in xy)
    draw.rounded_rectangle(
        (x1, y1, x2, y2),
        radius=s(radius),
        fill=fill,
        outline=outline,
        width=max(1, s(width)),
    )


def shield(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    w: float,
    h: float,
    fill: tuple[int, ...],
) -> None:
    points = [
        (x + w * 0.50, y),
        (x + w * 0.88, y + h * 0.14),
        (x + w * 0.83, y + h * 0.55),
        (x + w * 0.50, y + h * 0.98),
        (x + w * 0.17, y + h * 0.55),
        (x + w * 0.12, y + h * 0.14),
    ]
    draw.polygon([(s(px), s(py)) for px, py in points], fill=fill)
    # Keyhole cutout.
    cx, cy = s(x + w * 0.50), s(y + h * 0.42)
    r = s(w * 0.13)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BG)
    draw.polygon(
        [
            (cx - s(w * 0.055), cy + s(h * 0.02)),
            (cx + s(w * 0.055), cy + s(h * 0.02)),
            (cx + s(w * 0.085), cy + s(h * 0.25)),
            (cx - s(w * 0.085), cy + s(h * 0.25)),
        ],
        fill=BG,
    )


def tracked_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    tracking: float = 0,
) -> None:
    x, y = xy
    for char in text:
        draw.text((s(x), s(y)), char, font=fnt, fill=fill)
        x += fnt.getlength(char) / S + tracking


def pill(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    label: str,
    color: tuple[int, int, int],
    fnt: ImageFont.FreeTypeFont,
    *,
    tracking: float = 0.5,
    dot: bool = True,
) -> float:
    pad_x = 13.0
    gap = 7.0 if dot else 0.0
    text_w = sum(fnt.getlength(c) / S + tracking for c in label)
    h = 31.0
    w = pad_x * 2 + (5.0 + gap if dot else 0) + text_w
    rounded(
        draw,
        (x, y, x + w, y + h),
        15.5,
        fill=mix(color, BG, 0.13),
        outline=mix(color, BG, 0.62),
        width=1,
    )
    tx = x + pad_x + (5.0 + gap if dot else 0)
    if dot:
        draw.ellipse((s(x + pad_x), s(y + 13), s(x + pad_x + 5), s(y + 18)), fill=color)
    tracked_text(draw, (tx, y + 7.5), label, fnt, color, tracking)
    return w


def build() -> Image.Image:
    # Vertical background gradient.
    gradient = Image.new("RGB", (1, s(H)))
    top, bottom = (12, 18, 35), (8, 12, 23)
    for i in range(s(H)):
        t = i / max(1, s(H) - 1)
        gradient.putpixel(
            (0, i),
            tuple(round(top[c] * (1 - t) + bottom[c] * t) for c in range(3)),
        )
    img = gradient.resize((s(W), s(H))).convert("RGBA")

    # Soft colour glows.
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for cx, cy, radius, color in [
        (30, 20, 470, (*MINT, 42)),
        (1210, 610, 430, (*BLUE, 36)),
        (920, 50, 280, (*PURPLE, 25)),
    ]:
        gd.ellipse(
            (s(cx - radius), s(cy - radius), s(cx + radius), s(cy + radius)),
            fill=color,
        )
    glow = glow.filter(ImageFilter.GaussianBlur(s(125)))
    img = Image.alpha_composite(img, glow)

    # Very subtle grid.
    grid = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    for x in range(0, W + 1, 64):
        gd.line((s(x), 0, s(x), s(H)), fill=(255, 255, 255, 5), width=1)
    for y in range(0, H + 1, 64):
        gd.line((0, s(y), s(W), s(y)), fill=(255, 255, 255, 5), width=1)
    img = Image.alpha_composite(img, grid)

    draw = ImageDraw.Draw(img)

    # ---- Left: identity -------------------------------------------------
    label_font = font(LATO_BOLD, 13.5)
    x = 76.0
    h_pill = 34.0
    label = "PRIVACY-FIRST PASSWORD AUDIT"
    label_w = sum(label_font.getlength(c) / S + 0.8 for c in label)
    pill_w = 16 + 17 + 10 + label_w + 17
    rounded(
        draw,
        (x, 52, x + pill_w, 52 + h_pill),
        17,
        fill=mix(MINT, BG, 0.13),
        outline=mix(MINT, BG, 0.62),
        width=1,
    )
    shield(draw, x + 16, 59, 16, 20, MINT)
    tracked_text(draw, (x + 43, 60.5), label, label_font, MINT, 0.8)

    title_font = font(LATO_BLACK, 92)
    tx, ty = x, 102
    for part, color in (("IsMy", TEXT), ("Pwd", MINT), ("Safe", TEXT)):
        draw.text((s(tx), s(ty)), part, font=title_font, fill=color)
        tx += text_width(part, title_font)

    tagline_font = font(LATO_BOLD, 35)
    draw.text((s(x), s(220)), "zxcvbn, but readable.", font=tagline_font, fill=MINT)

    desc_font = font(LATO_REGULAR, 23)
    draw.text(
        (s(x), s(281)),
        "Audit password strength and HIBP breaches in your",
        font=desc_font,
        fill=MUTED,
    )
    draw.text(
        (s(x), s(312)),
        "CLI, CI and GitHub Actions \u2014 without exposing secrets.",
        font=desc_font,
        fill=MUTED,
    )

    # Install command.
    command_font = font(MONO, 21)
    box_y = 374.0
    rounded(
        draw,
        (x, box_y, x + 438, box_y + 62),
        14,
        fill=CARD,
        outline=mix(MINT, CARD, 0.7),
        width=1,
    )
    draw.text((s(x + 22), s(box_y + 17)), "$", font=command_font, fill=MINT)
    draw.text((s(x + 47), s(box_y + 17)), "pipx install ismypwdsafe", font=command_font, fill=TEXT)
    small = font(LATO_SEMIBOLD, 12)
    draw.text((s(x + 397), s(box_y + 24)), "PyPI", font=small, fill=(*MINT, 190))

    # Trust pills.
    tag_font = font(LATO_BOLD, 13.5)
    px, py = x, 466
    for label, color in (
        ("VALUES-FREE OUTPUT", MINT),
        ("HIBP ON BY DEFAULT", BLUE),
        ("GITHUB ACTION", PURPLE),
    ):
        px += pill(draw, px, py, label, color, tag_font) + 11

    # Footer.
    footer_font = font(MONO, 14)
    draw.text((s(x), s(583)), "github.com/Roma476/IsMyPwdSafe", font=footer_font, fill=DIM)
    sep = "  \u00b7  "
    pypi_x = x + text_width("github.com/Roma476/IsMyPwdSafe", footer_font)
    pypi_x += text_width(sep, footer_font)
    draw.text(
        (s(pypi_x), s(583)),
        "pypi.org/project/ismypwdsafe",
        font=footer_font,
        fill=DIM,
    )
    lic_x = 1204 - text_width("MIT licensed", footer_font)
    draw.text((s(lic_x), s(583)), "MIT licensed", font=footer_font, fill=DIM)

    # ---- Right: terminal ------------------------------------------------
    card_x, card_y, card_w, card_h = 692.0, 82.0, 512.0, 470.0
    # Shadow / glow.
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        (s(card_x), s(card_y + 14), s(card_x + card_w), s(card_y + card_h + 14)),
        radius=s(18),
        fill=(0, 0, 0, 150),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(s(22)))
    img.alpha_composite(shadow)
    draw = ImageDraw.Draw(img)

    rounded(
        draw,
        (card_x, card_y, card_x + card_w, card_y + card_h),
        18,
        fill=CARD,
        outline=mix(MINT, CARD, 0.5),
        width=1.4,
    )
    # Header bar: rounded top, square bottom.
    rounded(draw, (card_x, card_y, card_x + card_w, card_y + 52), 18, fill=CARD_HEADER)
    draw.rectangle(
        (s(card_x), s(card_y + 30), s(card_x + card_w), s(card_y + 52)),
        fill=CARD_HEADER,
    )
    draw.line(
        (s(card_x), s(card_y + 52), s(card_x + card_w), s(card_y + 52)),
        fill=mix(BORDER, CARD, 0.6),
        width=1,
    )
    for i, color in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        cx = card_x + 26 + i * 18
        draw.ellipse((s(cx), s(card_y + 20), s(cx + 11), s(card_y + 31)), fill=color)

    ui_font = font(LATO_SEMIBOLD, 13)
    draw.text((s(card_x + 82), s(card_y + 18)), "imps scan", font=ui_font, fill=MUTED)
    draw.text((s(card_x + card_w - 62), s(card_y + 18)), "2.1.0", font=font(MONO, 12), fill=DIM)

    mono = font(MONO, 17)
    small_mono = font(MONO, 14)
    tiny_mono = font(MONO, 13)
    left = card_x + 28
    y = card_y + 86

    draw.text((s(left), s(y)), "$", font=mono, fill=MINT)
    draw.text((s(left + 18), s(y)), "imps scan", font=mono, fill=TEXT)
    y += 46

    # Finding rows: status, location, key, result.
    rows = [
        ("\u2713", MINT, ".env:12", 30, "DB_PASSWORD", 122, "92/100", MINT),
        ("!", YELLOW, ".env:18", 30, "API_KEY", 122, "no score", YELLOW),
        ("\u2715", RED, ".env:24", 30, "PRIVATE_KEY", 122, "CRITICAL", RED),
    ]
    for status, status_color, loc, loc_x, key, key_x, result, result_color in rows:
        draw.text((s(left), s(y)), status, font=mono, fill=status_color)
        draw.text((s(left + loc_x), s(y)), loc, font=mono, fill=DIM)
        draw.text((s(left + key_x), s(y)), key, font=mono, fill=TEXT)
        draw.text((s(left + 262), s(y)), result, font=mono, fill=result_color)
        y += 34

    y += 6
    draw.line((s(left), s(y), s(card_x + card_w - 28), s(y)), fill=mix(BORDER, CARD, 0.55), width=1)
    y += 24
    draw.text((s(left), s(y)), "Scan: 3 files \u00b7 14 values", font=small_mono, fill=MUTED)
    y += 26
    draw.text((s(left), s(y)), "1 weak \u00b7 1 critical \u00b7 exit 6", font=small_mono, fill=TEXT)
    y += 26
    draw.text((s(left), s(y)), "HIBP checked 2 values \u00b7 0 pwned", font=tiny_mono, fill=DIM)
    y += 42

    # Bottom emphasis: the privacy promise.
    rounded(
        draw,
        (left, y, card_x + card_w - 28, y + 38),
        9,
        fill=mix(MINT, CARD, 0.1),
        outline=mix(MINT, CARD, 0.55),
        width=1,
    )
    draw.text(
        (s(left + 13), s(y + 10)),
        "No values printed, stored, or logged.",
        font=tiny_mono,
        fill=MINT,
    )

    # Corner accent: a faint shield watermark.
    watermark = Image.new("RGBA", img.size, (0, 0, 0, 0))
    wd = ImageDraw.Draw(watermark)
    shield(wd, 1135, 480, 110, 135, (*MINT, 18))
    img.alpha_composite(watermark)

    return img.convert("RGB").resize((W, H), Image.Resampling.LANCZOS)


if __name__ == "__main__":
    image = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT, format="PNG", optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {image.width}x{image.height})")
