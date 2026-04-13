"""
Экспорт бинарных .ymt в .ymt.xml через MetaTool из gta-toolkit (RageLib).

MetaTool пишет выходной файл как <путь_к_ymt>.xml (например foo.ymt → foo.ymt.xml).
Требуется собранный MetaTool.exe и списки имён в ресурсах сборки.

Переменные окружения:
  GTA_CLOTHES_META_TOOL — полный путь к MetaTool.exe
  META_TOOL_EXE — то же (совместимость)

Сборка PyInstaller --onefile: если в .spec вшита папка bin/Release (или Debug) MetaTool как
datas → metatool/, resolve_meta_tool_exe находит MetaTool внутри sys._MEIPASS (на диске один gta-clothes-pack.exe).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    """Корень репозитория (родитель каталога gta_clothes_pack)."""
    return Path(__file__).resolve().parent.parent


def resolve_meta_tool_exe(explicit: Path | None = None) -> Path | None:
    """Путь к MetaTool.exe: аргумент → env → сборка из submodule tools/gta-toolkit → cwd."""
    if explicit is not None:
        if explicit.is_file():
            return explicit.resolve()
        return None
    for key in ("GTA_CLOTHES_META_TOOL", "META_TOOL_EXE"):
        v = os.environ.get(key, "").strip()
        if v:
            p = Path(v)
            if p.is_file():
                return p.resolve()
    # PyInstaller --onefile: каталог metatool/ из gta-clothes-pack.spec (вся bin/Release или bin/Debug)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        me = Path(sys._MEIPASS)
        for p in (me / "metatool" / "MetaTool.exe", me / "MetaTool.exe"):
            if p.is_file():
                return p.resolve()
    root = _repo_root()
    for cand in (
        root / "tools" / "MetaTool" / "bin" / "Release" / "MetaTool.exe",
        root / "tools" / "MetaTool" / "bin" / "Debug" / "MetaTool.exe",
        root / "tools" / "gta-toolkit" / "Tools" / "MetaTool" / "bin" / "Release" / "MetaTool.exe",
        root / "tools" / "gta-toolkit" / "Tools" / "MetaTool" / "bin" / "Debug" / "MetaTool.exe",
        root / "tools" / "metatool" / "MetaTool.exe",
    ):
        if cand.is_file():
            return cand.resolve()
    for rel in (
        "MetaTool.exe",
        Path("Tools") / "MetaTool" / "bin" / "Release" / "MetaTool.exe",
        Path("Tools") / "MetaTool" / "bin" / "Debug" / "MetaTool.exe",
    ):
        p = Path(rel)
        if p.is_file():
            return p.resolve()
    return None


def export_one_ymt(ymt_path: Path, meta_tool: Path, *, timeout_s: float = 120) -> Path:
    """
    Запускает MetaTool с одним аргументом — путём к .ymt.
    Возвращает путь к созданному .ymt.xml.
    """
    ymt_path = ymt_path.resolve()
    out = Path(str(ymt_path) + ".xml")
    r = subprocess.run(
        [str(meta_tool), str(ymt_path)],
        capture_output=True,
        text=True,
        timeout=timeout_s,
        cwd=str(meta_tool.parent),
    )
    if r.returncode != 0:
        err = (r.stderr or r.stdout or "").strip() or f"exit {r.returncode}"
        raise RuntimeError(err)
    if not out.is_file():
        raise FileNotFoundError(f"MetaTool не создал файл: {out}")
    return out


def export_ymt_tree(
    root: Path,
    meta_tool: Path,
    *,
    force: bool = False,
) -> tuple[int, int, list[str]]:
    """
    Рекурсивно все *.ymt (не считая уже *.ymt.xml как вход — таких нет).
    Если рядом уже есть .ymt.xml и force=False — пропуск.
    Возвращает (успех, ошибки, строки лога).
    """
    root = root.resolve()
    log: list[str] = []
    ok, fail = 0, 0
    for ymt in sorted(root.rglob("*.ymt")):
        out = Path(str(ymt) + ".xml")
        if out.exists() and not force:
            log.append(f"skip (есть XML): {ymt}")
            continue
        try:
            export_one_ymt(ymt, meta_tool)
            ok += 1
            log.append(f"ok: {ymt} -> {out}")
        except Exception as e:
            fail += 1
            log.append(f"err: {ymt}: {e}")
    return ok, fail, log
