# -*- mode: python ; coding: utf-8 -*-

import glob
import os
import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None
PROJECT_ROOT = os.path.abspath(SPECPATH)

# Collect all data, binaries and hiddenimports for ortools
ortools_datas, ortools_binaries, ortools_hiddenimports = collect_all("ortools")

# Also find all DLLs in ortools/.libs and include both in root and ortools/.libs
VENV_ROOT = os.path.join(PROJECT_ROOT, ".venv")
ortools_libs_dir = os.path.join(VENV_ROOT, "Lib", "site-packages", "ortools", ".libs")
extra_binaries = []
if os.path.isdir(ortools_libs_dir):
    for dll_path in glob.glob(os.path.join(ortools_libs_dir, "*.dll")):
        extra_binaries.append((dll_path, "ortools/.libs"))
        extra_binaries.append((dll_path, "."))

datas = [
    (os.path.join(PROJECT_ROOT, "frontend", "dist"), os.path.join("frontend", "dist")),
    (os.path.join(PROJECT_ROOT, "placement_engine.db"), "."),
    (os.path.join(PROJECT_ROOT, "fixtures"), "fixtures"),
    (os.path.join(PROJECT_ROOT, "backend", "alembic"), os.path.join("backend", "alembic")),
    (os.path.join(PROJECT_ROOT, "backend", "alembic.ini"), "backend"),
] + ortools_datas

binaries = ortools_binaries + extra_binaries

hidden_imports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "fastapi.responses",
    "fastapi.staticfiles",
    "starlette",
    "starlette.staticfiles",
    "starlette.responses",
    "pydantic",
    "pydantic_core",
    "sqlalchemy",
    "sqlalchemy.sql.default_comparator",
    "sqlalchemy.dialects.sqlite",
    "multipart",
    "python_multipart",
    "alembic",
    "alembic.runtime.migration",
    "alembic.ddl.sqlite",
    "backend.app.api.main",
    "backend.app.storage.database",
    "backend.app.storage.models.entities",
    "backend.app.scheduler.engine",
    "backend.app.scheduler.solver",
    "backend.app.scheduler.heuristic",
    "backend.app.scheduler.verifier",
    "backend.app.domain.eligibility.evaluator",
    "backend.app.domain.eligibility.batch_evaluator",
] + ortools_hiddenimports

a = Analysis(
    [os.path.join(PROJECT_ROOT, "scripts", "exe_launcher.py")],
    pathex=[PROJECT_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PlacementEngine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
