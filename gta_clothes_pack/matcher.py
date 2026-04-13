from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .ydd_parse import YddParseResult, parse_ydd_file
from .ytd_index import YtdEntry, find_ytd_for_texture, scan_ytd_tree


@dataclass
class YddMatch:
    ydd_path: Path
    parse: YddParseResult
    ytd_paths: list[Path] = field(default_factory=list)
    ambiguous_textures: list[str] = field(default_factory=list)
    missing_textures: list[str] = field(default_factory=list)


def match_one_ydd(
    ydd_path: Path,
    ytd_entries: list[YtdEntry],
) -> YddMatch:
    pr = parse_ydd_file(ydd_path)
    m = YddMatch(ydd_path=ydd_path, parse=pr)
    if not pr.texture_names:
        return m

    seen: set[Path] = set()
    for tex in sorted(pr.texture_names):
        hits = find_ytd_for_texture(tex, ytd_entries)
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


def match_all_ydds(input_root: Path, ytd_entries: list[YtdEntry]) -> list[YddMatch]:
    out: list[YddMatch] = []
    for ydd in sorted(input_root.rglob("*.ydd")):
        out.append(match_one_ydd(ydd, ytd_entries))
    return out


def build_ytd_index(input_root: Path) -> list[YtdEntry]:
    return scan_ytd_tree(input_root)
