from __future__ import annotations

import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from fivefury.ytd import read_ytd

from .classify import classify_gender_from_ydd, classify_slot_from_ydd_metadata, normalize_slug_for_filename
from .config import Settings
from .durty_names import durty_kind_slot, parse_ydd_filename_durty, stream_drawable_stem
from .matcher import build_ytd_index, match_from_parse
from .rename_epic import build_epic_ydd_name, build_epic_ytd_name, patch_ydd_raw, rewrite_ytd_with_mapping
from .runlog import RunLog, default_log_path
from .ydd_parse import collect_strings_for_heuristics, parse_ydd_file
from .ymt_hints import YmtGenderContext, gender_hint_for_ydd_path
from .ymt_export import export_ymt_tree, resolve_meta_tool_exe
from .ymt_meta import resolve_ymt_meta_for_ydd
from .ytd_index import TextureIndex


def _resolve_workers(settings: Settings) -> int:
    if settings.worker_threads and settings.worker_threads > 0:
        return settings.worker_threads
    cpu = os.cpu_count() or 4
    return max(2, min(32, cpu * 2))


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
    matched_ytd_paths: list[Path] = field(default_factory=list)
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
    if not settings.apply_epic_rename:
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


def _process_one_ydd(
    args: tuple[int, Path, Path, Settings, TextureIndex, YmtGenderContext],
) -> ItemRecord:
    """Поток: один YDD — разбор + матч по общему индексу текстур (только чтение)."""
    epic_number, ydd_path, root, settings, tex_index, ymt_ctx = args
    rel = _rel(root, ydd_path)
    pr = parse_ydd_file(ydd_path)
    heur = collect_strings_for_heuristics(ydd_path)
    text_blob = "\n".join(pr.file_metadata_lines(heur))
    ymt_meta = resolve_ymt_meta_for_ydd(ydd_path, root, pr.drawable_name_strings, settings)
    ymt_g = (
        gender_hint_for_ydd_path(
            ydd_path,
            root,
            ymt_stem_map=ymt_ctx.stem_map,
            ymt_folder_index=ymt_ctx.folder_index,
        )
        if settings.use_ymt_folder_for_gender and not settings.strict_engine_identity
        else None
    )
    gender = classify_gender_from_ydd(
        pr,
        text_blob,
        settings,
        rel_posix=rel,
        ymt_folder_gender=ymt_g,
        ymt_meta=ymt_meta,
        ydd_stem=ydd_path.stem,
    )
    kind, slot, _hint = classify_slot_from_ydd_metadata(pr, heur, settings, ymt_meta=ymt_meta)
    slot_norm = normalize_slug_for_filename(slot)
    slot_unresolved = slot_norm == "unknown"
    slot_slug = (
        normalize_slug_for_filename(settings.fallback_slot_slug)
        if slot_unresolved
        else slot_norm
    )

    # Имя файла в стиле Durty (jbib_000_u) — слот/kind без regex по произвольным строкам внутри YDD
    if settings.use_durty_filename_for_slot and slot_unresolved:
        dp_slot = parse_ydd_filename_durty(stream_drawable_stem(ydd_path.stem))
        if dp_slot and not dp_slot.is_variation:
            ks = durty_kind_slot(dp_slot)
            if ks:
                kind, slot_slug = ks[0], normalize_slug_for_filename(ks[1])
                slot_unresolved = False

    m = match_from_parse(ydd_path, pr, tex_index, settings)
    ytd_list = list(dict.fromkeys(m.ytd_paths))

    rec = ItemRecord(
        ydd_path=ydd_path,
        rel_posix=rel,
        gender=gender,
        kind=kind,
        slot_slug=slot_slug,
        epic_number=epic_number,
        matched_ytd_paths=ytd_list,
    )
    if m.parse.errors:
        rec.issues.extend(m.parse.errors)
    if m.missing_textures:
        rec.issues.append("missing_textures:" + ",".join(m.missing_textures[:8]))
    if m.ambiguous_textures:
        rec.issues.append("ambiguous_textures:" + ",".join(m.ambiguous_textures[:8]))
    if gender == "unknown":
        rec.issues.append("unknown_gender")
    if kind == "unknown" or slot_unresolved:
        rec.issues.append("unknown_slot")

    return rec


def analyze_input(root: Path, settings: Settings, log: RunLog) -> PipelineState:
    state = PipelineState()
    if getattr(settings, "auto_export_ymt_xml", False):
        mt = None
        if settings.meta_tool_exe.strip():
            mt = resolve_meta_tool_exe(Path(settings.meta_tool_exe))
        if mt is None:
            mt = resolve_meta_tool_exe(None)
        if mt is not None:
            log.log(f"auto_export_ymt_xml: MetaTool {mt}")
            ok, fail, lines = export_ymt_tree(root, mt, force=False)
            log.log(f"  экспорт .ymt→.ymt.xml: ok={ok}, ошибок={fail}")
            for line in lines[:40]:
                log.log(f"  {line}")
            if len(lines) > 40:
                log.log(f"  … ещё строк лога: {len(lines) - 40}")
        else:
            log.log(
                "auto_export_ymt_xml включён, но MetaTool.exe не найден "
                "(meta_tool_exe, GTA_CLOTHES_META_TOOL) — пропуск."
            )

    ytd_glob = list(root.rglob("*.ytd"))
    ydd_glob = list(root.rglob("*.ydd"))
    log.log(f"Найдено файлов: {len(ydd_glob)} .ydd, {len(ytd_glob)} .ytd")
    if settings.strict_engine_identity:
        log.log(
            "  strict_engine_identity: пол — литералы mp_*_freemode_01 в YDD, в бинарных .ymt в каталоге, "
            "drawable mp_*_freemode_01^… и при наличии — экспорт *.ymt.xml (CPedVariationInfo); "
            "слот — caret, затем разбор XML меты."
        )
    if getattr(settings, "infer_gender_from_filename", True):
        log.log(
            "  infer_gender_from_filename: запасной пол по stem имени .ydd (сегменты _m_/_f_, male/female, mp_m/mp_f…)."
        )
    n_ymt_xml = len(list(root.rglob("*.ymt.xml")))
    if settings.use_ymt_meta and n_ymt_xml:
        log.log(f"  Найдено {n_ymt_xml} файлов *.ymt.xml (CodeWalker / MetaToolkit) для разбора CPedVariationInfo.")
    log.log("Индексация YTD: чтение всех .ytd в память (словарь имён текстур)...")
    ytd_entries = build_ytd_index(root)
    tex_index = TextureIndex(ytd_entries)
    log.log(
        f"  индекс YTD готов: {len(ytd_entries)} файлов, "
        f"уникальных имён текстур в индексе: {tex_index.texture_key_count}"
    )
    if settings.pair_ytd_same_stem_as_ydd:
        log.log(
            "  матчинг YTD: по именам текстур в шейдерах + пара foo.ydd↔foo.ytd с тем же stem (если включено)."
        )
    else:
        log.log("  матчинг YTD: только по именам текстур (пара по stem отключена).")
    if settings.durty_cloth_texture_patterns:
        log.log(
            "  + Durty/altCloth: в той же папке что .ydd — шаблоны *_diff_*_*_uni/_whi.ytd и для пропов *_diff_*_*.ytd."
        )

    ymt_ctx = YmtGenderContext(stem_map={}, folder_index={})
    if settings.use_ymt_folder_for_gender and not settings.strict_engine_identity:
        ymt_ctx = YmtGenderContext.build(root)
        n_single = sum(1 for v in ymt_ctx.folder_index.values() if v is not None)
        log.log(
            f"  freemode: .ymt stem с полом {len(ymt_ctx.stem_map)}, "
            f"папок с одним полом по ymt {n_single} "
            f"(из {len(ymt_ctx.folder_index)} папок с mp_*_freemode_01*.ymt); "
            "пол также по именам папок mp_m_… / mp_f_… и совпадению папки со stem .ymt."
        )

    ydd_paths = sorted(ydd_glob)
    total_ydd = len(ydd_paths)
    workers = _resolve_workers(settings)
    log.log(f"Разбор и матч YDD: потоков={workers} (индекс YTD общий, только чтение)")

    tasks: list[tuple[int, Path, Path, Settings, TextureIndex, YmtGenderContext]] = [
        (i, p, root, settings, tex_index, ymt_ctx) for i, p in enumerate(ydd_paths, start=1)
    ]

    items_by_epic: dict[int, ItemRecord] = {}
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_process_one_ydd, t): t[0] for t in tasks}
        for fut in as_completed(futures):
            epic = futures[fut]
            rec = fut.result()
            items_by_epic[epic] = rec
            done += 1
            if done == 1 or done % 25 == 0 or done == total_ydd:
                log.log(f"  YDD обработано {done}/{total_ydd} (последний epic #{epic})")

    state.items = [items_by_epic[i] for i in range(1, total_ydd + 1)]

    used_ytd: set[Path] = set()
    for rec in state.items:
        for p in rec.matched_ytd_paths:
            used_ytd.add(p.resolve())

    log.log("Построение задач epic rename (чтение YTD для имён текстур)...")
    for rec in state.items:
        _build_epic_maps(rec, rec.matched_ytd_paths, settings)

    for ent in ytd_entries:
        if ent.path.resolve() not in used_ytd and not ent.errors:
            state.orphan_ytd.append(ent.path)

    log.log(
        f"Анализ завершён: записей {len(state.items)}, orphan YTD: {len(state.orphan_ytd)}"
    )
    return state


def _gender_counts(items: list[ItemRecord]) -> tuple[int, int, int]:
    males = sum(1 for i in items if i.gender == "male")
    females = sum(1 for i in items if i.gender == "female")
    unknown = sum(1 for i in items if i.gender not in ("male", "female"))
    return males, females, unknown


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

    log_path: Path | None
    if settings.log_path:
        log_path = Path(settings.log_path).resolve()
    else:
        log_path = default_log_path(out, settings.report_path or None)

    log_lines: list[str] = []
    with RunLog(log_path) as run_log:
        run_log.log("Анализ каталога (при большом наборе файлов ожидайте, не закрывайте окно)...")
        if log_path is not None:
            run_log.log(f"Журнал: {log_path}")
        state = analyze_input(root, settings, run_log)
        bins = _pack_bins(state.items, settings)
        gm, gf, gu = _gender_counts(state.items)
        run_log.log(
            f"Распределение YDD по полу: male={gm}, female={gf}, unknown={gu}. "
            f"В каждом паке до {settings.max_male_per_pack} male + до {settings.max_female_per_pack} female "
            "только среди распознанных male/female; все unknown — отдельным паком в конце."
        )

        if settings.dry_run:
            msg = (
                f"dry_run: packs={len(bins)} items={len(state.items)} "
                f"orphan_ytd={len(state.orphan_ytd)}"
            )
            run_log.log(msg)
            log_lines.append(msg)
            run_log.log(
                "Dry run завершён: папки pack_* не создавались, файлы не копировались. "
                "Запустите без --dry-run для упаковки."
            )
            return log_lines

        out.mkdir(parents=True, exist_ok=True)
        run_log.log(f"Запись паков в {out} ...")

        for bi, bin_items in enumerate(bins, start=1):
            pack_dir = out / f"pack_{bi:03d}"
            pack_dir.mkdir(parents=True, exist_ok=True)
            run_log.log(f"  pack_{bi:03d}: {len(bin_items)} YDD")

            for rec in bin_items:
                patch_map = _ydd_patch_map(rec)
                g_short = "m" if rec.gender == "male" else ("f" if rec.gender == "female" else "x")

                if settings.apply_epic_rename:
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
                    if settings.apply_epic_rename:
                        dst_ytd = pack_dir / f"{job.new_stem}.ytd"
                        if job.texture_map:
                            try:
                                rewrite_ytd_with_mapping(job.path, job.texture_map, dst_ytd)
                            except Exception as e:
                                err = f"ytd_fail {job.path}: {e}"
                                run_log.log(err)
                                log_lines.append(err)
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
            run_log.log(f"Отчёт: {rep}")

        done_msg = f"done: {len(bins)} packs -> {out}"
        run_log.log(done_msg)
        log_lines.append(done_msg)

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
