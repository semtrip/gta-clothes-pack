"""PyInstaller runtime hook: register pure-Python ``fivefury.hashing`` before other imports."""
from __future__ import annotations

import sys

if getattr(sys, "frozen", False):
    from gta_clothes_pack.fivefury_hashing_shim import install_fivefury_hashing_shim

    install_fivefury_hashing_shim()
