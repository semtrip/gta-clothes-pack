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
    max_male_per_pack: int = 128
    max_female_per_pack: int = 128
    layout: str = "flat"  # flat | preserve
    duplicate_shared_ytd: bool = True
    dry_run: bool = False
    apply_epic_rename: bool = True
    epic_number_width: int = 3
    texture_index_width: int = 2
    male_regex: str = r"(?i)(^|[\\/])mp_m_freemode_01|(^|[_/])m_|_m_|male"
    female_regex: str = r"(?i)(^|[\\/])mp_f_freemode_01|(^|[_/])f_|_f_|female"
    # Prefix in drawable / path -> (kind, slot_slug) kind: cloth|prop
    prefix_rules: list[list[str]] = field(
        default_factory=lambda: [
            ["jbib", "cloth", "tops"],
            ["lowr", "cloth", "legs"],
            ["feet", "cloth", "shoes"],
            ["hand", "cloth", "accessories"],
            ["teef", "cloth", "undershirts"],
            ["berd", "cloth", "masks"],
            ["hair", "cloth", "hair_styles"],
            ["task", "cloth", "bags_and_parachutes"],
            ["decl", "cloth", "decals"],
            ["accs", "cloth", "accessories"],
            ["p_head", "prop", "hats"],
            ["p_eyes", "prop", "glasses"],
            ["p_ears", "prop", "ears"],
            ["p_wrist", "prop", "watches"],
            ["p_bracelet", "prop", "bracelets"],
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
