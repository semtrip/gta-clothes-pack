"""
Соглашения об именах как в открытом altClothTool / Durty Cloth (github.com/DurtyFree/durty-cloth-tool).

Там пол задаётся в UI при добавлении файла; у нас — из метаданных YDD + опционально из папок.
Текстуры ищутся по шаблонам ClothData.SearchForTextures / ClothNameResolver.DrawableTypeToString.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Имя компонента в drawable (parts[0]) -> префикс в имени .ytd (DrawableTypeToString)
_COMPONENT_DRAWABLE_TO_TEX_PREFIX: dict[str, str] = {
    "head": "head",
    "berd": "berd",
    "hair": "hair",
    "uppr": "uppr",
    "lowr": "lowr",
    "hand": "hand",
    "feet": "feet",
    "teef": "teef",
    "accs": "accs",
    "task": "task",
    "decl": "decl",
    "jbib": "jbib",
}

# parts[1] для p_* -> префикс текстуры (p_head, …)
_PROP_TO_TEX_PREFIX: dict[str, str] = {
    "head": "p_head",
    "eyes": "p_eyes",
    "ears": "p_ears",
    "mouth": "p_mouth",
    "lhand": "p_lhand",
    "rhand": "p_rhand",
    "lwrist": "p_lwrist",
    "rwrist": "p_rwrist",
    "hip": "p_hip",
    "lfoot": "p_lfoot",
    "rfoot": "p_rfoot",
    "unk1": "p_unk1",
    "unk2": "p_unk2",
}

# Префикс drawable -> (kind, slot_slug) под epic_cloth^… / epic_prop^… в rename_epic
_DURTY_PREFIX_TO_KIND_SLOT: dict[str, tuple[str, str]] = {
    "head": ("cloth", "accessories"),
    "berd": ("cloth", "masks"),
    "hair": ("cloth", "hair_styles"),
    "uppr": ("cloth", "tops"),
    "lowr": ("cloth", "legs"),
    "hand": ("cloth", "accessories"),
    "feet": ("cloth", "shoes"),
    "teef": ("cloth", "undershirts"),
    "accs": ("cloth", "accessories"),
    "task": ("cloth", "bags_and_parachutes"),
    "decl": ("cloth", "decals"),
    "jbib": ("cloth", "tops"),
    "p_head": ("prop", "hats"),
    "p_eyes": ("prop", "glasses"),
    "p_ears": ("prop", "ears"),
    "p_mouth": ("prop", "mouth"),
    "p_lhand": ("prop", "hands"),
    "p_rhand": ("prop", "hands"),
    "p_lwrist": ("prop", "watches"),
    "p_rwrist": ("prop", "watches"),
    "p_hip": ("prop", "legs"),
    "p_lfoot": ("prop", "shoes"),
    "p_rfoot": ("prop", "shoes"),
    "p_unk1": ("prop", "misc"),
    "p_unk2": ("prop", "misc"),
}


@dataclass(slots=True)
class DurtyParsed:
    """Результат разбора имени файла как в ClothNameResolver."""

    is_prop: bool
    drawable_key: str
    texture_prefix: str
    bind_number: str
    postfix: str = ""
    is_variation: bool = False


def stream_drawable_stem(stem: str) -> str:
    """
    Stream-имена GTA: `mp_f_freemode_01_mp_f_pack^jbib_000_u` — словарь и drawable разделены `^`.
    Durty ожидает только drawable (`jbib_000_u`), без префикса словаря.
    """
    s = stem.strip()
    if "^" in s:
        return s.split("^", 1)[-1].strip()
    return s


def parse_ydd_filename_durty(stem: str) -> DurtyParsed | None:
    """
    Ожидаемый формат имени (как в Durty):
    - компонент: jbib_000_u, uppr_001_u, … (минимум 3 части)
    - проп: p_head_000, p_eyes_001, …
    """
    parts = stem.split("_")
    if len(parts) < 3:
        return None

    if parts[0].lower() == "p":
        sub = parts[1].lower()
        bind = parts[2]
        prefix = _PROP_TO_TEX_PREFIX.get(sub)
        if not prefix:
            return None
        return DurtyParsed(
            is_prop=True,
            drawable_key=prefix,
            texture_prefix=prefix,
            bind_number=bind,
            postfix="",
            is_variation=len(parts) > 3,
        )

    dr = parts[0].lower()
    if dr not in _COMPONENT_DRAWABLE_TO_TEX_PREFIX:
        return None
    tex_prefix = _COMPONENT_DRAWABLE_TO_TEX_PREFIX[dr]
    bind = parts[1]
    postfix = parts[2].lower()
    return DurtyParsed(
        is_prop=False,
        drawable_key=dr,
        texture_prefix=tex_prefix,
        bind_number=bind,
        postfix=postfix,
        is_variation=len(parts) > 3,
    )


def iter_durty_texture_filenames(parsed: DurtyParsed) -> list[str]:
    """Имена .ytd в той же папке, что и .ydd (ClothData.SearchForTextures)."""
    out: list[str] = []
    for i in range(26):
        letter = chr(ord("a") + i)
        pfx = parsed.texture_prefix
        b = parsed.bind_number
        if not parsed.is_prop:
            out.append(f"{pfx}_diff_{b}_{letter}_uni.ytd")
            out.append(f"{pfx}_diff_{b}_{letter}_whi.ytd")
        else:
            out.append(f"{pfx}_diff_{b}_{letter}.ytd")
    return out


def durty_kind_slot(parsed: DurtyParsed) -> tuple[str, str] | None:
    """kind (cloth|prop) и slot_slug для epic-имен."""
    return _DURTY_PREFIX_TO_KIND_SLOT.get(parsed.texture_prefix)


def _gender_from_segment_sets(
    parts: list[str],
    male_segs: frozenset[str],
    female_segs: frozenset[str],
) -> str | None:
    has_m = any(p in male_segs for p in parts)
    has_f = any(p in female_segs for p in parts)
    if has_m and not has_f:
        return "male"
    if has_f and not has_m:
        return "female"
    return None


def infer_gender_from_path_segments(rel_posix: str) -> str | None:
    """
    Как в Durty: мужской/женский набор задаётся отдельно; в каталогах часто папки male/female.
    Сравниваем только целые сегменты пути (без случайных вхождений «male» в середине имени).
    """
    parts = re.split(r"[\\/]+", rel_posix.strip().lower())
    male_segs = frozenset(
        {"male", "m", "men", "mp_m_freemode_01", "mp_m", "masculine", "муж", "мужской"}
    )
    female_segs = frozenset(
        {
            "female",
            "f",
            "women",
            "mp_f_freemode_01",
            "mp_f",
            "feminine",
            "жен",
            "женский",
        }
    )
    return _gender_from_segment_sets(parts, male_segs, female_segs)


def infer_gender_from_filename_stem(stem: str) -> str | None:
    """
    Пол по stem .ydd / .ytd: сегменты через _ - как jbib_000_m_u / jbib_000_f_u, mp_m, mp_f, male, female.
    Отдельные сегменты m / f учитываются (типично для Durty).
    Для stream (`dict^drawable`) пол берётся из префикса до `^` (mp_f_freemode / mp_m_freemode),
    иначе из части после `^` по тем же правилам.
    """
    s = stem.strip()
    if "^" in s:
        prefix, drawable = s.split("^", 1)
        prefix_l = prefix.strip().lower()
        if "mp_m_freemode" in prefix_l:
            return "male"
        if "mp_f_freemode" in prefix_l:
            return "female"
        s = drawable.strip()

    parts = re.split(r"[_\-\s]+", s.lower())
    if not parts:
        return None
    male_segs = frozenset(
        {
            "male",
            "m",
            "men",
            "mens",
            "mp_m_freemode_01",
            "mp_m",
            "mpm",
            "masculine",
            "муж",
            "мужской",
        }
    )
    female_segs = frozenset(
        {
            "female",
            "f",
            "women",
            "womens",
            "mp_f_freemode_01",
            "mp_f",
            "mpf",
            "feminine",
            "жен",
            "женский",
        }
    )
    return _gender_from_segment_sets(parts, male_segs, female_segs)
