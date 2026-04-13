"""
Подсказки пола из раскладки stream / DLC: .ymt и имена папок freemode.

Типичный случай (mpbusiness и т.п.):
  stream/
    mp_m_freemode_01_male_freemode_business.ymt
    mp_f_freemode_01_female_freemode_business.ymt
    mp_m_freemode_01_male_freemode_business/   … .ydd
    mp_f_freemode_01_female_freemode_business/ … .ydd

В одной папке stream два .ymt разного пола — старый «индекс одной папки» бесполезен.
Решение: пол по префиксу имени папки (mp_m_freemode_01* / mp_f_freemode_01*) и по stem .ymt.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


def gender_from_freemode_name_prefix(name: str) -> str | None:
    """
    Пол по имени файла без расширения, папки или любого сегмента пути.

    Поддерживаются:
      mp_m_freemode_01.ymt, mp_m_freemode_01_p.ymt
      mp_m_freemode_01_male_freemode_business.ymt
      папка mp_f_freemode_01_female_freemode_business
    """
    s = name.strip().lower()
    if s.startswith("mp_f_freemode_01"):
        return "female"
    if s.startswith("mp_m_freemode_01"):
        return "male"
    return None


def build_ymt_stem_gender_map(root: Path) -> dict[str, str]:
    """stem .ymt (lower) -> пол; для сопоставления с именем папки над stream."""
    out: dict[str, str] = {}
    for ymt in root.rglob("*.ymt"):
        g = gender_from_freemode_name_prefix(ymt.stem)
        if g is not None:
            out[ymt.stem.lower()] = g
    return out


def build_ymt_folder_gender_index(root: Path) -> dict[str, str | None]:
    """
    Только папки, где ровно один пол по freemode .ymt (нет двух mp_m и mp_f вместе).
    """
    folder_genders: dict[str, set[str]] = defaultdict(set)
    for ymt in root.rglob("*.ymt"):
        g = gender_from_freemode_name_prefix(ymt.stem)
        if g is None:
            continue
        folder_genders[str(ymt.parent.resolve())].add(g)

    out: dict[str, str | None] = {}
    for folder, genders in folder_genders.items():
        if len(genders) == 1:
            out[folder] = next(iter(genders))
        else:
            out[folder] = None
    return out


def gender_hint_for_ydd_path(
    ydd_path: Path,
    root: Path,
    *,
    ymt_stem_map: dict[str, str],
    ymt_folder_index: dict[str, str | None],
) -> str | None:
    """
    Приоритет:
    1) Имя любой папки от каталога с .ydd вверх до input_root: mp_*_freemode_01…
    2) Имя родительской папки .ydd совпадает со stem какого-либо .ymt под root (файл лежит в stream).
    3) Индекс папок с одним freemode .ymt (как раньше).
    """
    root = root.resolve()

    # 1) Папки: …/mp_f_freemode_01_female_freemode_business/…
    cur = ydd_path.parent.resolve()
    while True:
        g = gender_from_freemode_name_prefix(cur.name)
        if g is not None:
            return g
        if cur == root:
            break
        parent = cur.parent
        if parent == cur:
            break
        cur = parent

    # 2) Папка с YDD называется как DLC-pack: тот же stem, что у .ymt в stream
    parent_name = ydd_path.parent.name.lower()
    if parent_name in ymt_stem_map:
        return ymt_stem_map[parent_name]

    # 3) Одна ymt на папку
    cur = ydd_path.parent.resolve()
    while True:
        key = str(cur)
        if key in ymt_folder_index:
            g = ymt_folder_index[key]
            if g is not None:
                return g
        if cur == root:
            break
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return None


@dataclass(frozen=True)
class YmtGenderContext:
    """Собрано один раз в analyze_input, передаётся в воркеры."""

    stem_map: dict[str, str]
    folder_index: dict[str, str | None]

    @classmethod
    def build(cls, root: Path) -> YmtGenderContext:
        return cls(
            stem_map=build_ymt_stem_gender_map(root),
            folder_index=build_ymt_folder_gender_index(root),
        )


def gender_from_freemode_ymt_stem(stem: str) -> str | None:
    """Алиас к gender_from_freemode_name_prefix (имя .ymt без расширения)."""
    return gender_from_freemode_name_prefix(stem)
