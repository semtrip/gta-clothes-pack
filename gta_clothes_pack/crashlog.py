from __future__ import annotations

import io
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from . import __version__


def _is_frozen_exe() -> bool:
    return bool(getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"))


def crash_log_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("TEMP") or str(Path.home())
    d = Path(base) / "gta-clothes-pack"
    d.mkdir(parents=True, exist_ok=True)
    return d


def crash_log_path() -> Path:
    return crash_log_dir() / "crash.log"


def format_crash_report(exc: BaseException, extra_lines: list[str] | None = None) -> str:
    buf = io.StringIO()
    buf.write(f"gta-clothes-pack {__version__}\n")
    buf.write(f"{datetime.now().isoformat(timespec='seconds')}\n")
    buf.write(f"executable: {sys.executable}\n")
    buf.write(f"argv: {sys.argv!r}\n")
    if extra_lines:
        for line in extra_lines:
            buf.write(line + "\n")
    buf.write("\n")
    traceback.print_exception(type(exc), exc, exc.__traceback__, file=buf)
    return buf.getvalue()


def write_crash_log(exc: BaseException, extra_lines: list[str] | None = None) -> Path:
    """Пишет полный traceback в %LOCALAPPDATA%\\gta-clothes-pack\\crash.log (дозапись)."""
    path = crash_log_path()
    text = format_crash_report(exc, extra_lines)
    sep = "\n" + ("=" * 72) + "\n"
    try:
        with open(path, "a", encoding="utf-8", errors="replace") as f:
            if f.tell() > 0:
                f.write(sep)
            f.write(text)
            f.flush()
    except OSError:
        alt = Path(os.environ.get("TEMP", ".")) / "gta-clothes-pack-crash.log"
        try:
            alt.write_text(text, encoding="utf-8", errors="replace")
            return alt
        except OSError:
            return path
    return path


def print_crash_notice(log_path: Path) -> None:
    print("", file=sys.stderr)
    print(f"Подробности ошибки записаны в файл:", file=sys.stderr)
    print(f"  {log_path}", file=sys.stderr)
    print("", file=sys.stderr)


def pause_if_frozen_exe() -> None:
    if not _is_frozen_exe():
        return
    try:
        input("Нажмите Enter, чтобы закрыть окно...")
    except (EOFError, KeyboardInterrupt):
        pass
