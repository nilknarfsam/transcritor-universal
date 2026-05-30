# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — CortexFlow Desktop (one-directory).

Saída: ``dist/CortexFlow/CortexFlow.exe`` (+ DLLs/libs na mesma pasta).
Dados do usuário NÃO são empacotados — criados em ``<pasta_do_exe>/data/``
(ver settings_service.py).

Release: console=False (sem janela de terminal). Fase 3.3 usou console=True para debug.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

project_root = Path(SPECPATH)

# Assets de UI — CustomTkinter (temas/fontes) e tkinterdnd2 (tkdnd + DLLs)
datas = collect_data_files("customtkinter") + collect_data_files("tkinterdnd2")

# Binários externos embutidos (FFmpeg, Tesseract) — Standalone / Portátil
_bin_dir = project_root / "bin"
if _bin_dir.is_dir():
    datas.append((str(_bin_dir), "bin"))

# Branding — ícone da janela e assets empacotados
_assets_dir = project_root / "assets"
if _assets_dir.is_dir():
    datas.append((str(_assets_dir), "assets"))

_icon_file = project_root / "assets" / "icon.ico"

# Whisper / PyTorch — imports explícitos para evitar falhas silenciosas no onedir
_whisper_torch = ["tiktoken", "torchaudio", "whisper", "torch"]

hiddenimports = _whisper_torch + [
    "tiktoken_ext",
    "tiktoken_ext.openai_public",
    "customtkinter",
    "tkinterdnd2",
    "PIL",
    "PIL._tkinter_finder",
    "pdfplumber",
    "docx",
    "openpyxl",
    "pytesseract",
    "src",
    "src.core",
    "src.models",
    "src.ui",
    "src.ui.design",
    "src.ui.components",
    "src.ui.legacy_ui",
    "src.ai_ready",
    "src.cache",
    "src.library",
    "src.semantic",
    "src.study",
    "src.datasets",
    "src.knowledge_graph",
    "src.knowledge",
] + collect_submodules("src")

a = Analysis(
    [str(project_root / "app.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "scipy",
        "pandas",
        "notebook",
        "pytest",
        "IPython",
        "tkinter.test",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CortexFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(_icon_file) if _icon_file.is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CortexFlow",
)
