# -*- mode: python ; coding: utf-8 -*-
"""Spec do PyInstaller para gerar o cash_auditor.exe (onefile, Windows).

Build:
    pyinstaller packaging/cash_auditor.spec --noconfirm
Saída:
    dist/cash_auditor.exe
"""
import os

from PyInstaller.utils.hooks import collect_submodules

ROOT = os.path.abspath(os.getcwd())

# Frontend (HTML/CSS/JS + Chart.js) precisa ir embutido no executável.
datas = [
    (os.path.join(ROOT, "frontend"), "frontend"),
]

# uvicorn[standard] e o app usam imports dinâmicos — garantimos sua inclusão.
hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("backend")
    + [
        "anyio",
        "websockets",
        "httptools",
        "watchfiles",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
    ]
)

a = Analysis(
    [os.path.join(ROOT, "packaging", "launcher.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
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
    name="cash_auditor",
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
