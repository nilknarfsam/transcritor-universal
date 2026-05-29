"""Orquestração da fila de transcrição: persistência, worker thread e callbacks da UI."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Callable, Optional

from src.cache.cache_engine import CacheEngine
from src.core.export_service import ExportService
from src.core.job_errors import classify_job_error
from src.core.job_processor import JobProcessor, QueueRunContext
from src.core.log_service import get_logger
from src.core.persistent_queue import PersistentQueue, _utc_now
from src.core.settings_service import SettingsService
from src.models.transcription_job import JobStatus, TranscriptionJob


JobCallback = Callable[[TranscriptionJob], None]
VoidCallback = Callable[[], None]
ProgressCallback = Callable[[float, "QueueStats"], None]
RecoveryCallback = Callable[[dict], None]


@dataclass(frozen=True)
class QueueStats:
    """Contadores agregados da fila para a barra de status."""

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
    """Gerencia estado da fila, persistência, worker thread e delega processamento ao ``JobProcessor``."""

    def __init__(
        self,
        settings: SettingsService,
        on_job_updated: Optional[JobCallback] = None,
        on_queue_idle: Optional[VoidCallback] = None,
        on_status_message: Optional[Callable[[str], None]] = None,
        on_progress: Optional[ProgressCallback] = None,
        on_queue_recovered: Optional[RecoveryCallback] = None,
        *,
        job_processor: Optional[JobProcessor] = None,
    ) -> None:
        self.settings = settings
        self._jobs: list[TranscriptionJob] = []
        self._jobs_lock = threading.RLock()
        self._selected_id: Optional[str] = None
        self._on_job_updated = on_job_updated
        self._on_queue_idle = on_queue_idle
        self._on_status_message = on_status_message
        self._on_progress = on_progress
        self._on_queue_recovered = on_queue_recovered
        self._cache = CacheEngine()
        self._processor = job_processor or JobProcessor(settings, cache=self._cache)
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
        with self._jobs_lock:
            return list(self._jobs)

    @property
    def is_processing(self) -> bool:
        return self._processing

    @property
    def stats(self) -> QueueStats:
        return QueueStats.from_jobs(self.jobs)

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
    def job_processor(self) -> JobProcessor:
        return self._processor

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
        eligible = (
            stats.completed
            + stats.errors
            + stats.cancelled
            + stats.processing
            + stats.waiting
        )
        if eligible == 0:
            return 0.0
        done = stats.completed + stats.errors + stats.cancelled
        if stats.processing:
            with self._jobs_lock:
                active = [j for j in self._jobs if j.status == JobStatus.PROCESSING]
            partial = (
                sum(j.job_progress for j in active) / len(active) if active else 0.5
            )
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

        with self._jobs_lock:
            self._jobs = jobs
            sel = str(raw.get("selected_id", "")).strip()
            self._selected_id = (
                sel if self._get_job_unlocked(sel) else (jobs[0].id if jobs else None)
            )
        self._session_completed = int(raw.get("session_completed", 0))
        self._session_errors = int(raw.get("session_errors", 0))
        self._recovery_meta = meta
        self._queue_restored = True
        meta["auto"] = auto
        meta["restored_queue"] = True
        meta["recovery_used"] = True

        with self._jobs_lock:
            pending = [
                j for j in self._jobs
                if j.status in (JobStatus.WAITING, JobStatus.ERROR)
            ]
            jobs_snapshot = list(self._jobs)
        for job in jobs_snapshot:
            self._notify(job)

        self._emit_progress()
        if self._on_queue_recovered:
            self._safe_ui("on_queue_recovered", self._on_queue_recovered, meta)

        if auto and meta.get("was_processing") and pending:
            self._logger.info("Fila restaurada com %d item(ns) pendente(s).", len(pending))
        return True

    def select_job(self, job_id: Optional[str]) -> None:
        self._selected_id = job_id
        self._persist_queue()

    def add_files(self, paths: list[str]) -> list[TranscriptionJob]:
        """Adiciona arquivos válidos à fila; tipos inválidos entram como erro."""
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
            with self._jobs_lock:
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
        with self._jobs_lock:
            self._jobs = [j for j in self._jobs if j.id != job.id]
            if self._selected_id == job.id:
                self._selected_id = None
        self._persist_queue()
        self._emit_progress()
        return True

    def clear_queue(self) -> None:
        with self._jobs_lock:
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
            with self._jobs_lock:
                pending = [
                    j for j in self._jobs
                    if j.status in (JobStatus.WAITING, JobStatus.ERROR)
                ]
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
            with self._jobs_lock:
                jobs_snapshot = list(self._jobs)
            for job in jobs_snapshot:
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
                self._safe_ui("on_queue_idle", self._on_queue_idle)
            self._release_whisper_if_idle()
            msg = "Fila cancelada." if was_cancelled else "Fila finalizada."
            self._emit_status(msg)
            self._logger.info(msg)

    def _process_job(self, job: TranscriptionJob) -> None:
        ctx = QueueRunContext(
            is_stop_requested=lambda: self._stop_requested,
            on_notify=self._notify,
            on_persist=self._persist_queue,
            on_status=self._emit_status,
            on_completed=lambda: setattr(self, "_session_completed", self._session_completed + 1),
            on_error=lambda: setattr(self, "_session_errors", self._session_errors + 1),
            set_last_cache_status=lambda status: setattr(self, "_last_cache_status", status),
            recovery_meta=self._recovery_meta,
            queue_restored=self._queue_restored,
        )
        self._processor.process(job, ctx)

    def _persist_queue(
        self,
        *,
        is_processing: Optional[bool] = None,
        stop_requested: Optional[bool] = None,
    ) -> None:
        with self._jobs_lock:
            jobs_copy = list(self._jobs)
            selected_id = self._selected_id
        self._persistent.save(
            jobs_copy,
            selected_id=selected_id,
            is_processing=is_processing if is_processing is not None else self._processing,
            stop_requested=self._stop_requested if stop_requested is None else stop_requested,
            session_completed=self._session_completed,
            session_errors=self._session_errors,
            export_mode=self.settings.export_mode,
            content_template=self.settings.content_template,
        )

    def _get_job(self, job_id: str) -> Optional[TranscriptionJob]:
        with self._jobs_lock:
            return self._get_job_unlocked(job_id)

    def _get_job_unlocked(self, job_id: str) -> Optional[TranscriptionJob]:
        for job in self._jobs:
            if job.id == job_id:
                return job
        return None

    def _release_whisper_if_idle(self) -> None:
        """Libera o modelo Whisper da RAM quando a fila termina (sessões longas)."""
        transcription = self._processor.transcription
        if transcription.is_model_loaded:
            self._logger.debug("Liberando modelo Whisper da memória após fim da fila.")
            transcription.unload_model()

    def _safe_ui(self, label: str, fn: Callable[..., None], *args, **kwargs) -> None:
        try:
            fn(*args, **kwargs)
        except Exception:
            self._logger.exception("Callback UI falhou (%s)", label)

    def _notify(self, job: TranscriptionJob) -> None:
        job.updated_at = _utc_now()
        if self._on_job_updated:
            self._safe_ui("on_job_updated", self._on_job_updated, job)

    def _emit_status(self, message: str) -> None:
        if self._on_status_message:
            self._safe_ui("on_status_message", self._on_status_message, message)

    def _emit_progress(self) -> None:
        if self._on_progress:
            self._safe_ui(
                "on_progress",
                self._on_progress,
                self.get_overall_progress(),
                self.stats,
            )
