"""Общие литералы ped freemode в сыром бинарнике (YDD, YMT и т.д.)."""

from __future__ import annotations


def scan_freemode_ped_markers(raw: bytes) -> tuple[bool, bool]:
    """
    Только полные литералы mp_*_freemode_01 (ASCII и UTF-16LE).
    Возвращает (has_male_literal, has_female_literal).
    """
    low = raw.lower()
    has_m = b"mp_m_freemode_01" in low
    has_f = b"mp_f_freemode_01" in low
    if not has_m and not has_f:
        m16 = "mp_m_freemode_01".encode("utf-16le")
        f16 = "mp_f_freemode_01".encode("utf-16le")
        has_m = m16 in raw
        has_f = f16 in raw
    return has_m, has_f
