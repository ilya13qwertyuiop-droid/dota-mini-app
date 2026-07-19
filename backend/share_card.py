"""
share_card.py — рендер карточки-результата мини-игры «Выше/Ниже» для шеринга.

Композиция «дуэль сверху»: два портрета финального раунда лицом к лицу, ниже —
число серии + режим, в подвале вордмарк и call-to-action. Тёмный фон и токены
один-в-один с аппом (Linear-точность, без слопа).

Производительность: портреты героев тянутся с CDN ОДИН раз и кладутся в
локальный дисковый кэш (assets/hero_portraits/<slug>.webp); сама карточка
кэшируется по полному набору параметров (assets/share_cache/<hash>.png).
Рендерим только при нажатии «Поделиться» — Pillow, без браузеров.
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from backend.hero_portraits import get_hero_portrait_path

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_FONTS = _ROOT / "assets" / "fonts"
_CACHE = _ROOT / "assets" / "share_cache"
_AVATAR = _ROOT / "d2helper.jpg"      # аватарка бота (брендинг в подвале карточки)

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
    """Return a portrait from the shared validated, allowlisted cache."""
    path = get_hero_portrait_path(slug)
    if path is None:
        return None
    try:
        with Image.open(path) as portrait:
            return portrait.convert("RGBA")
    except Exception as e:
        logger.warning("[share_card] portrait open failed for %s: %s", slug, e)
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
    raw = f"{mode}|{streak}|" + "|".join(f"{s}:{n}:{v}" for s, n, v in heroes)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _fmt_value(mode: str, v) -> tuple[str, str]:
    """(значение, единица) под героем. pop → «142 350» «матчей»;
    kills/deaths → «7,3» «за игру». Узкий пробел между тысячами."""
    if v is None:
        return ("—", "")
    try:
        v = float(v)
    except (TypeError, ValueError):
        return ("—", "")
    if mode == "pop":
        return (f"{int(round(v)):,}".replace(",", " "), "матчей")
    return (f"{v:.1f}".replace(".", ","), "за игру")


def render_share_card(mode: str, streak: int, heroes: list[tuple]) -> bytes:
    """Рендерит JPEG-карточку результата.
    heroes = [(slug, display_name, value), …] (2 шт), value — метрика героя
    (число матчей / среднее за игру) для подписи под портретом."""
    # JPEG, а не PNG: Telegram InlineQueryResultPhoto принимает только JPEG —
    # PNG отдаётся браузеру нормально, но при отправке inline-фото отклоняется.
    key = _cache_key(mode, streak, heroes)
    cached = _CACHE / f"{key}.jpg"
    if cached.exists():
        try:
            return cached.read_bytes()
        except Exception:
            pass

    img = Image.new("RGB", (_W, _H), _BG)
    d = ImageDraw.Draw(img)

    M = 64
    f_brand = _font("Geist-SemiBold.ttf", 27)
    f_chip = _font("Geist-SemiBold.ttf", 26)
    f_name = _font("Geist-Medium.ttf", 30)
    f_val = _font("GeistMono-Bold.ttf", 33)
    f_unit = _font("Geist-Regular.ttf", 22)
    f_vs = _font("GeistMono-Bold.ttf", 26)
    f_slabel = _font("Geist-SemiBold.ttf", 22)
    f_streak = _font("GeistMono-Bold.ttf", 88)

    # ── Шапка: бренд слева, режим-чип справа, разделитель ──
    av_sz = 44
    hx, hy = M, 40
    av = _avatar(av_sz)
    if av is not None:
        img.paste(av, (hx, hy), av)
        hx += av_sz + 12
    d.text((hx, hy + av_sz / 2), "D2Helper", font=f_brand, fill=_TEXT, anchor="lm")

    chip_txt = _MODE_LABEL.get(mode, "")
    ctw = d.textlength(chip_txt, font=f_chip)
    cpad, chh = 18, 44
    cw = ctw + cpad * 2
    cx1 = _W - M - cw
    ccy = hy + av_sz / 2
    d.rounded_rectangle([cx1, ccy - chh / 2, cx1 + cw, ccy + chh / 2], 12,
                        fill=_CHIP_BG, outline=_CHIP_BORDER, width=1)
    d.text((cx1 + cw / 2, ccy), chip_txt, font=f_chip, fill=_ACCENT, anchor="mm")

    d.line([M, 108, _W - M, 108], fill=_BORDER, width=1)

    # ── Дуэль с числами: портрет + имя + значение метрики у каждого героя ──
    pw, ph = 372, 209                          # 16:9
    gap = 150
    x0 = (_W - (pw * 2 + gap)) // 2
    y0 = 144
    xs = [x0, x0 + pw + gap]
    for i, hero in enumerate(heroes[:2]):
        slug, name, value = hero
        px = xs[i]
        cx = px + pw / 2
        d.rounded_rectangle([px, y0, px + pw, y0 + ph], 16, fill=_SURFACE, outline=_BORDER, width=1)
        p = _portrait(slug)
        if p is not None:
            tile = _rounded(p.resize((pw, ph)), 16)
            img.paste(tile, (px, y0), tile)
        d.text((cx, y0 + ph + 16), name, font=f_name, fill=_TEXT, anchor="ma")
        # значение метрики + единица на одной базовой линии, по центру тайла
        val_s, unit = _fmt_value(mode, value)
        unit_s = (" " + unit) if unit else ""
        numw = d.textlength(val_s, font=f_val)
        uw = d.textlength(unit_s, font=f_unit) if unit_s else 0
        gxx = cx - (numw + uw) / 2
        vbase = y0 + ph + 16 + 70
        d.text((gxx, vbase), val_s, font=f_val, fill=_ACCENT, anchor="ls")
        if unit_s:
            d.text((gxx + numw, vbase), unit_s, font=f_unit, fill=_TEXT2, anchor="ls")

    # «VS» по центру между портретами — тихо (secondary), не конкурирует с числами
    d.text((_W / 2, y0 + ph / 2), "VS", font=f_vs, fill=_TEXT2, anchor="mm")

    # ── Итог: серия по центру снизу (кульминация) ──
    label = "СЕРИЯ ПОДРЯД"
    tr = 3
    lw = sum(d.textlength(ch, font=f_slabel) + tr for ch in label) - tr
    _text_tracked(d, (_W / 2 - lw / 2, 466), label, f_slabel, _TEXT3, tracking=tr)
    d.text((_W / 2, 500), str(streak), font=f_streak, fill=_ACCENT, anchor="ma")

    from io import BytesIO
    buf = BytesIO()
    # Гарантируем RGB (JPEG без альфы) — на случай, если режим где-то стал RGBA.
    (img if img.mode == "RGB" else img.convert("RGB")).save(
        buf, "JPEG", quality=90, optimize=True
    )
    data = buf.getvalue()
    try:
        _CACHE.mkdir(parents=True, exist_ok=True)
        # Атомарная запись: пишем во временный файл и переименовываем. Иначе
        # параллельный запрос (или фетчер Telegram) мог прочитать НАПОЛОВИНУ
        # записанный файл → обрезанный JPEG (нижняя половина серая на мобильном).
        fd, tmp = tempfile.mkstemp(dir=str(_CACHE), suffix=".tmp")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, cached)
    except Exception:
        pass
    return data


if __name__ == "__main__":
    data = render_share_card("kills", 23, [("pudge", "Pudge"), ("tinker", "Tinker")])
    (_ROOT / "assets" / "_sample_card.jpg").write_bytes(data)
    print("wrote assets/_sample_card.jpg", len(data), "bytes, magic:", data[:3])
