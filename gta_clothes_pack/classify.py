from __future__ import annotations

import re
from .config import Settings


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
    # jbib_000, hand_0, uppr^u — не цепляем «hand» из handmade
    return rest[0] in "_^" or rest[0].isdigit()


def classify_gender(text_blob: str, path_str: str, settings: Settings) -> str:
    m = settings.compiled_male()
    f = settings.compiled_female()
    blob = f"{text_blob}\n{path_str}"
    has_m = bool(m.search(blob))
    has_f = bool(f.search(blob))
    if has_m and not has_f:
        return "male"
    if has_f and not has_m:
        return "female"
    if has_m and has_f:
        return "unknown"
    return "unknown"


def classify_slot(strings: list[str], settings: Settings, extra_hay: str = "") -> tuple[str, str, str]:
    """Return (kind, slot_slug, hint)."""
    hay = " ".join(strings).lower()
    if extra_hay:
        hay = f"{hay}\n{extra_hay.lower()}"
    rules = _merge_rules(settings)
    ordered = sorted(rules, key=lambda x: -len(x[0]))
    for prefix, kind, slug in ordered:
        if prefix in hay:
            return kind, slug, prefix
    # Токены: часть модов даёт только имя файла без явного префикса в drawable.
    for tok in re.findall(r"[a-z]{3,}", hay):
        for prefix, kind, slug in ordered:
            if _token_matches_prefix(tok, prefix):
                return kind, slug, prefix
    return "unknown", "unknown", ""


def normalize_slug_for_filename(slug: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", slug.lower()).strip("_")
    return s or "unknown"
