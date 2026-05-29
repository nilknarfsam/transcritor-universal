"""Persistent Queue Engine — salva e restaura estado da fila em data/queue_state.json."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.core.log_service import get_logger
from src.core.settings_service import DATA_DIR
from src.models.transcription_job import JobStatus, TranscriptionJob

QUEUE_STATE_FILE = DATA_DIR / "queue_state.json"
STATE_VERSION = 1
PIPELINE_CHECKPOINTS = ("whisper", "ocr", "clean", "semantic", "study", "notebooklm", "dataset")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PersistentQueue:
    """Serializa e restaura o estado da fila em ``data/queue_state.json``."""

    def __init__(self) -> None:
        self._logger = get_logger()
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        jobs: list[TranscriptionJob],
        *,
        selected_id: Optional[str] = None,
        is_processing: bool = False,
        stop_requested: bool = False,
        session_completed: int = 0,
        session_errors: int = 0,
        export_mode: str = "",
        content_template: str = "",
    ) -> None:
        payload = {
            "version": STATE_VERSION,
            "saved_at": _utc_now(),
            "is_processing": is_processing,
            "stop_requested": stop_requested,
            "selected_id": selected_id or "",
            "session_completed": session_completed,
            "session_errors": session_errors,
            "export_mode": export_mode,
            "content_template": content_template,
            "jobs": [self._job_to_dict(j) for j in jobs],
        }
        try:
            tmp = QUEUE_STATE_FILE.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            tmp.replace(QUEUE_STATE_FILE)
        except OSError as exc:
            self._logger.warning("Falha ao persistir fila: %s", exc)

    def load(self) -> Optional[dict[str, Any]]:
        if not QUEUE_STATE_FILE.exists():
            return None
        try:
            with open(QUEUE_STATE_FILE, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return None
            return data
        except (json.JSONDecodeError, OSError) as exc:
            self._logger.warning("queue_state.json inválido: %s", exc)
            return None

    def restore_jobs(self, raw: dict[str, Any]) -> tuple[list[TranscriptionJob], dict[str, Any]]:
        """Restaura jobs com limpeza segura de entradas corrompidas."""
        meta = {
            "restored": False,
            "corrupted_removed": 0,
            "processing_reset": 0,
            "was_processing": bool(raw.get("is_processing")),
            "saved_at": raw.get("saved_at", ""),
        }
        jobs_raw = raw.get("jobs", [])
        if not isinstance(jobs_raw, list):
            return [], meta

        jobs: list[TranscriptionJob] = []
        for item in jobs_raw:
            job = self._dict_to_job(item)
            if job is None:
                meta["corrupted_removed"] += 1
                continue
            if job.status == JobStatus.PROCESSING:
                job.status = JobStatus.WAITING
                job.error_message = ""
                meta["processing_reset"] += 1
            jobs.append(job)

        if jobs:
            meta["restored"] = True
        return jobs, meta

    def clear_state(self) -> None:
        if QUEUE_STATE_FILE.exists():
            try:
                QUEUE_STATE_FILE.unlink()
            except OSError:
                pass

    def has_snapshot(self) -> bool:
        return QUEUE_STATE_FILE.exists()

    @staticmethod
    def _job_to_dict(job: TranscriptionJob) -> dict[str, Any]:
        return {
            "id": job.id,
            "file_path": job.file_path,
            "status": job.status.value,
            "output_path": job.output_path,
            "result_text": job.result_text[:500_000] if job.result_text else "",
            "error_message": job.error_message,
            "error_code": job.error_code,
            "semantic_metadata": dict(job.semantic_metadata),
            "study_metadata": dict(job.study_metadata),
            "pipeline_progress": dict(job.pipeline_progress),
            "job_progress": job.job_progress,
            "export_mode": job.export_mode,
            "content_template": job.content_template,
            "file_hash": job.file_hash,
            "cache_status": job.cache_status,
            "created_at": job.created_at,
            "updated_at": job.updated_at or _utc_now(),
        }

    def _dict_to_job(self, data: Any) -> Optional[TranscriptionJob]:
        if not isinstance(data, dict):
            return None
        path = str(data.get("file_path", "")).strip()
        if not path or not os.path.isfile(path):
            self._logger.info("Job removido na recuperação (arquivo ausente): %s", path)
            return None
        try:
            status = JobStatus(str(data.get("status", JobStatus.WAITING.value)))
        except ValueError:
            status = JobStatus.WAITING
        progress = data.get("pipeline_progress", {})
        if not isinstance(progress, dict):
            progress = {}
        semantic = data.get("semantic_metadata", {})
        if not isinstance(semantic, dict):
            semantic = {}
        study = data.get("study_metadata", {})
        if not isinstance(study, dict):
            study = {}
        job_id = str(data.get("id") or "").strip()
        if not job_id:
            job_id = str(uuid.uuid4())
        return TranscriptionJob(
            file_path=path,
            id=job_id,
            status=status,
            output_path=str(data.get("output_path", "")),
            result_text=str(data.get("result_text", "")),
            error_message=str(data.get("error_message", "")),
            error_code=str(data.get("error_code", "")),
            semantic_metadata=semantic,
            study_metadata=study,
            pipeline_progress={k: bool(v) for k, v in progress.items() if k in PIPELINE_CHECKPOINTS},
            job_progress=float(data.get("job_progress", 0.0) or 0.0),
            export_mode=str(data.get("export_mode", "")),
            content_template=str(data.get("content_template", "")),
            file_hash=str(data.get("file_hash", "")),
            cache_status=str(data.get("cache_status", "")),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )

    def update_job_checkpoint(
        self,
        job: TranscriptionJob,
        checkpoint: str,
        *,
        progress: Optional[float] = None,
    ) -> None:
        if checkpoint in PIPELINE_CHECKPOINTS:
            job.pipeline_progress[checkpoint] = True
        job.updated_at = _utc_now()
        if progress is not None:
            job.job_progress = max(0.0, min(1.0, progress))
