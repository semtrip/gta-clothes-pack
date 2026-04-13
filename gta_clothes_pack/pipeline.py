from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from fivefury.ytd import read_ytd

from .classify import classify_gender, classify_slot, normalize_slug_for_filename
from .config import Settings
from .matcher import build_ytd_index, match_one_ydd
from .rename_epic import build_epic_ydd_name, build_epic_ytd_name, patch_ydd_raw, rewrite_ytd_with_mapping
from .ydd_parse import collect_strings_for_heuristics, parse_ydd_file


def _prog(msg: str) -> None:
    print(msg, flush=True)


@dataclass
class YtdJob:
    path: Path
    new_stem: str
    texture_map: dict[str, str]


@dataclass
class ItemRecord:
    ydd_path: Path
    rel_posix: str
    gender: str
    kind: str
    slot_slug: str
    epic_number: int
    ytd_jobs: list[YtdJob] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


@dataclass
class PipelineState:
    items: list[ItemRecord] = field(default_factory=list)
    orphan_ytd: list[Path] = field(default_factory=list)


def _rel(root: Path, p: Path) -> str:
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return p.as_posix()


def _build_epic_maps(
    rec: ItemRecord,
    ytd_paths: list[Path],
    settings: Settings,
) -> None:
    """Fill per-YTD jobs for epic rename."""
    g_short = "m" if rec.gender == "male" else ("f" if rec.gender == "female" else "x")
    if g_short not in ("m", "f") or not settings.apply_epic_rename:
        for p in ytd_paths:
            rec.ytd_jobs.append(YtdJob(path=p, new_stem=p.stem, texture_map={}))
        return

    kind = rec.kind if rec.kind != "unknown" else "cloth"

    tex_counter = 0
    for ytd_p in ytd_paths:
        tex_counter += 1
        new_stem = build_epic_ytd_name(
            kind,
            g_short,
            rec.slot_slug,
            rec.epic_number,
            tex_counter,
            number_width=settings.epic_number_width,
            tex_width=settings.texture_index_width,
        )
        tex_map: dict[str, str] = {}
        try:
            ytd = read_ytd(ytd_p)
            names = [t.name for t in ytd.textures]
        except Exception:
            names = []
        if len(names) <= 1:
            for tn in names:
                tex_map[tn] = new_stem
        else:
            for i, tn in enumerate(names, start=1):
                tex_map[tn] = f"{new_stem}_{i:02d}"
        rec.ytd_jobs.append(YtdJob(path=ytd_p, new_stem=new_stem, texture_map=tex_map))


def analyze_input(root: Path, settings: Settings) -> PipelineState:
    state = PipelineState()
    ytd_glob = list(root.rglob("*.ytd"))
    ydd_glob = list(root.rglob("*.ydd"))
    _prog(f"Найдено файлов: {len(ydd_glob)} .ydd, {len(ytd_glob)} .ytd")
    _prog("Индексация YTD (чтение всех словарей текстур, может занять минуты)...")
    ytd_entries = build_ytd_index(root)
    _prog(f"  индекс YTD готов: {len(ytd_entries)} файлов")
    ydd_paths = sorted(ydd_glob)
    used_ytd: set[Path] = set()

    counter = 0
    total_ydd = len(ydd_paths)
    for ydd_path in ydd_paths:
        counter += 1
        if counter == 1 or counter % 25 == 0 or counter == total_ydd:
            _prog(f"  разбор YDD {counter}/{total_ydd}...")
        rel = _rel(root, ydd_path)
        pr = parse_ydd_file(ydd_path)
        blob = "\n".join(
            pr.drawable_name_strings + [str(ydd_path)] + collect_strings_for_heuristics(ydd_path)
        )
        gender = classify_gender(blob, rel, settings)
        kind, slot, _hint = classify_slot(pr.drawable_name_strings + list(pr.texture_names), settings)
        slot_slug = normalize_slug_for_filename(slot)

        m = match_one_ydd(ydd_path, ytd_entries)
        ytd_list = list(dict.fromkeys(m.ytd_paths))
        for p in ytd_list:
            used_ytd.add(p.resolve())

        rec = ItemRecord(
            ydd_path=ydd_path,
            rel_posix=rel,
            gender=gender,
            kind=kind,
            slot_slug=slot_slug,
            epic_number=counter,
        )
        if m.parse.errors:
            rec.issues.extend(m.parse.errors)
        if m.missing_textures:
            rec.issues.append("missing_textures:" + ",".join(m.missing_textures[:8]))
        if m.ambiguous_textures:
            rec.issues.append("ambiguous_textures:" + ",".join(m.ambiguous_textures[:8]))
        if gender == "unknown":
            rec.issues.append("unknown_gender")
        if kind == "unknown" or slot_slug == "unknown":
            rec.issues.append("unknown_slot")

        _build_epic_maps(rec, ytd_list, settings)
        state.items.append(rec)

    for ent in ytd_entries:
        if ent.path.resolve() not in used_ytd and not ent.errors:
            state.orphan_ytd.append(ent.path)

    return state


def _pack_bins(
    items: list[ItemRecord],
    settings: Settings,
) -> list[list[ItemRecord]]:
    males = [i for i in items if i.gender == "male"]
    females = [i for i in items if i.gender == "female"]
    others = [i for i in items if i.gender not in ("male", "female")]

    bins: list[list[ItemRecord]] = []
    mi, fi = 0, 0
    while mi < len(males) or fi < len(females):
        chunk: list[ItemRecord] = []
        cap_m = settings.max_male_per_pack
        cap_f = settings.max_female_per_pack
        while cap_m > 0 and mi < len(males):
            chunk.append(males[mi])
            mi += 1
            cap_m -= 1
        while cap_f > 0 and fi < len(females):
            chunk.append(females[fi])
            fi += 1
            cap_f -= 1
        if chunk:
            bins.append(chunk)
    if others:
        bins.append(others)
    return bins


def _ydd_patch_map(rec: ItemRecord) -> dict[str, str]:
    m: dict[str, str] = {}
    for job in rec.ytd_jobs:
        m.update(job.texture_map)
        m[job.path.stem] = job.new_stem
    return m


def run_pack(settings: Settings) -> list[str]:
    root = Path(settings.input_root).resolve()
    out = Path(settings.output_root).resolve()
    if not root.is_dir():
        return [f"Input not a directory: {root}"]

    _prog("Анализ каталога (при большом наборе файлов ожидайте, не закрывайте окно)...")
    state = analyze_input(root, settings)
    bins = _pack_bins(state.items, settings)

    if settings.dry_run:
        return [
            f"dry_run: packs={len(bins)} items={len(state.items)} orphan_ytd={len(state.orphan_ytd)}",
        ]

    out.mkdir(parents=True, exist_ok=True)
    log_lines: list[str] = []
    _prog(f"Запись паков в {out} ...")

    for bi, bin_items in enumerate(bins, start=1):
        pack_dir = out / f"pack_{bi:03d}"
        pack_dir.mkdir(parents=True, exist_ok=True)
        _prog(f"  pack_{bi:03d}: {len(bin_items)} YDD")

        for rec in bin_items:
            patch_map = _ydd_patch_map(rec)
            g_short = "m" if rec.gender == "male" else ("f" if rec.gender == "female" else "x")

            if settings.apply_epic_rename and g_short in ("m", "f"):
                kind = rec.kind if rec.kind != "unknown" else "cloth"
                ydd_name = (
                    build_epic_ydd_name(
                        kind,
                        g_short,
                        rec.slot_slug,
                        rec.epic_number,
                        number_width=settings.epic_number_width,
                    )
                    + ".ydd"
                )
                dst_ydd = pack_dir / ydd_name
                if patch_map:
                    patch_ydd_raw(rec.ydd_path, patch_map, dst_ydd)
                else:
                    shutil.copy2(rec.ydd_path, dst_ydd)
            else:
                dst_ydd = pack_dir / rec.ydd_path.name
                shutil.copy2(rec.ydd_path, dst_ydd)

            for job in rec.ytd_jobs:
                if settings.apply_epic_rename and rec.gender in ("male", "female"):
                    dst_ytd = pack_dir / f"{job.new_stem}.ytd"
                    if job.texture_map:
                        try:
                            rewrite_ytd_with_mapping(job.path, job.texture_map, dst_ytd)
                        except Exception as e:
                            log_lines.append(f"ytd_fail {job.path}: {e}")
                            shutil.copy2(job.path, dst_ytd)
                    else:
                        shutil.copy2(job.path, dst_ytd)
                else:
                    shutil.copy2(job.path, pack_dir / job.path.name)

    rep = Path(settings.report_path) if settings.report_path else None
    if rep:
        rep.parent.mkdir(parents=True, exist_ok=True)
        rep.write_text(
            "\n".join(_report_lines(state, bins)),
            encoding="utf-8",
        )
    log_lines.append(f"done: {len(bins)} packs -> {out}")
    return log_lines


def _report_lines(state: PipelineState, bins: list[list[ItemRecord]]) -> list[str]:
    lines = [
        f"packs={len(bins)}",
        f"items={len(state.items)}",
        f"orphan_ytd={len(state.orphan_ytd)}",
    ]
    for p in state.orphan_ytd[:200]:
        lines.append(f"orphan:{p.as_posix()}")
    for it in state.items:
        if it.issues:
            lines.append(f"issues:{it.rel_posix}:{'|'.join(it.issues)}")
    return lines
