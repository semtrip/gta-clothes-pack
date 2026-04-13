"""
Мета freemode: бинарные .ymt (литералы в файле) и экспорт CodeWalker *.ymt.xml.

Имена файлов/папок не используются — только содержимое .ymt и разметка XML.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .ped_markers import scan_freemode_ped_markers
from .ymt_hints import gender_from_freemode_name_prefix

if TYPE_CHECKING:
    from .config import Settings


def _local_tag(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


# Подстроки в имени тега предка (CodeWalker: hash_… и читаемые имена)
_XML_ANCESTOR_TAG_HINTS: list[tuple[str, str, str]] = [
    ("pv_comp_jbib", "cloth", "tops"),
    ("pv_comp_uppr", "cloth", "tops"),
    ("pv_comp_lowr", "cloth", "legs"),
    ("pv_comp_feet", "cloth", "shoes"),
    ("pv_comp_hand", "cloth", "accessories"),
    ("pv_comp_teef", "cloth", "undershirts"),
    ("pv_comp_accs", "cloth", "accessories"),
    ("pv_comp_task", "cloth", "bags_and_parachutes"),
    ("pv_comp_decl", "cloth", "decals"),
    ("pv_comp_berd", "cloth", "masks"),
    ("pv_comp_hair", "cloth", "hair_styles"),
    ("pv_comp_head", "cloth", "hair_styles"),
    ("jbib", "cloth", "tops"),
    ("uppr", "cloth", "tops"),
    ("lowr", "cloth", "legs"),
    ("feet", "cloth", "shoes"),
    ("hand", "cloth", "accessories"),
    ("teef", "cloth", "undershirts"),
    ("berd", "cloth", "masks"),
    ("hair", "cloth", "hair_styles"),
    ("task", "cloth", "bags_and_parachutes"),
    ("decl", "cloth", "decals"),
    ("accs", "cloth", "accessories"),
    ("p_head", "prop", "hats"),
    ("p_eyes", "prop", "glasses"),
    ("p_ears", "prop", "ears"),
    ("p_mouth", "prop", "mouth"),
    ("p_lhand", "prop", "hands"),
    ("p_rhand", "prop", "hands"),
    ("p_lwrist", "prop", "watches"),
    ("p_rwrist", "prop", "watches"),
    ("p_legs", "prop", "legs"),
]


def _merge_rules_tuples(settings: "Settings | None") -> list[tuple[str, str, str]]:
    if settings is None:
        return [(a, b, c) for a, b, c in _XML_ANCESTOR_TAG_HINTS]
    out: list[tuple[str, str, str]] = []
    for row in settings.prefix_rules:
        if len(row) >= 3:
            out.append((row[0].lower(), row[1], row[2]))
    if not out:
        return [(a, b, c) for a, b, c in _XML_ANCESTOR_TAG_HINTS]
    return out


def _element_refs_drawable(el: ET.Element, dname: str) -> bool:
    if not dname:
        return False
    for v in el.attrib.values():
        if v.strip() == dname:
            return True
    blob = "".join(el.itertext())
    if dname in blob:
        return True
    return False


def _build_parent_map(root: ET.Element) -> dict[ET.Element, ET.Element | None]:
    parents: dict[ET.Element, ET.Element | None] = {root: None}
    for p in root.iter():
        for ch in list(p):
            parents[ch] = p
    return parents


def _slot_from_ancestors(
    el: ET.Element,
    parents: dict[ET.Element, ET.Element | None],
    rules: list[tuple[str, str, str]],
) -> tuple[str, str, str] | None:
    ordered = sorted(rules, key=lambda x: -len(x[0]))
    cur: ET.Element | None = el
    while cur is not None:
        tag = _local_tag(cur.tag).lower()
        for prefix, kind, slug in ordered:
            pl = prefix.lower()
            if pl in tag:
                return kind, slug, prefix
        cur = parents.get(cur)
    return None


def slot_from_ymt_xml_tree(
    root_el: ET.Element,
    drawable_name: str,
    settings: "Settings | None",
) -> tuple[str, str, str] | None:
    """Ищем элемент, где встречается имя drawable, поднимаемся по предкам — подсказка слота по тегам."""
    rules = _merge_rules_tuples(settings)
    parents = _build_parent_map(root_el)
    for el in root_el.iter():
        if not _element_refs_drawable(el, drawable_name):
            continue
        hit = _slot_from_ancestors(el, parents, rules)
        if hit is not None:
            return hit
    return None


def gender_from_ymt_xml_root(root_el: ET.Element) -> str | None:
    if _local_tag(root_el.tag) != "CPedVariationInfo":
        return None
    name = root_el.get("name")
    if not name:
        return None
    return gender_from_freemode_name_prefix(name)


def drawable_in_xml_tree(root_el: ET.Element, names: list[str]) -> bool:
    for el in root_el.iter():
        for dn in names:
            if _element_refs_drawable(el, dn):
                return True
    return False


def scan_first_folder_ymt_binary_flags(ydd_path: Path, root: Path) -> tuple[bool, bool]:
    """
    Первый каталог от папки с YDD вверх до root, где есть *.ymt: объединяем литералы из всех .ymt там.
    """
    root = root.resolve()
    cur = ydd_path.parent.resolve()
    while True:
        ymts = list(cur.glob("*.ymt"))
        if ymts:
            has_m = False
            has_f = False
            for ymt in ymts:
                try:
                    raw = ymt.read_bytes()
                except OSError:
                    continue
                m, f = scan_freemode_ped_markers(raw)
                has_m |= m
                has_f |= f
            return has_m, has_f
        if cur == root:
            break
        parent = cur.parent
        if parent == cur:
            break
        cur = parent.resolve()
    return False, False


def iter_ymt_xml_paths_upward(ydd_path: Path, root: Path) -> list[Path]:
    """*.ymt.xml от папки с YDD к root."""
    root = root.resolve()
    out: list[Path] = []
    cur = ydd_path.parent.resolve()
    while True:
        for p in sorted(cur.glob("*.ymt.xml")):
            out.append(p)
        if cur == root:
            break
        parent = cur.parent
        if parent == cur:
            break
        cur = parent.resolve()
    return out


@dataclass
class YmtMetaResolution:
    """Результат use_ymt_meta для одного YDD."""

    binary_m: bool = False
    binary_f: bool = False
    xml_gender: str | None = None
    xml_slot: tuple[str, str, str] | None = None


def resolve_ymt_meta_for_ydd(
    ydd_path: Path,
    root: Path,
    drawable_names: list[str],
    settings: "Settings",
) -> YmtMetaResolution:
    """
    Бинарные .ymt в первом каталоге с мета-файлами.
    *.ymt.xml: слот/пол, если drawable встречается в XML и корень CPedVariationInfo.
    """
    r = YmtMetaResolution()
    if not getattr(settings, "use_ymt_meta", True):
        return r

    r.binary_m, r.binary_f = scan_first_folder_ymt_binary_flags(ydd_path, root)

    if not getattr(settings, "use_ymt_xml_meta", True):
        return r

    names = [n for n in drawable_names if n.strip()]
    if not names:
        return r

    for xml_path in iter_ymt_xml_paths_upward(ydd_path, root):
        try:
            tree = ET.parse(xml_path)
            root_el = tree.getroot()
        except (ET.ParseError, OSError):
            continue
        g = gender_from_ymt_xml_root(root_el)
        slot: tuple[str, str, str] | None = None
        for dn in names:
            slot = slot_from_ymt_xml_tree(root_el, dn, settings)
            if slot is not None:
                r.xml_slot = slot
                r.xml_gender = g
                return r
        # Drawable есть в мета, но теги предков не сопоставились — пол из CPedVariationInfo@name
        if drawable_in_xml_tree(root_el, names) and g is not None:
            r.xml_gender = g
            return r
    return r


def gender_from_binary_flags(has_m: bool, has_f: bool) -> str | None:
    if has_m and not has_f:
        return "male"
    if has_f and not has_m:
        return "female"
    if has_m and has_f:
        return "unknown"
    return None
