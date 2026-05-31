"""Ponto de entrada do CortexFlow."""

from __future__ import annotations

import multiprocessing
import os
import subprocess
import sys
from pathlib import Path


def _patch_subprocess_for_windows_windowless() -> None:
    """
    Evita janelas CMD piscando e crash de FFmpeg/Tesseract em build windowless.

    Deve rodar antes de imports que invocam subprocess (Whisper, ffmpeg, etc.).
    """
    if sys.platform != "win32":
        return

    _CREATE_NO_WINDOW = 0x08000000
    _original_popen = subprocess.Popen

    class _Popen(_original_popen):
        def __init__(self, *args, **kwargs):
            if "creationflags" not in kwargs:
                kwargs["creationflags"] = _CREATE_NO_WINDOW
            if getattr(sys, "frozen", False):
                kwargs["stdin"] = subprocess.DEVNULL
                kwargs["stdout"] = subprocess.DEVNULL
                kwargs["stderr"] = subprocess.STDOUT
            super().__init__(*args, **kwargs)

    subprocess.Popen = _Popen  # type: ignore[misc, assignment]


_patch_subprocess_for_windows_windowless()


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
        os.environ["PATH"] = path_entry + os.pathsep + os.environ.get("PATH", "")
        break


inject_local_binaries_to_path()

from src.ui.main_window import run_app

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_app()
