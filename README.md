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

Опции: `--dry-run`, `--no-rename`, `--max-male`, `--max-female`, `--report`, `--settings path.json`.

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

## Поведение

- Парсинг YDD: drawable в dictionary, материалы/текстурные ссылки.
- Индекс всех YTD под входным каталогом; сопоставление по совпадению имени текстуры.
- Пол: строки drawable / путь / `mp_m_freemode_01` vs `mp_f_freemode_01` (настраивается regex в `config.Settings`).
- Слот: префиксы вроде `jbib`, `lowr`, `p_head` → slug (`tops`, `legs`, `hats`, …).
- Переименование: правка C-строк в бинарнике YDD и сохранение YTD с новыми именами текстур (ограничение: длина строки сохраняется как в оригинале при замене в YDD).

Сборка `dlc.rpf` не входит в утилиту.
