"""Serviço singleton de transcrição Whisper para áudio e vídeo."""

from __future__ import annotations

import os
import threading
from typing import Any, Callable, Optional

from src.core.whisper_progress import capture_tqdm_progress
from src.models.transcription_job import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS

# Agrupa segmentos Whisper em blocos de ~N segundos para parágrafos legíveis.
DEFAULT_BLOCK_SECONDS = 60

# Progresso do job reservado antes/depois da fase Whisper (JobProcessor).
WHISPER_JOB_PROGRESS_START = 0.05
WHISPER_JOB_PROGRESS_END = 0.90


def format_timestamp_mmss(seconds: float) -> str:
    """Formata segundos como ``MM:SS`` (ex.: 45 -> ``00:45``)."""
    total = int(max(0, seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def format_segments_to_text(
    segments: list[dict[str, Any]],
    *,
    block_seconds: int = DEFAULT_BLOCK_SECONDS,
) -> str:
    """
    Agrupa segmentos Whisper em parágrafos com timestamp Markdown.

    Cada bloco (~``block_seconds``) inicia com ``**[MM:SS]**`` seguido do texto.
    """
    if not segments:
        return ""

    paragraphs: list[str] = []
    current_bucket = -1
    current_parts: list[str] = []
    block_start = 0.0

    for seg in segments:
        start = float(seg.get("start", 0) or 0)
        text = str(seg.get("text", "")).strip()
        if not text:
            continue

        bucket = int(start // block_seconds) if block_seconds > 0 else 0
        if bucket != current_bucket:
            if current_parts:
                ts = format_timestamp_mmss(block_start)
                paragraphs.append(f"**[{ts}]** {' '.join(current_parts)}")
            current_bucket = bucket
            block_start = start
            current_parts = [text]
        else:
            current_parts.append(text)

    if current_parts:
        ts = format_timestamp_mmss(block_start)
        paragraphs.append(f"**[{ts}]** {' '.join(current_parts)}")

    return "\n\n".join(paragraphs).strip()


def map_whisper_fraction_to_job(whisper_fraction: float) -> float:
    """Mapeia progresso do Whisper (0–1) para a faixa do job (5%–90%)."""
    whisper_fraction = max(0.0, min(1.0, whisper_fraction))
    span = WHISPER_JOB_PROGRESS_END - WHISPER_JOB_PROGRESS_START
    return WHISPER_JOB_PROGRESS_START + whisper_fraction * span


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
        *,
        on_whisper_progress: Optional[Callable[[float], None]] = None,
        block_seconds: int = DEFAULT_BLOCK_SECONDS,
    ) -> str:
        """
        Transcreve áudio/vídeo com parágrafos timestampados e progresso via tqdm.

        ``on_whisper_progress`` recebe fração 0.0–1.0 lida da barra tqdm em ``stderr``.
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        if ext not in (AUDIO_EXTENSIONS | VIDEO_EXTENSIONS):
            raise ValueError(f"Arquivo não é áudio/vídeo: {file_path}")

        model = self.load_model(model_name)

        def _run_transcribe() -> dict[str, Any]:
            if language == "auto":
                return model.transcribe(file_path)
            return model.transcribe(file_path, language=language)

        if on_whisper_progress is not None:
            with capture_tqdm_progress(on_whisper_progress):
                result = _run_transcribe()
        else:
            result = _run_transcribe()

        segments = result.get("segments") or []
        if segments:
            formatted = format_segments_to_text(segments, block_seconds=block_seconds)
            if formatted:
                return formatted

        return str(result.get("text", "")).strip()

    @property
    def is_model_loaded(self) -> bool:
        return self._model is not None

    @property
    def loaded_model_name(self) -> Optional[str]:
        return self._model_name
