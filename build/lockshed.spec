# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for The LockShed.
#
# Run this from the PROJECT ROOT (not from inside build/), e.g.:
#   pyinstaller build\lockshed.spec --distpath dist --workpath build\work --noconfirm
# (build.bat does this for you automatically.)
#
# Produces an "onedir" build (a folder containing LockShed.exe plus its
# dependencies and data files) rather than a single giant "onefile" exe.
# Onedir starts faster and avoids onefile's self-extracting-to-a-temp-folder
# behavior, which matters here since the app reads chrome_extension/ and
# mobile_pwa/ as real files at runtime (see BASE_DIR in password_manager.py).

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# PyInstaller resolves every relative path in this file relative to the
# spec file's OWN directory (SPECPATH, injected automatically by
# PyInstaller) - not relative to wherever `pyinstaller` was invoked from.
# Since this spec lives in build/, we need to step up one level to reach
# the actual project root where password_manager.py and the data folders
# live.
ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))

block_cipher = None

# Data folders bundled alongside the exe, at the same relative paths the
# app already expects (see BASE_DIR / ICON_PATH / mobile_pwa lookups in
# password_manager.py).
datas = [
    (os.path.join(ROOT, 'chrome_extension'), 'chrome_extension'),
    (os.path.join(ROOT, 'mobile_pwa'), 'mobile_pwa'),
    (os.path.join(ROOT, 'assets'), 'assets'),
]
datas += collect_data_files('customtkinter')  # bundled themes/fonts

hiddenimports = []
hiddenimports += collect_submodules('pystray')   # picks up the win32 backend
hiddenimports += ['PIL._tkinter_finder']

a = Analysis(
    [os.path.join(ROOT, 'password_manager.py')],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LockShed',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # windowed app, no console popup (matches starta.bat's pythonw)
    icon=os.path.join(ROOT, 'assets', 'lock_icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LockShed',         # -> dist/LockShed/LockShed.exe
)

