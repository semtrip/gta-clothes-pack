"""Точка входа для PyInstaller (один файл .exe)."""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

# Сразу после распаковки onefile — меньше буферизации stdout в консоли
os.environ.setdefault("PYTHONUNBUFFERED", "1")


def _write_import_crash(text: str) -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", "."))) / "gta-clothes-pack"
    base.mkdir(parents=True, exist_ok=True)
    p = base / "crash.log"
    sep = "\n" + ("=" * 72) + "\n"
    try:
        with open(p, "a", encoding="utf-8", errors="replace") as f:
            if f.tell() > 0:
                f.write(sep)
            f.write(text)
            f.flush()
    except OSError:
        p = Path(os.environ.get("TEMP", ".")) / "gta-clothes-pack-crash.log"
        p.write_text(text, encoding="utf-8", errors="replace")
    return p


if __name__ == "__main__":
    try:
        # Before any ``fivefury`` import: pure-Python jenk_hash when frozen (see fivefury_hashing_shim).
        from gta_clothes_pack.fivefury_hashing_shim import install_fivefury_hashing_shim

        install_fivefury_hashing_shim()
        from gta_clothes_pack.cli import main
    except Exception as e:
        text = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        try:
            p = _write_import_crash(text)
            print(f"Подробности записаны в:\n  {p}", file=sys.stderr, flush=True)
        except Exception:
            traceback.print_exc()
        try:
            input("Нажмите Enter, чтобы закрыть окно...")
        except (EOFError, KeyboardInterrupt):
            pass
        raise SystemExit(1)

    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        try:
            from gta_clothes_pack.crashlog import pause_if_frozen_exe, print_crash_notice, write_crash_log

            log_path = write_crash_log(e, extra_lines=["[entry_exe] необработанное исключение после main"])
            print_crash_notice(log_path)
            traceback.print_exc()
            pause_if_frozen_exe()
        except Exception:
            p = _write_import_crash(traceback.format_exc())
            print(f"Подробности записаны в:\n  {p}", file=sys.stderr, flush=True)
            traceback.print_exc()
            try:
                input("Нажмите Enter, чтобы закрыть окно...")
            except (EOFError, KeyboardInterrupt):
                pass
        raise SystemExit(1)
