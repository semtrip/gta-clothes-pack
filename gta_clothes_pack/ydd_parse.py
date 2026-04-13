from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fivefury.assets.ydd import YddAsset
from fivefury.binary import u16 as _u16, u32 as _u32, u64 as _u64
from fivefury.resource import checked_virtual_offset, read_virtual_pointer_array, split_rsc7_sections
from fivefury.ydr.defs import DAT_VIRTUAL_BASE
from fivefury.ydr.read_materials import parse_materials
from fivefury.ydr.reader import load_shader_library
from fivefury.ydr.reader import (
    _decode_parameter_value,
    _hash_name,
    _read_pointer_array,
    _resolve_name,
    _try_read_c_string,
)


def _vo(pointer: int, data: bytes) -> int:
    return checked_virtual_offset(pointer, data, base=DAT_VIRTUAL_BASE, allow_plain_offset=True)


def _read_ptr_array(pointer: int, count: int, system_data: bytes) -> list[int]:
    return read_virtual_pointer_array(system_data, pointer, count, base=DAT_VIRTUAL_BASE, allow_plain_offset=True)


_shader_library_cache: object | None = None


def get_shader_library_cached():
    """load_shader_library() тяжёлый — один раз на процесс."""
    global _shader_library_cache
    if _shader_library_cache is None:
        _shader_library_cache = load_shader_library()
    return _shader_library_cache


@dataclass
class YddParseResult:
    texture_names: set[str] = field(default_factory=set)
    drawable_labels: list[str] = field(default_factory=list)
    drawable_name_strings: list[str] = field(default_factory=list)
    embedded_texture_dicts: int = 0
    errors: list[str] = field(default_factory=list)
    # Литералы в бинарнике (RAGE ped names) — надёжнее путей на диске
    binary_has_mp_m_freemode_01: bool = False
    binary_has_mp_f_freemode_01: bool = False


def _scan_freemode_ped_markers(raw: bytes) -> tuple[bool, bool]:
    """Поиск mp_m_freemode_01 / mp_f_freemode_01 по всему файлу (нижний регистр)."""
    low = raw.lower()
    return (b"mp_m_freemode_01" in low, b"mp_f_freemode_01" in low)


def parse_ydd_file(path: Path) -> YddParseResult:
    out = YddParseResult()
    try:
        raw = path.read_bytes()
    except OSError as e:
        out.errors.append(f"read {path}: {e}")
        return out

    out.binary_has_mp_m_freemode_01, out.binary_has_mp_f_freemode_01 = _scan_freemode_ped_markers(raw)

    try:
        header, system_data, _graphics = split_rsc7_sections(raw)
    except Exception as e:
        out.errors.append(f"rsc7 {path}: {e}")
        return out

    try:
        asset = YddAsset.from_bytes(raw, path=str(path))
    except Exception as e:
        out.errors.append(f"ydd asset {path}: {e}")
        return out

    for emb in asset.iter_embedded_texture_dictionaries():
        out.embedded_texture_dicts += 1
        for t in emb.ytd.textures:
            out.texture_names.add(t.name)

    shader_library = get_shader_library_cached()
    count = _u16(system_data, 0x38)
    drawables_pointer = _u64(system_data, 0x30)
    if not drawables_pointer or not count:
        return out

    drawable_pointers = _read_ptr_array(drawables_pointer, count, system_data)

    for index, drawable_pointer in enumerate(drawable_pointers):
        label = f"drawable_{index}"
        out.drawable_labels.append(label)
        if not drawable_pointer:
            continue
        d_off = _vo(drawable_pointer, system_data)

        name_ptr = _u64(system_data, d_off + 0xA8)
        if name_ptr:
            try:
                ns = _try_read_c_string(name_ptr, system_data)
                if ns:
                    out.drawable_name_strings.append(ns)
            except Exception:
                pass

        root_off = d_off + 0x10
        try:
            materials, _td_ptr = parse_materials(
                system_data,
                shader_library,
                root_offset=root_off,
                virtual_offset=_vo,
                u16=_u16,
                u32=_u32,
                u64=_u64,
                read_pointer_array=_read_ptr_array,
                resolve_name=_resolve_name,
                hash_name=_hash_name,
                decode_parameter_value=_decode_parameter_value,
                try_read_c_string=_try_read_c_string,
            )
        except Exception as e:
            out.errors.append(f"{label}: materials {e}")
            continue

        for mat in materials:
            for tr in mat.textures:
                if tr.name:
                    out.texture_names.add(tr.name)

    return out


def collect_strings_for_heuristics(path: Path, *, max_strings: int = 200) -> list[str]:
    """Extra ASCII strings from system section (fallback for gender/slot)."""
    try:
        raw = path.read_bytes()
        _, system_data, _ = split_rsc7_sections(raw)
    except Exception:
        return []
    out: list[str] = []
    i = 0
    while i < len(system_data) and len(out) < max_strings:
        if system_data[i] < 32 or system_data[i] > 126:
            i += 1
            continue
        start = i
        while i < len(system_data) and 32 <= system_data[i] <= 126:
            i += 1
        chunk = system_data[start:i].decode("ascii", errors="ignore")
        if len(chunk) >= 4:
            out.append(chunk)
        i += 1
    return out
