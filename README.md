# GTA Clothes Pack

Утилита для сканирования каталогов с `.ydd`, сопоставления внешних `.ytd` по именам текстур из шейдеров (через **fivefury**), классификации пола и типа слота, переименования в схему `epic_cloth__` / `epic_prop__` и раскладки по папкам `pack_001`, `pack_002`, … (до 128 мужских и 128 женских YDD на пак).

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

Готовый файл: `dist\gta-clothes-pack.exe` (консольное приложение).

Либо запустите `.\scripts\build_exe.ps1` — скрипт ставит зависимости и вызывает PyInstaller.

Первая сборка создаёт `gta-clothes-pack.spec`; дальше достаточно `python -m PyInstaller gta-clothes-pack.spec`. В spec используется `--collect-all fivefury`, чтобы подтянуть нативные модули и данные **fivefury**.

## Публикация на GitHub (публичный репозиторий и релиз с .exe)

Код и CI уже в репозитории: при **пуше тега** `v*` (например `v0.1.0`) GitHub Actions собирает `gta-clothes-pack.exe` и **прикрепляет его к релизу** (см. [.github/workflows/release.yml](.github/workflows/release.yml)).

1. Создайте **пустой** публичный репозиторий на GitHub (без README, если клонируете существующий проект).
2. В каталоге проекта:

```bash
git remote add origin https://github.com/ВАШ_НИК/gta-clothes-pack.git
git push -u origin main
git tag v0.1.0
git push origin v0.1.0
```

3. Откройте вкладку **Actions** — после завершения workflow в **Releases** появится релиз с файлом `gta-clothes-pack.exe`.

Вручную без Actions: установите [GitHub CLI](https://cli.github.com/), выполните `gh auth login`, затем `.\scripts\publish_github.ps1 -RepoOwner ВАШ_НИК`.

## Поведение

- Парсинг YDD: drawable в dictionary, материалы/текстурные ссылки.
- Индекс всех YTD под входным каталогом; сопоставление по совпадению имени текстуры.
- Пол: в первую очередь **литералы в бинарнике YDD** `mp_m_freemode_01` и `mp_f_freemode_01` (полный скан файла); путь и имя файла на диске **не** используются. Если маркеров нет — запасной вариант по regex по строкам **из данных ресурса**: drawable, текстуры, **имена шейдеров и параметров материалов**, плюс эвристика по ASCII в **system и graphics** секциях RSC7 (`male_regex` / `female_regex`).
- Слот (`epic_cloth__…_<слот>_…`): по **уровням** — сначала только **имена drawable** из меты YDD, затем вместе с текстурами и строками материалов, затем с эвристикой по секциям RSC7; путь на диске не участвует. При отсутствии совпадения — `fallback_slot_slug` (по умолчанию `misc`), в отчёт может попасть `unknown_slot`.
- Слот: префиксы вроде `jbib`, `lowr`, `p_head` → slug (`tops`, `legs`, `hats`, …).
- Переименование: правка C-строк в бинарнике YDD и сохранение YTD с новыми именами текстур (ограничение: длина строки сохраняется как в оригинале при замене в YDD). Пол **male** → `m`, **female** → `f`, **unknown** → `x` в имени (`epic_cloth__x_…`), чтобы отдельный пак с нераспознанным полом тоже получал epic rename.
- **Паки `pack_*`:** в один пак кладётся до `max_male` YDD с полом **male** и до `max_female` с полом **female** (по очереди: сначала порция male, затем female). YDD с полом **unknown** (не угадали по regex или совпали оба варианта) **не участвуют** в этом лимите и собираются **отдельным паком** в конце — поэтому первый пак может быть меньше 128+128, если часть файлов ушла в unknown.

Сборка `dlc.rpf` не входит в утилиту.
