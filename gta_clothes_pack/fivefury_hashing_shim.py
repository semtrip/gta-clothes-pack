"""Pure-Python replacement for ``fivefury.hashing.jenk_hash`` when the native wheel breaks.

The upstream extension can raise ``SystemError: PY_SSIZE_T_CLEAN macro must be defined for '#' formats``
in some PyInstaller / Python combinations. The algorithm matches ``fivefury``'s C implementation:
Jenkins one-at-a-time mixing on UTF-8 bytes with a 256-byte lookup table from ``data/lut.dat``.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from functools import lru_cache
from pathlib import Path
from typing import Final

_IDENTITY_LUT: Final[bytes] = bytes(range(256))
_SHIM_ATTR: Final[str] = "_gta_clothes_pack_jenk_hash_shim"


def _env_force_shim() -> bool:
    v = os.environ.get("GTA_CLOTHES_PACK_FIVEFURY_HASHING_SHIM", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _should_install() -> bool:
    if _env_force_shim():
        return True
    return bool(getattr(sys, "frozen", False))


@lru_cache(maxsize=1)
def _read_lut_bytes() -> bytes:
    """Load ``lut.dat`` without importing ``fivefury`` (avoids pulling ``fivefury.__init__``)."""
    spec = importlib.util.find_spec("fivefury")
    roots: list[str] = []
    if spec and spec.submodule_search_locations:
        roots.extend(spec.submodule_search_locations)
    for root in roots:
        p = Path(root) / "data" / "lut.dat"
        if p.is_file():
            data = p.read_bytes()
            if len(data) == 256:
                return data
    return _IDENTITY_LUT


def _jenk_hash_pure(value: str | bytes, *, encoding: str = "utf-8") -> int:
    text = value if isinstance(value, str) else value.decode(encoding)
    lut = _read_lut_bytes()
    h = 0
    for b in text.encode("utf-8"):
        v = lut[b]
        h = (h + v) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    h = (h + (h << 15)) & 0xFFFFFFFF
    return h


def install_fivefury_hashing_shim() -> None:
    """Pre-register ``fivefury.hashing`` so ``from fivefury...`` never loads ``_native_abi3`` for jenk_hash."""
    if not _should_install():
        return
    existing = sys.modules.get("fivefury.hashing")
    if existing is not None and getattr(existing, _SHIM_ATTR, False):
        return
    if existing is not None:
        # Another loader already registered hashing; do not replace.
        return

    mod = types.ModuleType("fivefury.hashing")
    mod.jenk_hash = _jenk_hash_pure
    mod.__all__ = ["jenk_hash"]
    setattr(mod, _SHIM_ATTR, True)
    sys.modules["fivefury.hashing"] = mod
