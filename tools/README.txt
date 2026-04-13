Submodule: gta-toolkit (https://github.com/indilo53/gta-toolkit)
  Опционально: RageLib и MetaTool для экспорта .ymt в .ymt.xml.
  Сборка gta-clothes-pack.exe / build_all.ps1 MetaTool не собирает.

После клона репозитория (если нужен MetaTool):
  git submodule update --init --recursive

Скрипт build_meta_tool.ps1 не вызывает MSBuild, если уже есть MetaTool.exe в одном из путей:
  tools\MetaTool\bin\Release\ (или Debug), tools\gta-toolkit\Tools\MetaTool\bin\…, либо tools\metatool\
  (скопируйте сюда содержимое bin\Release с DLL). Или заданы GTA_CLOTHES_META_TOOL / META_TOOL_EXE
  на существующий файл. Пересборка: -Force или GTA_CLOTHES_FORCE_META_TOOL_REBUILD=1

Сборка MetaTool:
  - MSBuild (Visual Studio или Build Tools)
  - .NET Framework 4.7.2 Developer Pack (reference assemblies для MSBuild):
    скрипт при отсутствии папки Reference Assemblies\v4.7.2 сам скачивает официальный
    NDP472-DevPack-ENU.exe с Microsoft и ставит его тихо (/quiet); нужны права администратора
    (UAC). Отключить автоустановку: -SkipNet472Install или GTA_CLOTHES_SKIP_NET472_INSTALL=1
  powershell -ExecutionPolicy Bypass -File scripts\build_meta_tool.ps1

Скрипт собирает MetaTool через tools\gta-toolkit\Toolkit.sln (Release | Any CPU), чтобы native DirectXTex шёл как x64; если .sln нет — fallback на MetaTool.csproj.

Готовый exe (после Release):
  tools\gta-toolkit\Tools\MetaTool\bin\Release\MetaTool.exe

Python находит его автоматически (ymt_export.resolve_meta_tool_exe).
