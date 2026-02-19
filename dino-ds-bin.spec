# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('src/dino_ds/schemas', 'dino_ds/schemas'), ('src/dino_ds/system_prompt_registry.json', 'dino_ds'), ('system_prompt_registry.json', 'dino_ds'), ('system_prompt_registry.json', '.'), ('prompts/system', 'prompts/system'), ('MASTER_GLOBAL_SCHEMA_LABELS_SUPERSEDED_v2.md', '.'), ('DinoDS_full_validator_config_2026-02-19.md', '.')]
binaries = []
hiddenimports = []
tmp_ret = collect_all('dino_ds')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['/tmp/dino_ds_entry.py'],
    pathex=['src'],
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
    name='dino-ds-bin',
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
)
