from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fivefury.ytd import read_ytd


@dataclass
class YtdEntry:
    path: Path
    stem: str
    texture_names: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)


class TextureIndex:
    """
    Быстрый поиск YTD по имени текстуры: в памяти map texture_lower -> [YtdEntry, ...].
    Строится один раз после сканирования всех YTD.
    """

    __slots__ = ("entries", "_by_texture_lower")

    def __init__(self, entries: list[YtdEntry]) -> None:
        self.entries = entries
        self._by_texture_lower: dict[str, list[YtdEntry]] = {}
        for e in entries:
            if e.errors:
                continue
            for tn in e.texture_names:
                key = tn.lower()
                bucket = self._by_texture_lower.setdefault(key, [])
                if e not in bucket:
                    bucket.append(e)

    @property
    def texture_key_count(self) -> int:
        return len(self._by_texture_lower)

    def find(self, texture_name: str) -> list[YtdEntry]:
        return list(self._by_texture_lower.get(texture_name.lower(), []))


def scan_ytd_tree(root: Path) -> list[YtdEntry]:
    """All .ytd under root (same stem in different folders allowed)."""
    entries: list[YtdEntry] = []
    for path in sorted(root.rglob("*.ytd")):
        stem = path.stem.lower()
        entry = YtdEntry(path=path, stem=stem)
        try:
            ytd = read_ytd(path)
            for t in ytd.textures:
                entry.texture_names.add(t.name)
        except Exception as e:
            entry.errors.append(str(e))
        entries.append(entry)
    return entries


def find_ytd_for_texture(
    texture_name: str,
    entries: list[YtdEntry],
) -> list[YtdEntry]:
    """Линейный поиск (устаревший путь); предпочтительно TextureIndex.find."""
    lower = texture_name.lower()
    hits: list[YtdEntry] = []
    for e in entries:
        for tn in e.texture_names:
            if tn.lower() == lower:
                hits.append(e)
                break
    return hits
