"""
share_card.py — рендер карточки-результата мини-игры «Выше/Ниже» для шеринга.

Композиция «дуэль сверху»: два портрета финального раунда лицом к лицу, ниже —
число серии + режим, в подвале вордмарк и call-to-action. Тёмный фон и токены
один-в-один с аппом (Linear-точность, без слопа).

Производительность: портреты героев тянутся с CDN ОДИН раз и кладутся в
локальный дисковый кэш (assets/hero_portraits/<slug>.png); сама карточка
кэшируется по полному набору параметров (assets/share_cache/<hash>.png).
Рендерим только при нажатии «Поделиться» — Pillow, без браузеров.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_FONTS = _ROOT / "assets" / "fonts"
_PORTRAITS = _ROOT / "assets" / "hero_portraits"
_CACHE = _ROOT / "assets" / "share_cache"
_AVATAR = _ROOT / "d2helper.jpg"      # аватарка бота (брендинг в подвале карточки)
_CDN = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/{slug}.png"

# Токены аппа (styles.css :root) — карточка обязана совпадать по цвету.
_BG = (10, 10, 15)            # --bg-base   #0a0a0f
_SURFACE = (25, 25, 30)       # --bg-elevated #19191e
_BORDER = (42, 42, 48)        # ~rgba(255,255,255,0.08) на тёмном
_TEXT = (237, 237, 240)       # --text-primary
_TEXT2 = (139, 139, 149)      # --text-secondary
_TEXT3 = (86, 86, 95)         # --text-tertiary
_ACCENT = (107, 125, 179)     # --accent #6b7db3

_W, _H = 1200, 630

# Режим как существительное-ярлык (в тон вкладкам лидерборда).
_MODE_LABEL = {
    "pop": "Популярность",
    "kills": "Убийства",
    "deaths": "Смерти",
}

# Accent-тинт для чипа режима (color-mix вручную: accent над bg-base).
_CHIP_BG = (24, 26, 38)       # accent ~14% над фоном
_CHIP_BORDER = (49, 56, 81)   # accent ~40% над фоном


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(_FONTS / name), size)


def _portrait(slug: str) -> Image.Image | None:
    """Портрет героя 256×144: локальный кэш, при промахе — один fetch с CDN."""
    safe = "".join(c for c in slug if c.isalnum() or c in "_-")
    if not safe:
        return None
    path = _PORTRAITS / f"{safe}.png"
    if not path.exists():
        try:
            _PORTRAITS.mkdir(parents=True, exist_ok=True)
            r = httpx.get(_CDN.format(slug=safe), timeout=10.0, follow_redirects=True)
            r.raise_for_status()
            path.write_bytes(r.content)
        except Exception as e:
            logger.warning("[share_card] portrait fetch failed for %s: %s", safe, e)
            return None
    try:
        return Image.open(path).convert("RGBA")
    except Exception as e:
        logger.warning("[share_card] portrait open failed for %s: %s", safe, e)
        return None


def _rounded(img: Image.Image, radius: int) -> Image.Image:
    """Скругляет углы изображения через альфа-маску."""
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.size[0], img.size[1]], radius, fill=255)
    out = img.copy()
    out.putalpha(mask)
    return out


def _avatar(size: int) -> Image.Image | None:
    """Аватарка бота — квадрат со скруглением (как в шапке Telegram-чата)."""
    if not _AVATAR.exists():
        return None
    try:
        a = Image.open(_AVATAR).convert("RGBA")
        # центральный квадратный кроп → ресайз → скругление
        w, h = a.size
        s = min(w, h)
        a = a.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2)).resize((size, size))
        return _rounded(a, size // 4)
    except Exception as e:
        logger.warning("[share_card] avatar load failed: %s", e)
        return None


def _text_tracked(draw, xy, text, font, fill, tracking=0):
    """Текст с межбуквенным интервалом (Pillow его нативно не умеет)."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


def _cache_key(mode: str, streak: int, heroes) -> str:
    raw = f"{mode}|{streak}|" + "|".join(f"{s}:{n}" for s, n in heroes)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def render_share_card(mode: str, streak: int, heroes: list[tuple[str, str]]) -> bytes:
    """Рендерит PNG-карточку результата. heroes = [(slug, display_name), …] (2 шт)."""
    key = _cache_key(mode, streak, heroes)
    cached = _CACHE / f"{key}.png"
    if cached.exists():
        try:
            return cached.read_bytes()
        except Exception:
            pass

    img = Image.new("RGB", (_W, _H), _BG)
    d = ImageDraw.Draw(img)

    M = 80                                    # единое левое поле для всех блоков
    f_num = _font("GeistMono-Bold.ttf", 116)
    f_chip = _font("Geist-SemiBold.ttf", 30)
    f_name = _font("Geist-Medium.ttf", 30)
    f_vs = _font("GeistMono-Bold.ttf", 32)
    f_label = _font("Geist-SemiBold.ttf", 22)
    f_brand = _font("Geist-SemiBold.ttf", 28)

    # ── Дуэль сверху: два портрета 16:9 лицом к лицу ──
    pw, ph = 384, 216
    gap = 120
    x0 = (_W - (pw * 2 + gap)) // 2
    y0 = 52
    xs = [x0, x0 + pw + gap]
    for i, (slug, name) in enumerate(heroes[:2]):
        px = xs[i]
        d.rounded_rectangle([px, y0, px + pw, y0 + ph], 16, fill=_SURFACE, outline=_BORDER, width=1)
        p = _portrait(slug)
        if p is not None:
            tile = _rounded(p.resize((pw, ph)), 16)
            img.paste(tile, (px, y0), tile)
        # имя под портретом — якорь «сверху-по-центру» (ma)
        d.text((px + pw / 2, y0 + ph + 16), name, font=f_name, fill=_TEXT, anchor="ma")

    # «VS» — якорь «по центру» (mm), ровно между портретами по их центру
    d.text((_W / 2, y0 + ph / 2), "VS", font=f_vs, fill=_ACCENT, anchor="mm")

    # ── Разделитель ──
    dy = 348
    d.line([M, dy, _W - M, dy], fill=_BORDER, width=1)

    # ── Серия: метка → крупное число + чип режима ──
    _text_tracked(d, (M, dy + 26), "СЕРИЯ", f_label, _TEXT3, tracking=4)
    base = dy + 152                           # базовая линия числа
    num = str(streak)
    d.text((M, base), num, font=f_num, fill=_ACCENT, anchor="ls")
    num_w = d.textlength(num, font=f_num)
    # Чип режима — accent-тинт, по оптическому центру числа (≈ base-42).
    chip_txt = _MODE_LABEL.get(mode, "")
    tw = d.textlength(chip_txt, font=f_chip)
    pad_x, chip_h = 20, 56
    chip_w = tw + pad_x * 2
    chip_x = M + num_w + 28
    chip_cy = base - 42
    d.rounded_rectangle(
        [chip_x, chip_cy - chip_h / 2, chip_x + chip_w, chip_cy + chip_h / 2],
        14, fill=_CHIP_BG, outline=_CHIP_BORDER, width=1,
    )
    d.text((chip_x + chip_w / 2, chip_cy), chip_txt, font=f_chip, fill=_ACCENT, anchor="mm")

    # ── Подвал: аватарка бота + название, ВНИЗУ-СПРАВА ──
    av_sz = 52
    av_y = _H - av_sz - 34
    av = _avatar(av_sz)
    name = "D2Helper"
    name_w = d.textlength(name, font=f_brand)
    group_w = (av_sz + 14 if av is not None else 0) + name_w
    gx = _W - M - group_w
    if av is not None:
        img.paste(av, (int(gx), av_y), av)
        gx += av_sz + 14
    d.text((gx, av_y + av_sz / 2), name, font=f_brand, fill=_TEXT, anchor="lm")

    out = img
    try:
        _CACHE.mkdir(parents=True, exist_ok=True)
        out.save(cached, "PNG")
        from io import BytesIO
        buf = BytesIO(); out.save(buf, "PNG")
        return buf.getvalue()
    except Exception:
        from io import BytesIO
        buf = BytesIO(); out.save(buf, "PNG")
        return buf.getvalue()


if __name__ == "__main__":
    data = render_share_card("kills", 23, [("pudge", "Pudge"), ("tinker", "Tinker")])
    (_ROOT / "assets" / "_sample_card.png").write_bytes(data)
    print("wrote assets/_sample_card.png", len(data), "bytes")
