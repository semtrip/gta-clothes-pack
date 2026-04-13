from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .ydd_parse import YddParseResult, parse_ydd_file
from .ytd_index import TextureIndex, YtdEntry, find_ytd_for_texture, scan_ytd_tree


@dataclass
class YddMatch:
    ydd_path: Path
    parse: YddParseResult
    ytd_paths: list[Path] = field(default_factory=list)
    ambiguous_textures: list[str] = field(default_factory=list)
    missing_textures: list[str] = field(default_factory=list)


def match_from_parse(
    ydd_path: Path,
    pr: YddParseResult,
    tex_index: TextureIndex,
) -> YddMatch:
    """Подбор YTD по уже разобранному YDD (без повторного чтения файла)."""
    m = YddMatch(ydd_path=ydd_path, parse=pr)
    if not pr.texture_names:
        return m

    seen: set[Path] = set()
    for tex in sorted(pr.texture_names):
        hits = tex_index.find(tex)
        if not hits:
            m.missing_textures.append(tex)
            continue
        if len(hits) > 1:
            m.ambiguous_textures.append(tex)
        h = hits[0]
        if h.path not in seen:
            seen.add(h.path)
            m.ytd_paths.append(h.path)

    return m


def match_one_ydd(
    ydd_path: Path,
    ytd_entries: list[YtdEntry],
) -> YddMatch:
    """Полный путь: разбор YDD + матч (для совместимости)."""
    pr = parse_ydd_file(ydd_path)
    tex_index = TextureIndex(ytd_entries)
    return match_from_parse(ydd_path, pr, tex_index)


def match_all_ydds(input_root: Path, ytd_entries: list[YtdEntry]) -> list[YddMatch]:
    tex_index = TextureIndex(ytd_entries)
    out: list[YddMatch] = []
    for ydd in sorted(input_root.rglob("*.ydd")):
        pr = parse_ydd_file(ydd)
        out.append(match_from_parse(ydd, pr, tex_index))
    return out


def build_ytd_index(input_root: Path) -> list[YtdEntry]:
    return scan_ytd_tree(input_root)
