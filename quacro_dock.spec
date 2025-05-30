# -*- mode: python ; coding: utf-8 -*-

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--release", action='store_true')
options = parser.parse_args()

# to build in release mode
# use `pyinstaller.exe .\quacro_dock.spec -- --release` 
if options.release:
    OPTIMIZE_FLAG = 1 # remove __debug__ branches
    HAS_CONSOLE = False
else:
    OPTIMIZE_FLAG = 0
    HAS_CONSOLE = True

a = Analysis(
    ['quacro_main.py'],
    pathex=[],
    binaries=[
        ('quacro_hook_proc.dll','.'),
        ('quacro_utils.dll','.')
    ],
    datas=[
        ('./i18n/quacro_lang_en.toml','./i18n'),
        ('./i18n/quacro_lang_zh_cn.toml','./i18n'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "asyncio",
        "argparse",
        "getopt",
        "multiprocessing",
        "bz2",
        "lzma",
        "tarfile",
        "decimal",
        "fractions",
        "statistics",
        "hashlib",
        "pkg_resources",
        "xml",
        "socket",
        "_socket",
        "select",
        "setuptools",
        "distutils",
        "tracemalloc",
        "email",
        "csv",
        "pprint",
        "imp",
        "webbrowser",

        "win32com",
        "win32ui",
        "pywin32_system32",
        
        "webview.http",
        "bottle",
        "ssl",
        "unicodedata",
    ],
    noarchive=False,
    optimize=OPTIMIZE_FLAG,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='quacro_dock',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[
        # hook_proc.dll is small enough (4k)
        # we don't need to compress it
        'quacro_hook_proc.dll'
    ],
    runtime_tmpdir=None,
    console=HAS_CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
