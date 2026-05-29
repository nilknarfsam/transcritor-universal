"""Serviço singleton de transcrição Whisper para áudio e vídeo."""

from __future__ import annotations

import os
import threading
from typing import Any, Optional

from src.models.transcription_job import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS


class TranscriptionService:
    """Carrega o modelo Whisper uma vez e reutiliza entre transcrições na mesma sessão."""

    _instance: Optional["TranscriptionService"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "TranscriptionService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._model = None
                    cls._instance._model_name: Optional[str] = None
                    cls._instance._model_lock = threading.Lock()
        return cls._instance

    def ensure_whisper(self) -> Any:
        """Importa o pacote ``whisper`` ou levanta ``RuntimeError`` com instrução de instalação."""
        try:
            import whisper
        except ImportError as exc:
            raise RuntimeError(
                "Whisper não instalado. Rode instalar_dependencias.bat ou "
                "pip install -r requirements.txt"
            ) from exc
        return whisper

    def load_model(self, model_name: str = "base") -> Any:
        """Carrega (ou reutiliza) o modelo Whisper indicado."""
        with self._model_lock:
            if self._model is not None and self._model_name == model_name:
                return self._model
            whisper = self.ensure_whisper()
            self._model = whisper.load_model(model_name)
            self._model_name = model_name
            return self._model

    def unload_model(self) -> None:
        """Libera o modelo da memória (útil após filas longas ou troca de modelo)."""
        with self._model_lock:
            self._model = None
            self._model_name = None

    def transcribe_media(
        self,
        file_path: str,
        language: str = "auto",
        model_name: str = "base",
    ) -> str:
        """Transcreve um arquivo de áudio ou vídeo e retorna o texto."""
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        if ext not in (AUDIO_EXTENSIONS | VIDEO_EXTENSIONS):
            raise ValueError(f"Arquivo não é áudio/vídeo: {file_path}")

        model = self.load_model(model_name)
        if language == "auto":
            result = model.transcribe(file_path)
        else:
            result = model.transcribe(file_path, language=language)
        return str(result.get("text", "")).strip()

    @property
    def is_model_loaded(self) -> bool:
        return self._model is not None

    @property
    def loaded_model_name(self) -> Optional[str]:
        return self._model_name
