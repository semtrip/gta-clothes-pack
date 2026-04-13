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

# MetaTool в exe не вшивается. Для export-ymt-xml: GTA_CLOTHES_META_TOOL или свой MetaTool рядом с exe.

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
    runtime_hooks=[str(_SPEC_ROOT / 'pyi_rth_fivefury_hashing.py')],
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
