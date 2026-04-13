# GTA Clothes Pack

Утилита для сканирования каталогов с `.ydd`, сопоставления внешних `.ytd` по именам текстур из шейдеров (через **fivefury**), классификации пола и типа слота, переименования в схему `mp_m_freemode_01_epic_cloth^{слот}_{номер}` / `mp_f_freemode_01_…` (пропы: `epic_prop^…`) и раскладки по папкам `pack_001`, `pack_002`, … (до 128 мужских и 128 женских YDD на пак).

## Установка

```bash
pip install -r requirements.txt
```

Или из корня проекта:

```bash
pip install -e .
```

## Запуск

Интерактивное меню (если не указаны аргументы):

```bash
python -m gta_clothes_pack
```

CLI:

```bash
python -m gta_clothes_pack --input "F:\mods\Clothes\mod" --output "F:\mods\Clothes\packed" --dry-run
python -m gta_clothes_pack -i "F:\mods\Clothes\mod" -o "F:\mods\Clothes\packed"
```

Опции: `--no-rename`, `--max-male`, `--max-female`, `--report`, `--settings path.json`, `--workers`, `--log`, `--no-pause`.

- **`--dry-run`** — только анализ (индекс YTD, разбор YDD, расчёт паков, журнал); **не** создаёт `pack_*` и **не** копирует/переименовывает файлы. Для реальной упаковки запускайте **без** этого флага.

## Полная сборка проекта (Windows)

Из корня репозитория: подмодули (опционально), зависимости Python и `gta-clothes-pack.exe` (PyInstaller). **MetaTool** в эту сборку не входит; для экспорта `.ymt` → `.ymt.xml` соберите MetaTool отдельно: `.\scripts\build_meta_tool.ps1` (нужен submodule `tools/gta-toolkit` и MSBuild).

```bat
build_all.bat
```

Или PowerShell:

```powershell
.\scripts\build_all.ps1
```

Параметры: `-SkipSubmodule`, `-SkipPyInstaller` (только зависимости и `pip install -e .`).

## Сборка в один .exe (Windows)

1. Установите зависимости и пакет в режиме разработки:

```bash
pip install -r requirements.txt -r requirements-build.txt
pip install -e .
```

2. Соберите исполняемый файл (в каталоге проекта):

```bash
python -m PyInstaller --noconfirm --clean gta-clothes-pack.spec
```

Готовый файл: `dist\gta-clothes-pack.exe` (консольное приложение). Иконка Windows задаётся `icons\gta-clothes-pack.ico` в `gta-clothes-pack.spec`; исходник — `icons\gta-clothes-pack.png`. Пересобрать `.ico`: `python scripts\generate_app_icon.py` (нужен Pillow из `requirements-build.txt`).

**MetaTool** в exe **не** упаковывается. Для команд с экспортом `.ymt` укажите путь к `MetaTool.exe` через `GTA_CLOTHES_META_TOOL` / `META_TOOL_EXE` или положите exe рядом с приложением; либо соберите MetaTool из `tools/gta-toolkit` (`.\scripts\build_meta_tool.ps1`).

Либо запустите `.\scripts\build_exe.ps1` — скрипт ставит зависимости и вызывает PyInstaller.

Первая сборка создаёт `gta-clothes-pack.spec`; дальше достаточно `python -m PyInstaller gta-clothes-pack.spec`. В spec используется `--collect-all fivefury`, чтобы подтянуть нативные модули и данные **fivefury**.

## Публикация на GitHub (публичный репозиторий и релиз с .exe)

**Релиз на GitHub (страница Releases + файл .exe)** создаётся **только через Actions**: при **пуше тега** `v*` workflow [.github/workflows/release.yml](.github/workflows/release.yml) собирает `gta-clothes-pack.exe` и публикует релиз (`softprops/action-gh-release`). Вручную `gh release create` или кнопка «Draft release» на сайте **не нужны** — после `git push origin v0.x.y` откройте **Actions** и дождитесь job **Release Windows EXE**.

1. Создайте **пустой** публичный репозиторий на GitHub (без README, если клонируете существующий проект).
2. В каталоге проекта:

```bash
git remote add origin https://github.com/ВАШ_НИК/gta-clothes-pack.git
git push -u origin main
git tag v0.1.0
git push origin v0.1.0
```

3. Откройте вкладку **Actions** — после завершения workflow в **Releases** появится релиз с файлом `gta-clothes-pack.exe`.

Обходной путь без CI (локальная сборка exe и выгрузка через `gh`): `.\scripts\publish_github.ps1` — только если Actions недоступен; для обычных релизов используйте пуш тега, как выше.

## Поведение

- Парсинг YDD: drawable в dictionary, материалы/текстурные ссылки.
- Индекс всех YTD под входным каталогом; сопоставление по совпадению **имени текстуры** в шейдере YDD с именем текстуры внутри YTD. Дополнительно (по умолчанию): если есть **foo.ydd** и **foo.ytd** с тем же именем без расширения, YTD подключается к этому YDD даже при несовпадении имён текстур (`pair_ytd_same_stem_as_ydd`; отключение: `--no-stem-pair`). **Orphan YTD** — файлы .ytd, которые ни к одному YDD не привязались.
- Пол: в первую очередь **литералы в бинарнике YDD** `mp_m_freemode_01` и `mp_f_freemode_01` (полный скан файла); путь и имя файла на диске **не** используются. Если маркеров нет — запасной вариант по regex по строкам **из данных ресурса**: drawable, текстуры, **имена шейдеров и параметров материалов**, плюс эвристика по ASCII в **system и graphics** секциях RSC7 (`male_regex` / `female_regex`).
- Слот (в имени файла после `^`, напр. `epic_cloth^tops_001`): по **уровням** — сначала только **имена drawable** из меты YDD, затем вместе с текстурами и строками материалов, затем с эвристикой по секциям RSC7; путь на диске не участвует. При отсутствии совпадения — `fallback_slot_slug` (по умолчанию `misc`), в отчёт может попасть `unknown_slot`.
- Слот: префиксы вроде `jbib`, `lowr`, `p_head` → slug (`tops`, `legs`, `hats`, …).
- Переименование: правка C-строк в бинарнике YDD и сохранение YTD с новыми именами текстур (ограничение: длина строки сохраняется как в оригинале при замене в YDD). Имена: **`mp_m_freemode_01`** / **`mp_f_freemode_01`**, затем **`_epic_cloth^`** или **`_epic_prop^`**, тип слота (например `tops`), номер: `mp_f_freemode_01_epic_cloth^tops_001`. Для unknown префикс ped — `mp_m_freemode_01`.
- **Паки `pack_*`:** в один пак кладётся до `max_male` YDD с полом **male** и до `max_female` с полом **female** (по очереди: сначала порция male, затем female). YDD с полом **unknown** (не угадали по regex или совпали оба варианта) **не участвуют** в этом лимите и собираются **отдельным паком** в конце — поэтому первый пак может быть меньше 128+128, если часть файлов ушла в unknown.

Сборка `dlc.rpf` не входит в утилиту.
