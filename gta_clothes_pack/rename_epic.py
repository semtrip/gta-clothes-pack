from __future__ import annotations

from pathlib import Path

from fivefury.ytd import read_ytd
from fivefury.ytd.model import Ytd


def epic_prefix(kind: str) -> str:
    k = kind.lower()
    if k == "prop":
        return "epic_prop"
    return "epic_cloth"


def build_epic_ydd_name(
    kind: str,
    gender_short: str,
    slot_slug: str,
    number: int,
    *,
    number_width: int,
) -> str:
    pref = epic_prefix(kind)
    nn = str(number).zfill(number_width)
    slug = slot_slug.replace(" ", "_")
    return f"{pref}__{gender_short}_{slug}_{nn}"


def build_epic_ytd_name(
    kind: str,
    gender_short: str,
    slot_slug: str,
    number: int,
    texture_index: int,
    *,
    number_width: int,
    tex_width: int,
) -> str:
    base = build_epic_ydd_name(kind, gender_short, slot_slug, number, number_width=number_width)
    ti = str(texture_index).zfill(tex_width)
    return f"{base}_{ti}"


def patch_cstring_inplace(data: bytearray, old: str, new: str) -> int:
    """Replace null-terminated old string with new, padded/truncated to same byte length. Returns count of replacements."""
    old_b = old.encode("utf-8") + b"\x00"
    new_raw = new.encode("utf-8")
    if len(new_raw) >= len(old_b):
        new_b = new_raw[: len(old_b) - 1] + b"\x00"
    else:
        new_b = new_raw + b"\x00" * (len(old_b) - len(new_raw))
    count = 0
    start = 0
    while True:
        pos = data.find(old_b, start)
        if pos < 0:
            break
        data[pos : pos + len(old_b)] = new_b
        count += 1
        start = pos + len(old_b)
    return count


def rewrite_ytd_with_mapping(path: Path, name_map: dict[str, str], out_path: Path) -> None:
    ytd: Ytd = read_ytd(path)
    lower_map = {k.lower(): v for k, v in name_map.items()}
    for tex in ytd.textures:
        new_name = lower_map.get(tex.name.lower())
        if new_name is not None:
            tex.name = new_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ytd.save(out_path)


def patch_ydd_raw(path: Path, name_map: dict[str, str], out_path: Path) -> tuple[int, list[str]]:
    """Apply cstring replacements for texture/dict name references."""
    raw = bytearray(path.read_bytes())
    total = 0
    errs: list[str] = []
    for old, new in name_map.items():
        if not old:
            continue
        try:
            total += patch_cstring_inplace(raw, old, new)
        except Exception as e:
            errs.append(f"{old}->{new}: {e}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(bytes(raw))
    return total, errs
