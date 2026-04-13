"""
Идентичность freemode из данных RAGE внутри YDD, а не из имени файла на диске.

В оригинальных и корректно экспортированных YDD drawable часто называется так:
  mp_m_freemode_01^jbib_000_u
  mp_f_freemode_01^p_head_000

Левая часть до «^» — привязка к ped (пол), правая — компонент/проп (как в GTAUtil ComponentFilePrefix / AnchorFilePrefix).

GTAUtil (GenPedDefs) опирается на путь и regex имени файла — при переименовании это ломается.
Здесь используются только строки drawable, прочитанные из ресурса (см. ydd_parse.parse_ydd_file).
"""

from __future__ import annotations

import re

_PED_M = "mp_m_freemode_01"
_PED_F = "mp_f_freemode_01"


def drawable_component_part(name: str) -> str:
    """
    Часть имени, по которой определяется слот (компонент/проп).
    Если есть «^», берётся правая часть (имя drawable в словаре).
    """
    s = name.strip()
    if not s:
        return ""
    if "^" in s:
        s = s.split("^", 1)[1].strip()
    return s


def _ped_marker_from_drawable_string(raw: str, *, caret_only: bool) -> str | None:
    """
    caret_only=True: только ped^drawable (без доверия к demonic_003, tattoo и т.д.).
    caret_only=False: устаревший режим — ещё и строка, начинающаяся с mp_*_freemode_01.
    """
    s = raw.strip()
    if not s:
        return None
    if "^" in s:
        left = s.split("^", 1)[0].strip().lower()
        has_m = left.startswith(_PED_M)
        has_f = left.startswith(_PED_F)
        if has_m and has_f:
            return "unknown"
        if has_m:
            return "male"
        if has_f:
            return "female"
        return None
    if caret_only:
        return None
    low = s.lower()
    if low.startswith(_PED_M):
        return "male"
    if low.startswith(_PED_F):
        return "female"
    return None


def infer_gender_from_drawable_names(names: list[str], *, caret_only: bool = True) -> str | None:
    """
    Пол по строкам drawable. При caret_only=True — только нотация mp_*_freemode_01^… (безопасно).

    Returns
    -------
    "male" | "female"
        Все drawable с явным ped-id согласованы.
    "unknown"
        Смешаны male и female между drawable или конфликт внутри строки.
    None
        Ни одна строка не содержит явного ped-id (пол не выводится из drawable).
    """
    markers: list[str] = []
    for raw in names:
        m = _ped_marker_from_drawable_string(raw, caret_only=caret_only)
        if m is not None:
            markers.append(m)
    if not markers:
        return None
    if any(m == "unknown" for m in markers):
        return "unknown"
    uniq = set(markers)
    if uniq == {"male"}:
        return "male"
    if uniq == {"female"}:
        return "female"
    return "unknown"


def slot_from_caret_freemode_only(
    drawable_names: list[str],
    rules: list[tuple[str, str, str]],
) -> tuple[str, str, str] | None:
    """
    Слот только если drawable в форме mp_{m|f}_freemode_01^component — правая часть как у Rockstar.
    «demonic_003» без ped слева от «^» не используется.
    """
    filtered: list[str] = []
    for raw in drawable_names:
        if "^" not in raw:
            continue
        left = raw.split("^", 1)[0].strip().lower()
        if left.startswith(_PED_M) or left.startswith(_PED_F):
            filtered.append(raw)
    if not filtered:
        return None
    return slot_from_drawable_identity(filtered, rules)


def slot_from_drawable_identity(
    drawable_names: list[str],
    rules: list[tuple[str, str, str]],
) -> tuple[str, str, str] | None:
    """
    kind, slot_slug, hint по правой части после ^ или по строке jbib_… / p_head_…
    rules: (prefix, kind, slot) из Settings.prefix_rules.
    """
    ordered = sorted(rules, key=lambda x: -len(x[0]))

    for raw in drawable_names:
        part = drawable_component_part(raw)
        if not part:
            continue
        hay = part.lower()
        for prefix, kind, slug in ordered:
            pl = prefix.lower()
            if hay == pl or hay.startswith(pl + "_") or hay.startswith(pl + "^"):
                return kind, slug, prefix
            if re.match(rf"^{re.escape(pl)}(?![a-z0-9])", hay):
                return kind, slug, prefix
    return None
