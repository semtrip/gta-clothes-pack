"""PyInstaller runtime hook: register pure-Python ``fivefury.hashing`` before other imports."""
from __future__ import annotations

from gta_clothes_pack.fivefury_hashing_shim import install_fivefury_hashing_shim

# install_fivefury_hashing_shim() no-ops unless frozen / _MEIPASS / env (see shim).
install_fivefury_hashing_shim()
