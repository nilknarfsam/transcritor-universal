from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from typing import Callable, Optional

from src.cache.cache_engine import CacheEngine, CacheLookupResult
from src.core.extraction_service import ExtractionService
from src.core.export_service import ExportService
from src.core.job_errors import classify_job_error, format_traceback
from src.core.log_service import get_logger
from src.core.performance_metrics import PerformanceMetrics
from src.core.persistent_queue import PersistentQueue
from src.core.settings_service import SettingsService
from src.core.transcription_service import TranscriptionService
from src.models.transcription_job import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    JobStatus,
    TranscriptionJob,
)


JobCallback = Callable[[TranscriptionJob], None]
VoidCallback = Callable[[], None]
ProgressCallback = Callable[[float, "QueueStats"], None]
RecoveryCallback = Callable[[dict], None]


@dataclass(frozen=True)
class QueueStats:
    total: int
    waiting: int
    processing: int
    completed: int
    errors: int
    cancelled: int

    @classmethod
    def from_jobs(cls, jobs: list[TranscriptionJob]) -> "QueueStats":
        counts = {s: 0 for s in JobStatus}
        for job in jobs:
            counts[job.status] = counts.get(job.status, 0) + 1
        return cls(
            total=len(jobs),
            waiting=counts.get(JobStatus.WAITING, 0),
            processing=counts.get(JobStatus.PROCESSING, 0),
            completed=counts.get(JobStatus.COMPLETED, 0),
            errors=counts.get(JobStatus.ERROR, 0),
            cancelled=counts.get(JobStatus.CANCELLED, 0),
        )


class QueueManager:
    def __init__(
        self,
        settings: SettingsService,
        on_job_updated: Optional[JobCallback] = None,
        on_queue_idle: Optional[VoidCallback] = None,
        on_status_message: Optional[Callable[[str], None]] = None,
        on_progress: Optional[ProgressCallback] = None,
        on_queue_recovered: Optional[RecoveryCallback] = None,
    ) -> None:
        self.settings = settings
        self._jobs: list[TranscriptionJob] = []
        self._selected_id: Optional[str] = None
        self._on_job_updated = on_job_updated
        self._on_queue_idle = on_queue_idle
        self._on_status_message = on_status_message
        self._on_progress = on_progress
        self._on_queue_recovered = on_queue_recovered
        self._transcription = TranscriptionService()
        self._extraction = ExtractionService()
        self._export = ExportService()
        self._cache = CacheEngine()
        self._persistent = PersistentQueue()
        self._logger = get_logger()
        self._worker: Optional[threading.Thread] = None
        self._stop_requested = False
        self._processing = False
        self._start_lock = threading.Lock()
        self._session_completed = 0
        self._session_errors = 0
        self._recovery_meta: dict = {}
        self._queue_restored = False
        self._last_cache_status = ""

    @property
    def jobs(self) -> list[TranscriptionJob]:
        return list(self._jobs)

    @property
    def is_processing(self) -> bool:
        return self._processing

    @property
    def stats(self) -> QueueStats:
        return QueueStats.from_jobs(self._jobs)

    @property
    def queue_restored(self) -> bool:
        return self._queue_restored

    @property
    def last_cache_status(self) -> str:
        return self._last_cache_status

    @property
    def cache_engine(self) -> CacheEngine:
        return self._cache

    @property
    def recovery_meta(self) -> dict:
        return dict(self._recovery_meta)

    @property
    def selected_job(self) -> Optional[TranscriptionJob]:
        if not self._selected_id:
            return None
        return self._get_job(self._selected_id)

    def get_overall_progress(self) -> float:
        """Progresso da sessão atual: itens finalizados / itens elegíveis."""
        stats = self.stats
        if not self._processing and stats.total == 0:
            return 0.0
        eligible = stats.completed + stats.errors + stats.cancelled + stats.processing + stats.waiting
        if eligible == 0:
            return 0.0
        done = stats.completed + stats.errors + stats.cancelled
        if stats.processing:
            active = [j for j in self._jobs if j.status == JobStatus.PROCESSING]
            partial = sum(j.job_progress for j in active) / len(active) if active else 0.5
            return min(0.99, (done + partial) / eligible)
        return done / eligible if eligible else 0.0

    def try_recover_queue(self, *, auto: bool = True) -> bool:
        """Recovery automático ao abrir o app."""
        raw = self._persistent.load()
        if not raw:
            return False
        return self._apply_restored_state(raw, auto=auto)

    def restore_last_queue(self) -> bool:
        """Restaura manualmente a última fila persistida."""
        return self.try_recover_queue(auto=False)

    def _apply_restored_state(self, raw: dict, *, auto: bool) -> bool:
        if self._processing:
            return False
        jobs, meta = self._persistent.restore_jobs(raw)
        if not jobs:
            if meta.get("corrupted_removed"):
                self._persistent.clear_state()
            return False

        self._jobs = jobs
        sel = str(raw.get("selected_id", "")).strip()
        self._selected_id = sel if self._get_job(sel) else (jobs[0].id if jobs else None)
        self._session_completed = int(raw.get("session_completed", 0))
        self._session_errors = int(raw.get("session_errors", 0))
        self._recovery_meta = meta
        self._queue_restored = True
        meta["auto"] = auto
        meta["restored_queue"] = True
        meta["recovery_used"] = True

        pending = [j for j in self._jobs if j.status in (JobStatus.WAITING, JobStatus.ERROR)]
        for job in self._jobs:
            self._notify(job)

        self._emit_progress()
        if self._on_queue_recovered:
            self._on_queue_recovered(meta)

        if auto and meta.get("was_processing") and pending:
            self._logger.info("Fila restaurada com %d item(ns) pendente(s).", len(pending))
        return True

    def select_job(self, job_id: Optional[str]) -> None:
        self._selected_id = job_id
        self._persist_queue()

    def add_files(self, paths: list[str]) -> list[TranscriptionJob]:
        added: list[TranscriptionJob] = []
        for path in paths:
            path = path.strip().strip('"')
            if not path or not os.path.isfile(path):
                self._logger.warning("Arquivo ignorado (inexistente): %s", path)
                continue
            job = TranscriptionJob(file_path=path)
            job.export_mode = self.settings.export_mode
            job.content_template = self.settings.content_template
            if not job.is_supported():
                info = classify_job_error(
                    ValueError("Tipo de arquivo não suportado."), path
                )
                job.status = JobStatus.ERROR
                job.error_message = info.user_message
                job.error_code = info.error_code
                self._logger.error("Tipo não suportado: %s", path)
            output_dir = self.settings.resolve_output_dir(path)
            fmt = self.settings.default_export_format  # type: ignore[arg-type]
            job.output_path = ExportService.build_output_path(path, output_dir, fmt)
            self._jobs.append(job)
            added.append(job)
            self._notify(job)
        self._persist_queue()
        self._emit_progress()
        return added

    def remove_selected(self) -> bool:
        job = self.selected_job
        if not job:
            return False
        if job.status == JobStatus.PROCESSING:
            return False
        self._jobs = [j for j in self._jobs if j.id != job.id]
        if self._selected_id == job.id:
            self._selected_id = None
        self._persist_queue()
        self._emit_progress()
        return True

    def clear_queue(self) -> None:
        if self._processing:
            self._jobs = [j for j in self._jobs if j.status == JobStatus.PROCESSING]
        else:
            self._jobs = []
            self._selected_id = None
        self._persist_queue()
        self._emit_progress()

    def clear_cache(self) -> tuple[int, int]:
        return self._cache.clear_all()

    def start_queue(self) -> bool:
        with self._start_lock:
            if self._processing:
                self._emit_status("A fila já está em processamento.")
                self._logger.warning("Tentativa de iniciar fila duplicada ignorada.")
                return False
            pending = [j for j in self._jobs if j.status in (JobStatus.WAITING, JobStatus.ERROR)]
            if not pending:
                self._emit_status("Nenhum item aguardando na fila.")
                return False
            self._stop_requested = False
            self._processing = True
            if not self._queue_restored:
                self._session_completed = 0
                self._session_errors = 0
            self._worker = threading.Thread(target=self._process_queue, daemon=True)
            self._worker.start()
            self._logger.info("Fila iniciada com %d item(ns) pendente(s).", len(pending))
            self._persist_queue(is_processing=True)
            self._emit_progress()
            return True

    def cancel_queue(self) -> bool:
        if not self._processing:
            self._emit_status("Nenhuma fila em processamento.")
            return False
        self._stop_requested = True
        self._emit_status("Cancelando fila após o item atual…")
        self._logger.info("Cancelamento de fila solicitado.")
        self._persist_queue(is_processing=True, stop_requested=True)
        return True

    def resolve_output_folder_for_job(self, job: Optional[TranscriptionJob]) -> Optional[str]:
        if job and job.output_path:
            folder = os.path.dirname(os.path.abspath(job.output_path))
            if os.path.isdir(folder):
                return folder
        if job:
            folder = self.settings.resolve_output_dir(job.file_path)
            if os.path.isdir(folder):
                return folder
        folder = self.settings.output_folder.strip()
        if folder and os.path.isdir(folder):
            return folder
        return None

    def _process_queue(self) -> None:
        cancelled_count = 0
        recovery_used = self._queue_restored
        try:
            for job in list(self._jobs):
                if self._stop_requested:
                    if job.status == JobStatus.WAITING:
                        job.status = JobStatus.CANCELLED
                        job.error_message = "Cancelado pelo usuário."
                        cancelled_count += 1
                        self._notify(job)
                    continue
                if job.status not in (JobStatus.WAITING, JobStatus.ERROR):
                    continue
                self._process_job(job)
                self._emit_progress()
        finally:
            was_cancelled = self._stop_requested
            self._processing = False
            self._stop_requested = False
            self._queue_restored = False

            if was_cancelled and (self._session_completed or self._session_errors or cancelled_count):
                self.settings.add_partial_queue_history(
                    self._session_completed,
                    self._session_errors,
                    cancelled_count,
                    self.stats.total,
                    reason="cancelada",
                    recovery_used=recovery_used,
                    restored_queue=recovery_used,
                )

            self._persist_queue()
            self._emit_progress()
            if self._on_queue_idle:
                self._on_queue_idle()
            msg = "Fila cancelada." if was_cancelled else "Fila finalizada."
            self._emit_status(msg)
            self._logger.info(msg)

    def _process_job(self, job: TranscriptionJob) -> None:
        if self._stop_requested:
            return

        metrics = PerformanceMetrics()
        metrics.start_total()
        recovery_used = self._queue_restored

        job.status = JobStatus.PROCESSING
        job.error_message = ""
        job.error_code = ""
        job.export_mode = self.settings.export_mode
        job.content_template = self.settings.content_template
        job.job_progress = 0.05
        self._notify(job)
        self._emit_status(f"Processando: {job.file_name}")
        self._logger.info("Processando job: %s (%s)", job.file_name, job.file_type)

        try:
            if not os.path.isfile(job.file_path):
                raise FileNotFoundError(job.file_path)

            language = self.settings.language
            model_name = self.settings.whisper_model
            export_mode = self.settings.export_mode
            template = self.settings.content_template
            ext = job.extension

            cache_lookup = self._safe_cache_lookup(job.file_path, export_mode, template, language)
            if cache_lookup.fingerprint:
                job.file_hash = cache_lookup.file_hash

            text = ""
            source_kind = ""
            reused = False

            if cache_lookup.hit and export_mode == "notebooklm":
                cached_out = self._cache.read_stage(cache_lookup.file_hash, "notebooklm")
                if cached_out:
                    text = cache_lookup.raw_text or self._cache.read_stage(cache_lookup.file_hash, "whisper") or self._cache.read_stage(cache_lookup.file_hash, "ocr")
                    metrics.cache_hit = True
                    metrics.reused_pipeline = True
                    job.cache_status = "hit"
                    self._last_cache_status = "hit"
                    reused = True
                    for stage in cache_lookup.reused_stages:
                        self._persistent.update_job_checkpoint(job, stage)
                    job.job_progress = 0.85
                    self._notify(job)
                    self._write_cached_export(job, cached_out, metrics, recovery_used)
                    return

            if cache_lookup.raw_text:
                text = cache_lookup.raw_text
                metrics.cache_hit = cache_lookup.hit
                metrics.reused_pipeline = True
                job.cache_status = "hit" if cache_lookup.hit else "partial"
                self._last_cache_status = job.cache_status or "hit"
                reused = True
                for stage in cache_lookup.reused_stages:
                    self._persistent.update_job_checkpoint(job, stage)
                if "whisper" in cache_lookup.reused_stages:
                    self._persistent.update_job_checkpoint(job, "whisper", progress=0.4)
                if "ocr" in cache_lookup.reused_stages:
                    self._persistent.update_job_checkpoint(job, "ocr", progress=0.4)
            else:
                job.cache_status = "miss"
                self._last_cache_status = "miss"

            if not text:
                if ext in (AUDIO_EXTENSIONS | VIDEO_EXTENSIONS):
                    metrics.start_whisper()
                    text = self._transcription.transcribe_media(
                        job.file_path, language=language, model_name=model_name
                    )
                    metrics.stop_whisper()
                    source_kind = "whisper"
                    self._persistent.update_job_checkpoint(job, "whisper", progress=0.45)
                    self._cache.save_stage(
                        job.file_path, "whisper", text,
                        export_mode=export_mode, template=template, language=language,
                    )
                elif self._extraction.can_extract(job):
                    metrics.start_ocr()
                    text = self._extraction.extract(job, language=language)
                    metrics.stop_ocr()
                    source_kind = "ocr" if ext in IMAGE_EXTENSIONS else "ocr"
                    self._persistent.update_job_checkpoint(job, "ocr", progress=0.45)
                    self._cache.save_stage(
                        job.file_path, "ocr", text,
                        export_mode=export_mode, template=template, language=language,
                    )
                else:
                    raise ValueError("Tipo de arquivo não suportado para transcrição.")

            if self._stop_requested:
                job.status = JobStatus.CANCELLED
                job.error_message = "Cancelado durante o processamento."
                self._persist_queue(is_processing=True)
                return

            job.result_text = text
            job.job_progress = 0.55
            self._persist_queue(is_processing=True)
            self._notify(job)

            if self._stop_requested:
                job.status = JobStatus.CANCELLED
                job.error_message = "Cancelado durante o processamento."
                return

            output_dir = self.settings.resolve_output_dir(job.file_path)
            fmt = self.settings.default_export_format  # type: ignore[arg-type]

            if reused and export_mode != "raw" and self._cache.read_stage(cache_lookup.file_hash, export_mode if export_mode in ("clean", "semantic") else "notebooklm"):
                stage_key = "notebooklm" if export_mode == "notebooklm" else "semantic" if export_mode == "ai_ready" else "clean"
                cached_content = self._cache.read_stage(cache_lookup.file_hash, stage_key)
                if cached_content and export_mode == "notebooklm":
                    self._write_cached_export(job, cached_content, metrics, recovery_used)
                    return

            metrics.start_semantic()
            metrics.start_export()
            job.output_path, stage = self._export.save_auto(
                job.file_path,
                text,
                output_dir,
                fmt,
                export_mode=export_mode,
                content_template=template,
                language=language,
                model=model_name,
            )
            metrics.stop_semantic()
            metrics.stop_export()
            metrics.finish_total()

            if stage:
                self._persistent.update_job_checkpoint(job, "clean", progress=0.7)
                if export_mode in ("ai_ready", "notebooklm"):
                    self._persistent.update_job_checkpoint(job, "semantic", progress=0.85)
                if export_mode == "notebooklm":
                    self._persistent.update_job_checkpoint(job, "notebooklm", progress=0.95)

            chunks_json = ""
            if stage and stage.metadata.get("chunks"):
                chunks_json = json.dumps(stage.metadata["chunks"], ensure_ascii=False)

            self._cache.save_pipeline_artifacts(
                job.file_path,
                raw_text=text,
                stage_result_content=stage.content if stage else None,
                stage_name=stage.pipeline_stage if stage else export_mode,
                export_mode=export_mode,
                template=template,
                language=language,
                chunks_json=chunks_json,
                source_kind=source_kind,
            )

            job.status = JobStatus.COMPLETED
            job.job_progress = 1.0
            self._session_completed += 1
            pipeline_stage = stage.pipeline_stage if stage else export_mode
            semantic_meta: dict = stage.metadata if stage else {}
            job.semantic_metadata = {
                "reference_count": semantic_meta.get("reference_count", 0),
                "highlight_count": semantic_meta.get("highlight_count", 0),
                "chunk_count": semantic_meta.get("chunk_count", 0),
                "topics": semantic_meta.get("topics", []),
                "semantic_ready": semantic_meta.get("semantic_ready", False),
            }
            hist_fields = metrics.to_history_fields()
            self.settings.add_history_entry(
                job.file_name,
                job.file_type,
                status="concluído",
                output_path=job.output_path,
                export_mode=export_mode,
                template_usado=template,
                pipeline_stage=pipeline_stage,
                tipo_documento=template,
                referencias=str(job.semantic_metadata.get("reference_count", 0)),
                highlights=str(job.semantic_metadata.get("highlight_count", 0)),
                chunks=str(job.semantic_metadata.get("chunk_count", 0)),
                topicos=", ".join(job.semantic_metadata.get("topics", [])[:5]),
                cache_hit=hist_fields["cache_hit"],
                recovery_used="sim" if recovery_used else "não",
                restored_queue="sim" if self._recovery_meta.get("restored_queue") else "não",
                processing_time=hist_fields["processing_time"],
                reused_pipeline=hist_fields["reused_pipeline"],
                tempo_whisper=hist_fields["tempo_whisper"],
                tempo_ocr=hist_fields["tempo_ocr"],
                tempo_semantic=hist_fields["tempo_semantic"],
            )
            self._logger.info("Concluído: %s -> %s", job.file_name, job.output_path)
        except Exception as exc:
            info = classify_job_error(exc, job.file_path)
            job.status = JobStatus.ERROR
            job.error_message = info.user_message
            job.error_code = info.error_code
            job.result_text = ""
            self._session_errors += 1
            metrics.finish_total()
            self.settings.add_history_entry(
                job.file_name,
                job.file_type,
                status="erro",
                message=info.user_message,
                recovery_used="sim" if recovery_used else "não",
            )
            self._logger.error(
                "Erro no job %s [%s]: %s\n%s",
                job.file_name,
                info.error_code,
                info.user_message,
                format_traceback(exc),
            )

        self._notify(job)
        self._persist_queue(is_processing=True)

    def _write_cached_export(
        self,
        job: TranscriptionJob,
        content: str,
        metrics: PerformanceMetrics,
        recovery_used: bool,
    ) -> None:
        output_dir = self.settings.resolve_output_dir(job.file_path)
        fmt = self.settings.default_export_format  # type: ignore[arg-type]
        job.output_path = ExportService.build_output_path(job.file_path, output_dir, fmt)
        os.makedirs(os.path.dirname(os.path.abspath(job.output_path)), exist_ok=True)
        with open(job.output_path, "w", encoding="utf-8") as f:
            f.write(content)
        metrics.stop_export()
        metrics.finish_total()
        job.status = JobStatus.COMPLETED
        job.job_progress = 1.0
        self._session_completed += 1
        self.settings.add_history_entry(
            job.file_name,
            job.file_type,
            status="concluído",
            output_path=job.output_path,
            export_mode=self.settings.export_mode,
            template_usado=self.settings.content_template,
            pipeline_stage="notebooklm",
            cache_hit="sim",
            recovery_used="sim" if recovery_used else "não",
            processing_time=f"{metrics.total_seconds:.2f}s",
            reused_pipeline="sim",
        )
        self._notify(job)

    def _safe_cache_lookup(
        self,
        path: str,
        export_mode: str,
        template: str,
        language: str,
    ) -> CacheLookupResult:
        try:
            return self._cache.lookup(
                path, export_mode=export_mode, template=template, language=language
            )
        except (OSError, FileNotFoundError) as exc:
            self._logger.warning("Cache lookup falhou: %s", exc)
            return CacheLookupResult()

    def _persist_queue(self, *, is_processing: Optional[bool] = None) -> None:
        self._persistent.save(
            self._jobs,
            selected_id=self._selected_id,
            is_processing=is_processing if is_processing is not None else self._processing,
            stop_requested=self._stop_requested,
            session_completed=self._session_completed,
            session_errors=self._session_errors,
            export_mode=self.settings.export_mode,
            content_template=self.settings.content_template,
        )

    def _get_job(self, job_id: str) -> Optional[TranscriptionJob]:
        for job in self._jobs:
            if job.id == job_id:
                return job
        return None

    def _notify(self, job: TranscriptionJob) -> None:
        from src.core.persistent_queue import _utc_now

        job.updated_at = _utc_now()
        if self._on_job_updated:
            self._on_job_updated(job)

    def _emit_status(self, message: str) -> None:
        if self._on_status_message:
            self._on_status_message(message)

    def _emit_progress(self) -> None:
        if self._on_progress:
            self._on_progress(self.get_overall_progress(), self.stats)
