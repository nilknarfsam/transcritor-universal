from __future__ import annotations

import os
import traceback
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class JobErrorInfo:
    user_message: str
    error_code: str
    technical_detail: str


def classify_job_error(exc: BaseException, file_path: str) -> JobErrorInfo:
    path = file_path or ""
    name = os.path.basename(path) if path else "arquivo"
    detail = f"{type(exc).__name__}: {exc}"

    if isinstance(exc, FileNotFoundError):
        if path and os.path.isfile(path):
            return JobErrorInfo(
                user_message=(
                    "FFmpeg não encontrado. Instale o FFmpeg e adicione ao PATH do sistema "
                    "(necessário para transcrever áudio e vídeo)."
                ),
                error_code="FFMPEG_NOT_FOUND",
                technical_detail=detail,
            )
        return JobErrorInfo(
            user_message=f"Arquivo não encontrado: {name}",
            error_code="FILE_NOT_FOUND",
            technical_detail=detail,
        )
    if isinstance(exc, PermissionError):
        return JobErrorInfo(
            user_message=f"Sem permissão para ler ou gravar: {name}",
            error_code="PERMISSION_DENIED",
            technical_detail=detail,
        )
    if isinstance(exc, MemoryError):
        return JobErrorInfo(
            user_message="Memória insuficiente para processar este arquivo.",
            error_code="OUT_OF_MEMORY",
            technical_detail=detail,
        )
    if isinstance(exc, ImportError):
        return JobErrorInfo(
            user_message="Dependência ausente. Verifique requirements.txt e reinicie o app.",
            error_code="MISSING_DEPENDENCY",
            technical_detail=detail,
        )
    if isinstance(exc, RuntimeError) and "Whisper" in str(exc):
        return JobErrorInfo(
            user_message="Whisper não disponível. Instale as dependências e o FFmpeg.",
            error_code="WHISPER_UNAVAILABLE",
            technical_detail=detail,
        )
    if isinstance(exc, OSError):
        return JobErrorInfo(
            user_message=f"Erro de sistema ao acessar: {name}",
            error_code="OS_ERROR",
            technical_detail=detail,
        )
    if isinstance(exc, ValueError):
        return JobErrorInfo(
            user_message=str(exc) or "Valor inválido para este arquivo.",
            error_code="INVALID_VALUE",
            technical_detail=detail,
        )

    msg = str(exc).strip() or type(exc).__name__
    if len(msg) > 200:
        msg = msg[:197] + "…"
    return JobErrorInfo(
        user_message=f"Falha ao processar {name}: {msg}",
        error_code="PROCESSING_ERROR",
        technical_detail=detail,
    )


def format_traceback(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
