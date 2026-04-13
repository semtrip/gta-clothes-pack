"""Точка входа для PyInstaller (один файл .exe)."""
from __future__ import annotations

import os

# Сразу после распаковки onefile — меньше буферизации stdout в консоли
os.environ.setdefault("PYTHONUNBUFFERED", "1")

from gta_clothes_pack.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
