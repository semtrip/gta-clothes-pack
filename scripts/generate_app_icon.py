"""Пересобрать icons/gta-clothes-pack.ico из icons/gta-clothes-pack.png (нужен Pillow)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    png = root / "icons" / "gta-clothes-pack.png"
    ico = root / "icons" / "gta-clothes-pack.ico"
    if not png.is_file():
        raise SystemExit(f"Not found: {png}")
    im = Image.open(png).convert("RGBA")
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    im.save(ico, format="ICO", sizes=sizes)
    print(f"OK: {ico} ({ico.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
