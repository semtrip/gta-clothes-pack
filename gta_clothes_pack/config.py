from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Settings:
    input_root: str = ""
    output_root: str = ""
    report_path: str = ""
    log_path: str = ""
    worker_threads: int = 0
    max_male_per_pack: int = 128
    max_female_per_pack: int = 128
    layout: str = "flat"  # flat | preserve
    duplicate_shared_ytd: bool = True
    dry_run: bool = False
    apply_epic_rename: bool = True
    epic_number_width: int = 3
    texture_index_width: int = 2
    # Только движок: литералы mp_*_freemode_01 в YDD и нотация mp_*_freemode_01^… в drawable; без имён файлов/папок/regex
    strict_engine_identity: bool = True
    # Если слот не распознан (нет префикса в drawable/пути), имя epic будет с этим slug вместо «unknown»
    fallback_slot_slug: str = "misc"
    # Запасной пол (если бинарные маркеры не сработали): подстроки в тексте из YDD, без якоря «начало строки»
    male_regex: str = r"(?i)mp_m_freemode_01|mp_m_freemode|(^|[\\/])m_|_m_|male"
    female_regex: str = r"(?i)mp_f_freemode_01|mp_f_freemode|(^|[\\/])f_|_f_|female"
    # Если у foo.ydd есть foo.ytd с тем же stem — подключать к паку (типичная пара модов)
    pair_ytd_same_stem_as_ydd: bool = True
    # Как altClothTool/Durty: jbib_000_u.ydd + jbib_diff_000_a_uni.ytd в той же папке
    durty_cloth_texture_patterns: bool = True
    # Если имя .ydd разбирается как jbib_000_u / p_head_000 — подставить kind/slot по префиксу
    use_durty_filename_for_slot: bool = True
    # Подсказка пола по папкам (имена файлов часто ошибочны; по умолчанию выключено)
    infer_gender_from_path: bool = False
    # Пол из stream: имена папок mp_*_freemode_01…, stem .ymt (в т.ч. …_male_freemode_business), индекс ymt
    use_ymt_folder_for_gender: bool = True
    # Содержимое .ymt (бинарные литералы) и экспорт CodeWalker *.ymt.xml — без имён файлов на диске
    use_ymt_meta: bool = True
    use_ymt_xml_meta: bool = True
    # Путь к MetaTool.exe (gta-toolkit) для подкоманды export-ymt-xml; иначе env GTA_CLOTHES_META_TOOL
    meta_tool_exe: str = ""
    # Перед анализом рекурсивно экспортировать все .ymt → .ymt.xml (нужен meta_tool_exe или env)
    auto_export_ymt_xml: bool = False
    # Prefix in drawable / path -> (kind, slot_slug) kind: cloth|prop
    prefix_rules: list[list[str]] = field(
        default_factory=lambda: [
            ["jbib", "cloth", "tops"],
            ["uppr", "cloth", "tops"],
            ["lowr", "cloth", "legs"],
            ["feet", "cloth", "shoes"],
            ["hand", "cloth", "accessories"],
            ["teef", "cloth", "undershirts"],
            ["berd", "cloth", "masks"],
            ["hair_d", "cloth", "hair_styles"],
            ["hairs", "cloth", "hair_styles"],
            ["hair", "cloth", "hair_styles"],
            ["task", "cloth", "bags_and_parachutes"],
            ["decl", "cloth", "decals"],
            ["accs", "cloth", "accessories"],
            ["p_head", "prop", "hats"],
            ["p_eyes", "prop", "glasses"],
            ["p_ears", "prop", "ears"],
            ["p_wrist", "prop", "watches"],
            ["p_bracelet", "prop", "bracelets"],
            ["p_mouth", "prop", "mouth"],
            ["p_lhand", "prop", "hands"],
            ["p_rhand", "prop", "hands"],
            ["p_lwrist", "prop", "watches"],
            ["p_rwrist", "prop", "watches"],
            ["p_legs", "prop", "legs"],
            ["p_lfinger", "prop", "rings"],
            ["p_rfinger", "prop", "rings"],
            ["p_finger", "prop", "rings"],
        ]
    )
    settings_file: str = ""

    def compiled_male(self) -> re.Pattern[str]:
        return re.compile(self.male_regex)

    def compiled_female(self) -> re.Pattern[str]:
        return re.compile(self.female_regex)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Settings:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        clean = {k: v for k, v in d.items() if k in known}
        return cls(**clean)

    def save(self, path: Path) -> None:
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Settings:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
