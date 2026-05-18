from __future__ import annotations

from io import BytesIO
from pathlib import Path
import random
import re
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from config import SOCIAL_ASSETS_DIR

CARD_SIZE = (1080, 1080)

INK = (53, 41, 31, 255)
ACCENT = (171, 123, 72, 255)
PAPER = (252, 247, 238, 222)


def _font(
    size: int,
    serif: bool = True,
    italic: bool = False,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if serif:
        candidates = [
            Path("C:/Windows/Fonts/georgiai.ttf") if italic else Path("C:/Windows/Fonts/georgia.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf") if italic else Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf") if italic else Path("/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf"),
        ]
    else:
        candidates = [
            Path("C:/Windows/Fonts/segoeui.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
        ]

    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)

    return ImageFont.load_default()


def _clean_prompt_text(text: str, max_chars: int = 220) -> str:
    clean = re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 .,;:¿?¡!\-]", " ", text)
    clean = re.sub(r"\btazas?\b", "objeto cotidiano", clean, flags=re.IGNORECASE)
    clean = " ".join(clean.split())
    return clean[:max_chars].strip()


def build_background_image_url(texto: str, tema: str, publicacion_id: int | None = None) -> str:
    """Crea una URL corta y estable de Pollinations para usar como fondo editorial."""

    fragmento = _clean_prompt_text(texto, max_chars=150)
    prompt = (
        f"quiet editorial photograph inspired by {tema}, "
        f"{fragmento}, soft natural window light, muted earth tones, "
        "warm minimalism, subtle paper texture, emotional atmosphere, "
        "clean negative space for overlaid text, no cups, no mugs, "
        "no text, no logo, no typography, no detailed faces"
    )
    seed = publicacion_id or 1
    return (
        "https://image.pollinations.ai/prompt/"
        f"{quote(prompt, safe='')}?width=1080&height=1080&nologo=true&enhance=true&seed={seed}"
    )


def _fallback_background(seed: str = "") -> Image.Image:
    """Fondo visual de respaldo. No es plano: simula una imagen editorial suave."""

    width, height = CARD_SIZE
    rnd = random.Random(seed)

    palettes = [
        ((242, 229, 210), (145, 126, 108), (96, 75, 58)),
        ((235, 222, 204), (170, 143, 112), (75, 61, 49)),
        ((230, 218, 205), (121, 109, 98), (64, 53, 44)),
    ]
    start, mid, end = rnd.choice(palettes)

    image = Image.new("RGB", CARD_SIZE, start)
    draw = ImageDraw.Draw(image)

    for y in range(height):
        ratio = y / (height - 1)
        if ratio < 0.55:
            local = ratio / 0.55
            a, b = start, mid
        else:
            local = (ratio - 0.55) / 0.45
            a, b = mid, end
        r = int(a[0] * (1 - local) + b[0] * local)
        g = int(a[1] * (1 - local) + b[1] * local)
        b_val = int(a[2] * (1 - local) + b[2] * local)
        draw.line([(0, y), (width, y)], fill=(r, g, b_val))

    # Formas grandes y borrosas para que el fallback no sea un bloque plano.
    glow = Image.new("RGBA", CARD_SIZE, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    for _ in range(10):
        x = rnd.randint(-260, 900)
        y = rnd.randint(-240, 850)
        radius = rnd.randint(260, 680)
        color = rnd.choice(
            [
                (255, 246, 226, 72),
                (199, 156, 108, 50),
                (87, 65, 49, 42),
                (150, 127, 101, 44),
            ]
        )
        glow_draw.ellipse([x, y, x + radius, y + radius], fill=color)

    glow = glow.filter(ImageFilter.GaussianBlur(78))
    image = Image.alpha_composite(image.convert("RGBA"), glow).convert("RGB")

    # Grano sutil.
    noise = Image.new("L", CARD_SIZE)
    noise_data = [rnd.randint(0, 28) for _ in range(width * height)]
    noise.putdata(noise_data)
    noise_rgba = ImageOps.colorize(noise, black="#000000", white="#ffffff").convert("RGBA")
    noise_rgba.putalpha(18)

    return Image.alpha_composite(image.convert("RGBA"), noise_rgba).convert("RGB")


def _download_background(url: str | None, seed: str) -> Image.Image:
    if not url:
        return _fallback_background(seed)

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; EcosDelAlma/1.0)",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }

    for timeout in (25, 45):
        try:
            response = requests.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "image" not in content_type and not response.content.startswith((b"\xff\xd8", b"\x89PNG", b"RIFF")):
                continue
            image = Image.open(BytesIO(response.content)).convert("RGB")
            return ImageOps.fit(image, CARD_SIZE, method=Image.Resampling.LANCZOS)
        except Exception:
            continue

    return _fallback_background(seed)


def _make_background(url: str | None, seed: str) -> Image.Image:
    fondo = _download_background(url, seed)

    # El fondo se mantiene visible, pero tratado como fotografía editorial suave.
    fondo = ImageEnhance.Color(fondo).enhance(0.82)
    fondo = ImageEnhance.Contrast(fondo).enhance(0.92)
    fondo = ImageEnhance.Brightness(fondo).enhance(1.00)
    fondo = fondo.filter(ImageFilter.GaussianBlur(radius=3))

    wash = Image.new("RGBA", CARD_SIZE, (246, 235, 219, 52))

    vignette = Image.new("L", CARD_SIZE, 0)
    vdraw = ImageDraw.Draw(vignette)
    vdraw.ellipse([-320, -270, 1400, 1380], fill=220)
    vignette = vignette.filter(ImageFilter.GaussianBlur(100))

    dark = Image.new("RGBA", CARD_SIZE, (38, 28, 20, 82))
    dark.putalpha(ImageOps.invert(vignette))

    composed = Image.alpha_composite(fondo.convert("RGBA"), wash)
    composed = Image.alpha_composite(composed, dark)

    return composed


def _wrap_by_pixels(
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    draw: ImageDraw.ImageDraw,
) -> list[str]:
    lines: list[str] = []

    for paragraph in text.splitlines():
        paragraph = " ".join(paragraph.split())

        if not paragraph:
            continue

        current = ""

        for word in paragraph.split():
            candidate = f"{current} {word}".strip()

            if draw.textlength(candidate, font=font) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

    return lines


def _text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_height: int,
):
    clean = " ".join(text.split())

    for size in [39, 37, 35, 33, 31, 29, 27, 25, 23, 21]:
        font = _font(size, serif=True)
        line_height = int(size * 1.36)
        lines = _wrap_by_pixels(clean, font, max_width, draw)

        if len(lines) * line_height <= max_height:
            return font, lines, line_height

    font = _font(20, serif=True)
    line_height = int(20 * 1.32)
    return font, _wrap_by_pixels(clean, font, max_width, draw), line_height


def _rounded_shadow(
    size: tuple[int, int],
    radius: int,
    shadow: int = 36,
) -> Image.Image:
    width, height = size

    canvas = Image.new("RGBA", (width + shadow * 2, height + shadow * 2), (0, 0, 0, 0))

    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, width, height], radius=radius, fill=255)

    shadow_layer = Image.new("RGBA", canvas.size, (55, 38, 22, 0))

    shadow_mask = Image.new("L", canvas.size, 0)
    shadow_mask.paste(mask, (shadow, shadow))
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(shadow // 2))

    shadow_layer.putalpha(shadow_mask.point(lambda p: int(p * 0.18)))

    return shadow_layer


def generar_tarjeta_social(
    texto: str,
    tema: str,
    imagen_url: str | None,
    publicacion_id: int,
) -> str:
    """Genera una tarjeta editorial cuadrada y devuelve su ruta para Jekyll."""

    SOCIAL_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    if not imagen_url:
        imagen_url = build_background_image_url(texto, tema, publicacion_id)

    seed = f"{tema}-{publicacion_id}-{texto[:40]}"
    card = _make_background(imagen_url, seed)

    # Panel principal. Es un poco más alto para alojar el texto completo.
    panel_x, panel_y = 130, 135
    panel_w, panel_h = 820, 810

    shadow = _rounded_shadow((panel_w, panel_h), radius=42, shadow=42)
    card.alpha_composite(shadow, (panel_x - 42, panel_y - 30))

    panel = Image.new("RGBA", CARD_SIZE, (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(panel)
    pdraw.rounded_rectangle(
        [panel_x, panel_y, panel_x + panel_w, panel_y + panel_h],
        radius=42,
        fill=PAPER,
        outline=(255, 255, 255, 118),
        width=2,
    )

    card = Image.alpha_composite(card, panel)
    draw = ImageDraw.Draw(card)

    label_font = _font(23, serif=False)
    brand_font = _font(35, serif=True)

    content_x = panel_x + 72
    top_y = panel_y + 58

    label = tema.upper()
    draw.text((content_x, top_y), label, fill=ACCENT, font=label_font)
    draw.line(
        (content_x, top_y + 43, content_x + 98, top_y + 43),
        fill=(171, 123, 72, 160),
        width=2,
    )

    text_area_h = panel_h - 300
    body_font, lines, line_height = _text_block(
        draw,
        texto,
        max_width=panel_w - 144,
        max_height=text_area_h,
    )

    text_height = len(lines) * line_height
    text_area_y = panel_y + 168
    text_y = text_area_y + max(0, (text_area_h - text_height) // 2)

    for line in lines:
        draw.text((content_x, text_y), line, fill=INK, font=body_font)
        text_y += line_height

    brand = "Ecos del Alma"
    brand_w = draw.textlength(brand, font=brand_font)
    brand_y = panel_y + panel_h - 105
    draw.text(
        ((CARD_SIZE[0] - brand_w) / 2, brand_y),
        brand,
        fill=(93, 68, 45, 255),
        font=brand_font,
    )

    filename = f"escrito-{publicacion_id:04d}.png"
    output = SOCIAL_ASSETS_DIR / filename

    card.convert("RGB").save(output, format="PNG", optimize=True)

    return f"/assets/social/{filename}"
