from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Settings
from .pipeline import run_pack


def _menu(base: Settings) -> Settings:
    print("=== GTA Clothes Pack ===")
    base.input_root = input(f"Каталог входа [{base.input_root}]: ").strip() or base.input_root
    base.output_root = input(f"Папка выхода [{base.output_root}]: ").strip() or base.output_root
    base.report_path = input("Отчёт (пусто = pack_report.txt в выходе): ").strip() or base.report_path
    m = input(f"Макс. мужских YDD на пак [{base.max_male_per_pack}]: ").strip()
    if m:
        base.max_male_per_pack = int(m)
    f = input(f"Макс. женских YDD на пак [{base.max_female_per_pack}]: ").strip()
    if f:
        base.max_female_per_pack = int(f)
    dry = input("Dry run? y/N: ").strip().lower()
    base.dry_run = dry in ("y", "yes", "д", "да")
    ren = input("Epic rename? Y/n: ").strip().lower()
    base.apply_epic_rename = ren not in ("n", "no", "нет")
    sf = input("Сохранить настройки в JSON [Enter = пропустить]: ").strip()
    if sf:
        base.save(Path(sf))
    return base


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="GTA V clothes YDD/YTD packer")
    p.add_argument("--input", "-i", help="Каталог со сканом YDD/YTD")
    p.add_argument("--output", "-o", help="Выходная папка для pack_001 …")
    p.add_argument("--report", "-r", help="Файл отчёта")
    p.add_argument("--max-male", type=int, help="Макс. мужских YDD на пак")
    p.add_argument("--max-female", type=int, help="Макс. женских YDD на пак")
    p.add_argument("--dry-run", action="store_true", help="Только анализ")
    p.add_argument("--no-rename", action="store_true", help="Не применять epic rename")
    p.add_argument("--settings", type=str, help="JSON с настройками (частичный)")
    p.add_argument("--menu", action="store_true", help="Интерактивное меню")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    ns = _build_argparser().parse_args(argv)
    s = Settings()

    if ns.settings:
        data = json.loads(Path(ns.settings).read_text(encoding="utf-8"))
        s = Settings.from_dict(data)

    if ns.menu or (not ns.input and not ns.output and not ns.settings):
        s = _menu(s)

    if ns.input:
        s.input_root = ns.input
    if ns.output:
        s.output_root = ns.output
    if ns.report:
        s.report_path = ns.report
    if ns.max_male is not None:
        s.max_male_per_pack = ns.max_male
    if ns.max_female is not None:
        s.max_female_per_pack = ns.max_female
    if ns.dry_run:
        s.dry_run = True
    if ns.no_rename:
        s.apply_epic_rename = False

    if not s.input_root or not s.output_root:
        print("Укажите --input и --output или используйте --menu.", file=sys.stderr)
        return 2

    if not s.report_path and s.output_root:
        s.report_path = str(Path(s.output_root) / "pack_report.txt")

    for line in run_pack(s):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
