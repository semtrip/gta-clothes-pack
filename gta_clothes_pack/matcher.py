from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import Settings
from .durty_names import iter_durty_texture_filenames, parse_ydd_filename_durty
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
    settings: Settings | None = None,
) -> YddMatch:
    """Подбор YTD по уже разобранному YDD (без повторного чтения файла)."""
    m = YddMatch(ydd_path=ydd_path, parse=pr)
    strict = bool(settings and settings.strict_engine_identity)
    pair_stem = (
        settings.pair_ytd_same_stem_as_ydd
        if settings is not None and not strict
        else (False if strict else True)
    )

    seen: set[Path] = set()
    if pr.texture_names:
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

    if pair_stem:
        stem = ydd_path.stem.lower()
        for e in tex_index.find_by_stem(stem):
            if e.path not in seen:
                seen.add(e.path)
                m.ytd_paths.append(e.path)

    use_durty = (
        settings.durty_cloth_texture_patterns
        if settings is not None and not strict
        else (False if strict else True)
    )
    if use_durty:
        dp = parse_ydd_filename_durty(ydd_path.stem)
        if dp and not dp.is_variation:
            ydd_dir = ydd_path.parent
            for fname in iter_durty_texture_filenames(dp):
                for e in tex_index.find_same_dir_by_filename(ydd_dir, fname):
                    if e.path not in seen:
                        seen.add(e.path)
                        m.ytd_paths.append(e.path)

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
