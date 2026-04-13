from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

from .config import Settings
from .crashlog import pause_after_success_if_frozen_exe, pause_if_frozen_exe, print_crash_notice, write_crash_log
from .pipeline import run_pack
from .ymt_export import export_ymt_tree, resolve_meta_tool_exe


def _configure_stdio() -> None:
    """В .exe stdout часто полностью буферизован — без flush кажется «зависание»."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", line_buffering=True)
        except Exception:
            try:
                stream.reconfigure(line_buffering=True)
            except Exception:
                pass


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
    dry = input(
        "Только анализ без записи pack (как --dry-run)? y/N: "
    ).strip().lower()
    base.dry_run = dry in ("y", "yes", "д", "да")
    ren = input("Epic rename? Y/n: ").strip().lower()
    base.apply_epic_rename = ren not in ("n", "no", "нет")
    sf = input("Сохранить настройки в JSON [Enter = пропустить]: ").strip()
    if sf:
        base.save(Path(sf))
    return base


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="GTA V clothes YDD/YTD packer",
        epilog=(
            "Экспорт меты: gta-clothes-pack export-ymt-xml -i КАТАЛОГ "
            "(MetaTool из submodule tools/gta-toolkit после scripts\\build_meta_tool.ps1)"
        ),
    )
    p.add_argument("--input", "-i", help="Каталог со сканом YDD/YTD")
    p.add_argument("--output", "-o", help="Выходная папка для pack_001 …")
    p.add_argument("--report", "-r", help="Файл отчёта")
    p.add_argument("--max-male", type=int, help="Макс. мужских YDD на пак")
    p.add_argument("--max-female", type=int, help="Макс. женских YDD на пак")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Пробный прогон: полный анализ каталога, журнал и отчёт по возможности; "
            "папки pack_* не создаются, YDD/YTD не копируются и не переименовываются. "
            "Без этого флага выполняется реальная упаковка в --output"
        ),
    )
    p.add_argument("--no-rename", action="store_true", help="Не применять epic rename")
    p.add_argument("--settings", type=str, help="JSON с настройками (частичный)")
    p.add_argument("--menu", action="store_true", help="Интерактивное меню")
    p.add_argument(
        "--workers",
        type=int,
        default=0,
        metavar="N",
        help="Число потоков для YDD (0 = авто)",
    )
    p.add_argument(
        "--log",
        type=str,
        default="",
        metavar="FILE",
        help="Журнал прогресса (пусто = pack_run.log в выходе или рядом с отчётом)",
    )
    p.add_argument(
        "--no-pause",
        action="store_true",
        help="Не ждать Enter в конце (для сценариев из .bat / CI; в .exe по умолчанию пауза)",
    )
    p.add_argument(
        "--no-stem-pair",
        action="store_true",
        help="Не подключать foo.ytd к foo.ydd по имени файла (stem без расширения)",
    )
    p.add_argument(
        "--auto-export-ymt-xml",
        action="store_true",
        help="Перед упаковкой экспортировать все .ymt→.ymt.xml (нужен --meta-tool или meta_tool_exe в JSON)",
    )
    p.add_argument(
        "--meta-tool",
        default="",
        metavar="EXE",
        help="Путь к MetaTool.exe для --auto-export-ymt-xml",
    )
    return p


def _run_export_ymt_xml(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        prog="gta-clothes-pack export-ymt-xml",
        description="Экспорт бинарных .ymt в .ymt.xml через MetaTool (RageLib, репозиторий indilo53/gta-toolkit).",
    )
    p.add_argument(
        "-i",
        "--input",
        required=True,
        help="Каталог рекурсивного поиска *.ymt",
    )
    p.add_argument(
        "--meta-tool",
        default="",
        metavar="EXE",
        help="Путь к MetaTool.exe (иначе GTA_CLOTHES_META_TOOL или META_TOOL_EXE)",
    )
    p.add_argument(
        "--settings",
        type=str,
        default="",
        metavar="FILE",
        help="JSON настроек: поле meta_tool_exe, если --meta-tool не задан",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Перезаписать уже существующие рядом .ymt.xml",
    )
    ns = p.parse_args(argv)
    root = Path(ns.input).resolve()
    if not root.is_dir():
        print(f"Не каталог: {root}", file=sys.stderr)
        return 2
    meta_arg = ns.meta_tool.strip()
    if not meta_arg and ns.settings.strip():
        data = json.loads(Path(ns.settings).read_text(encoding="utf-8"))
        meta_arg = (data.get("meta_tool_exe") or "").strip()
    explicit = Path(meta_arg) if meta_arg else None
    meta = resolve_meta_tool_exe(explicit)
    if not meta:
        print(
            "Не найден MetaTool.exe. В репозитории: submodule tools/gta-toolkit, затем\n"
            "  powershell -ExecutionPolicy Bypass -File scripts\\build_meta_tool.ps1\n"
            "Или укажите --meta-tool / переменную GTA_CLOTHES_META_TOOL.",
            file=sys.stderr,
        )
        return 2
    ok, fail, lines = export_ymt_tree(root, meta, force=ns.force)
    for line in lines:
        print(line, flush=True)
    print(f"\nЭкспорт завершён: успешно {ok}, ошибок {fail}.", flush=True)
    return 0 if fail == 0 else 1


def _run_impl(argv: list[str] | None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] == "export-ymt-xml":
        return _run_export_ymt_xml(argv[1:])
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
    if ns.workers is not None and ns.workers > 0:
        s.worker_threads = ns.workers
    if ns.log:
        s.log_path = ns.log
    if ns.no_stem_pair:
        s.pair_ytd_same_stem_as_ydd = False
    if ns.auto_export_ymt_xml:
        s.auto_export_ymt_xml = True
    if ns.meta_tool.strip():
        s.meta_tool_exe = ns.meta_tool.strip()

    if not s.input_root or not s.output_root:
        print("Укажите --input и --output или используйте --menu.", file=sys.stderr)
        return 2

    if not s.report_path and s.output_root:
        s.report_path = str(Path(s.output_root) / "pack_report.txt")

    print(
        "\nЗапуск обработки (большие каталоги обрабатываются долго — смотрите строки прогресса ниже).\n",
        flush=True,
    )

    for line in run_pack(s):
        print(line, flush=True)
    pause_after_success_if_frozen_exe(skip=ns.no_pause)
    return 0


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    try:
        return _run_impl(argv)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\nПрервано пользователем.", file=sys.stderr, flush=True)
        return 130
    except Exception as e:
        log_path = write_crash_log(e)
        print_crash_notice(log_path)
        traceback.print_exc()
        pause_if_frozen_exe()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
