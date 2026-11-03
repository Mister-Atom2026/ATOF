from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


ROOT = Path(SPECPATH)
DATA_DIRECTORIES = (
    "cars",
    "ch_home",
    "characters",
    "radio",
    "sounds",
    "weapons",
    "world",
    "videos",
)

datas = [(str(ROOT / directory), directory) for directory in DATA_DIRECTORIES]
datas.append((str(ROOT / "static.ttf"), "."))
hiddenimports = collect_submodules("cv2")

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ATOF",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
