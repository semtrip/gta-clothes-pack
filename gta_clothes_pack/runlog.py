from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from typing import TextIO


class RunLog:
    """Пишет в консоль и в файл (весь прогресс работы)."""

    def __init__(self, log_file: Path | None) -> None:
        self._path = log_file
        self._fp: TextIO | None = None
        self._lock = threading.Lock()
        if log_file is not None:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            self._fp = open(log_file, "w", encoding="utf-8", buffering=1)

    def close(self) -> None:
        with self._lock:
            if self._fp is not None:
                self._fp.close()
                self._fp = None

    def log(self, message: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        with self._lock:
            print(line, flush=True)
            if self._fp is not None:
                self._fp.write(line + "\n")
                self._fp.flush()

    def __enter__(self) -> RunLog:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def default_log_path(output_root: str | Path, report_path: str | Path | None) -> Path:
    """Рядом с отчётом или в output_root."""
    if report_path:
        p = Path(report_path)
        return p.parent / (p.stem + "_run.log")
    return Path(output_root) / "pack_run.log"
