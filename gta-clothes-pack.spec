# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

try:
    _SPEC_ROOT = Path(SPECPATH).resolve().parent
except NameError:
    _SPEC_ROOT = Path.cwd()

datas = []
binaries = []
hiddenimports = ['gta_clothes_pack.cli']
tmp_ret = collect_all('fivefury')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Вшить MetaTool + DLL: tools/MetaTool/bin, затем gta-toolkit/…/bin, затем tools/metatool.
_meta_embedded = False
for _base in (
    _SPEC_ROOT / 'tools' / 'MetaTool' / 'bin',
    _SPEC_ROOT / 'tools' / 'gta-toolkit' / 'Tools' / 'MetaTool' / 'bin',
):
    for _cfg in ('Release', 'Debug'):
        _meta_bin = _base / _cfg
        if (_meta_bin / 'MetaTool.exe').is_file():
            datas.append((str(_meta_bin), 'metatool'))
            _meta_embedded = True
            break
    if _meta_embedded:
        break
if not _meta_embedded:
    _meta_drop = _SPEC_ROOT / 'tools' / 'metatool'
    if (_meta_drop / 'MetaTool.exe').is_file():
        datas.append((str(_meta_drop), 'metatool'))

_ICO = _SPEC_ROOT / 'icons' / 'gta-clothes-pack.ico'
_ICON_KW = dict(icon=str(_ICO)) if _ICO.is_file() else {}

a = Analysis(
    ['entry_exe.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='gta-clothes-pack',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    **_ICON_KW,
)
