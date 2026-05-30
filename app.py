"""Ponto de entrada do CortexFlow."""

from __future__ import annotations

import multiprocessing
import os
import sys
from pathlib import Path


def inject_local_binaries_to_path() -> None:
    """
    Prioriza FFmpeg/Tesseract embutidos em ``bin/`` antes do PATH do sistema.

    Deve rodar antes de imports que invocam Whisper, ffmpeg ou pytesseract.
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        candidates = (
            base / "bin",
            Path(sys.executable).resolve().parent / "bin",
            Path(sys.executable).resolve().parent / "_internal" / "bin",
        )
    else:
        candidates = (Path(__file__).resolve().parent / "bin",)

    for bin_dir in candidates:
        if not bin_dir.is_dir():
            continue
        path_entry = str(bin_dir.resolve())
        current = os.environ.get("PATH", "")
        if path_entry not in current.split(os.pathsep):
            os.environ["PATH"] = path_entry + os.pathsep + current
        break


inject_local_binaries_to_path()

from src.ui.main_window import run_app

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_app()
