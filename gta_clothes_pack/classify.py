from __future__ import annotations

import re

from .config import Settings
from .durty_names import infer_gender_from_filename_stem, infer_gender_from_path_segments
from .freemode_identity import (
    infer_gender_from_drawable_names,
    slot_from_caret_freemode_only,
    slot_from_drawable_identity,
)
from .ymt_meta import YmtMetaResolution, gender_from_binary_flags
from .ydd_parse import YddParseResult


_PREFIX_TO_SLOT: list[tuple[str, str, str]] = [
    ("p_head", "prop", "hats"),
    ("p_eyes", "prop", "glasses"),
    ("p_ears", "prop", "ears"),
    ("p_wrist", "prop", "watches"),
    ("p_bracelet", "prop", "bracelets"),
    ("p_mouth", "prop", "mouth"),
    ("p_lhand", "prop", "hands"),
    ("p_rhand", "prop", "hands"),
    ("p_lwrist", "prop", "watches"),
    ("p_rwrist", "prop", "watches"),
    ("p_legs", "prop", "legs"),
    ("p_lfinger", "prop", "rings"),
    ("p_rfinger", "prop", "rings"),
    ("p_finger", "prop", "rings"),
    ("berd", "cloth", "masks"),
    ("hair_d", "cloth", "hair_styles"),
    ("hairs", "cloth", "hair_styles"),
    ("hair", "cloth", "hair_styles"),
    ("jbib", "cloth", "tops"),
    ("uppr", "cloth", "tops"),
    ("lowr", "cloth", "legs"),
    ("feet", "cloth", "shoes"),
    ("hand", "cloth", "accessories"),
    ("teef", "cloth", "undershirts"),
    ("task", "cloth", "bags_and_parachutes"),
    ("decl", "cloth", "decals"),
    ("accs", "cloth", "accessories"),
]


def _prefix_matches_hay(prefix: str, hay: str) -> bool:
    """Совпадение префикса без ложных вхождений вроде «hair» внутри «chair»."""
    return bool(
        re.search(rf"(?<![a-z0-9]){re.escape(prefix)}(?![a-z0-9])", hay, flags=re.IGNORECASE)
    )


def _merge_rules(settings: Settings) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for row in settings.prefix_rules:
        if len(row) >= 3:
            out.append((row[0].lower(), row[1], row[2]))
    if not out:
        out = [(a, b, c) for a, b, c in _PREFIX_TO_SLOT]
    return out


def _token_matches_prefix(tok: str, prefix: str) -> bool:
    if tok == prefix:
        return True
    if not tok.startswith(prefix):
        return False
    rest = tok[len(prefix) :]
    if not rest:
        return True
    return rest[0] in "_^" or rest[0].isdigit()


def classify_gender_from_ydd(
    pr: YddParseResult,
    text_blob: str,
    settings: Settings,
    rel_posix: str = "",
    ymt_folder_gender: str | None = None,
    ymt_meta: YmtMetaResolution | None = None,
    ydd_stem: str = "",
) -> str:
    """
    Пол.

    strict_engine_identity (по умолчанию True):
      только литералы mp_*_freemode_01 в сыром YDD и drawable с «mp_*_freemode_01^…».
      Дополнительно: при infer_gender_from_filename — пол по stem имени файла (jbib_000_m_u и т.п.)
      до перехода к строгому unknown.

    strict_engine_identity == False (устаревший режим):
      эвристики по тексту, ymt, пути — см. настройки.
    """
    g_draw = infer_gender_from_drawable_names(
        pr.drawable_name_strings,
        caret_only=settings.strict_engine_identity,
    )
    if g_draw is not None:
        return g_draw

    if pr.binary_has_mp_m_freemode_01 and not pr.binary_has_mp_f_freemode_01:
        return "male"
    if pr.binary_has_mp_f_freemode_01 and not pr.binary_has_mp_m_freemode_01:
        return "female"
    if pr.binary_has_mp_m_freemode_01 and pr.binary_has_mp_f_freemode_01:
        return "unknown"

    if ymt_meta is not None and getattr(settings, "use_ymt_meta", True):
        if ymt_meta.xml_gender in ("male", "female"):
            return ymt_meta.xml_gender
        g_ymt = gender_from_binary_flags(ymt_meta.binary_m, ymt_meta.binary_f)
        if g_ymt in ("male", "female"):
            return g_ymt
        if g_ymt == "unknown":
            return "unknown"

    if getattr(settings, "infer_gender_from_filename", True) and ydd_stem:
        g_fn = infer_gender_from_filename_stem(ydd_stem)
        if g_fn in ("male", "female"):
            return g_fn

    if settings.strict_engine_identity:
        return "unknown"

    m = settings.compiled_male()
    f = settings.compiled_female()
    has_m = bool(m.search(text_blob))
    has_f = bool(f.search(text_blob))
    if has_m and not has_f:
        return "male"
    if has_f and not has_m:
        return "female"
    if has_m and has_f:
        return "unknown"
    if settings.use_ymt_folder_for_gender and ymt_folder_gender in ("male", "female"):
        return ymt_folder_gender
    if settings.infer_gender_from_path and rel_posix:
        g = infer_gender_from_path_segments(rel_posix)
        if g:
            return g
    return "unknown"


def classify_slot_from_ydd_metadata(
    pr: YddParseResult,
    heuristics_ascii: list[str],
    settings: Settings,
    ymt_meta: YmtMetaResolution | None = None,
) -> tuple[str, str, str]:
    """
    Компонент (слот).

    strict_engine_identity: только «mp_*_freemode_01^jbib_…» и т.п.; иначе unknown.
    Иначе — прежние эвристики по строкам (небезопасно при demonic_003 / tattoo).
    """
    rules = _merge_rules(settings)
    if settings.strict_engine_identity:
        if pr.drawable_name_strings:
            hit = slot_from_caret_freemode_only(pr.drawable_name_strings, rules)
            if hit is not None:
                return hit[0], hit[1], hit[2]
        if (
            ymt_meta is not None
            and ymt_meta.xml_slot is not None
            and getattr(settings, "use_ymt_meta", True)
            and getattr(settings, "use_ymt_xml_meta", True)
        ):
            k, s, h = ymt_meta.xml_slot
            return k, s, h
        return "unknown", "unknown", ""

    if pr.drawable_name_strings:
        hit = slot_from_drawable_identity(pr.drawable_name_strings, rules)
        if hit is not None:
            return hit[0], hit[1], hit[2]
        r = classify_slot(pr.drawable_name_strings, settings)
        if r[0] != "unknown":
            return r
    if (
        ymt_meta is not None
        and ymt_meta.xml_slot is not None
        and getattr(settings, "use_ymt_meta", True)
        and getattr(settings, "use_ymt_xml_meta", True)
    ):
        k, s, h = ymt_meta.xml_slot
        return k, s, h
    tier2: list[str] = []
    tier2.extend(pr.drawable_name_strings)
    tier2.extend(sorted(pr.texture_names))
    tier2.extend(pr.shader_meta_strings)
    r = classify_slot(tier2, settings)
    if r[0] != "unknown":
        return r
    return classify_slot(pr.file_metadata_lines(heuristics_ascii), settings)


def classify_slot(strings: list[str], settings: Settings) -> tuple[str, str, str]:
    """Return (kind, slot_slug, hint)."""
    hay = " ".join(strings).lower()
    rules = _merge_rules(settings)
    ordered = sorted(rules, key=lambda x: -len(x[0]))
    for prefix, kind, slug in ordered:
        if _prefix_matches_hay(prefix, hay):
            return kind, slug, prefix
    for tok in re.findall(r"[a-z]{3,}", hay):
        for prefix, kind, slug in ordered:
            if _token_matches_prefix(tok, prefix):
                return kind, slug, prefix
    return "unknown", "unknown", ""


def normalize_slug_for_filename(slug: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", slug.lower()).strip("_")
    return s or "unknown"
