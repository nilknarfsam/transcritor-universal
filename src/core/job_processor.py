from __future__ import annotations

import json
import os
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
from src.datasets.dataset_engine import get_dataset_engine
from src.datasets.exporters.dataset_exporter import DatasetExporter
from src.library import get_library
from src.models.transcription_job import (
    AUDIO_EXTENSIONS,
    VIDEO_EXTENSIONS,
    JobStatus,
    TranscriptionJob,
)
from src.study import StudyExporter
from src.study.study_engine import StudyResult


@dataclass
class QueueRunContext:
    """Contexto de execução fornecido pelo QueueManager (fila, cancelamento, persistência)."""

    is_stop_requested: Callable[[], bool]
    on_notify: Callable[[TranscriptionJob], None]
    on_persist: Callable[..., None]
    on_status: Callable[[str], None]
    on_completed: Callable[[], None]
    on_error: Callable[[], None]
    set_last_cache_status: Callable[[str], None]
    recovery_meta: dict
    queue_restored: bool


class JobProcessor:
    """Pipeline de processamento de um job: cache, Whisper/OCR, exportação e pós-processamento."""

    def __init__(
        self,
        settings: SettingsService,
        *,
        cache: Optional[CacheEngine] = None,
        transcription: Optional[TranscriptionService] = None,
        extraction: Optional[ExtractionService] = None,
        export: Optional[ExportService] = None,
        persistent: Optional[PersistentQueue] = None,
    ) -> None:
        self.settings = settings
        self._transcription = transcription or TranscriptionService()
        self._extraction = extraction or ExtractionService()
        self._export = export or ExportService()
        self._cache = cache or CacheEngine()
        self._persistent = persistent or PersistentQueue()
        self._logger = get_logger()

    @property
    def cache(self) -> CacheEngine:
        return self._cache

    @property
    def transcription(self) -> TranscriptionService:
        return self._transcription

    def process(self, job: TranscriptionJob, ctx: QueueRunContext) -> None:
        """Executa o pipeline completo de um job (mutação in-place no ``TranscriptionJob``)."""
        if ctx.is_stop_requested():
            return

        metrics = PerformanceMetrics()
        metrics.start_total()
        recovery_used = ctx.queue_restored

        job.status = JobStatus.PROCESSING
        job.error_message = ""
        job.error_code = ""
        job.export_mode = self.settings.export_mode
        job.content_template = self.settings.content_template
        job.job_progress = 0.05
        ctx.on_notify(job)
        ctx.on_status(f"Processando: {job.file_name}")
        self._logger.info("Processando job: %s (%s)", job.file_name, job.file_type)

        try:
            if not os.path.isfile(job.file_path):
                raise FileNotFoundError(job.file_path)

            language = self.settings.language
            model_name = self.settings.whisper_model
            export_mode = self.settings.export_mode
            template = self.settings.content_template

            cache_lookup = self._safe_cache_lookup(job.file_path, export_mode, template, language)
            if cache_lookup.fingerprint:
                job.file_hash = cache_lookup.file_hash

            text, source_kind, reused = self._resolve_text(
                job,
                cache_lookup,
                metrics,
                language=language,
                model_name=model_name,
                export_mode=export_mode,
                template=template,
                ctx=ctx,
            )

            if text is None:
                return

            if ctx.is_stop_requested():
                job.status = JobStatus.CANCELLED
                job.error_message = "Cancelado durante o processamento."
                ctx.on_persist(is_processing=True)
                return

            job.result_text = text
            job.job_progress = 0.55
            ctx.on_persist(is_processing=True)
            ctx.on_notify(job)

            if ctx.is_stop_requested():
                job.status = JobStatus.CANCELLED
                job.error_message = "Cancelado durante o processamento."
                return

            if self._try_cached_export_shortcut(
                job, cache_lookup, reused, export_mode, metrics, recovery_used, ctx
            ):
                return

            self._export_and_finalize(
                job,
                text=text,
                source_kind=source_kind,
                cache_lookup=cache_lookup,
                metrics=metrics,
                language=language,
                model_name=model_name,
                export_mode=export_mode,
                template=template,
                recovery_used=recovery_used,
                ctx=ctx,
            )
            self._logger.info("Concluído: %s -> %s", job.file_name, job.output_path)
        except Exception as exc:
            info = classify_job_error(exc, job.file_path)
            job.status = JobStatus.ERROR
            job.error_message = info.user_message
            job.error_code = info.error_code
            job.result_text = ""
            ctx.on_error()
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

        ctx.on_notify(job)
        ctx.on_persist(is_processing=True)

    def _resolve_text(
        self,
        job: TranscriptionJob,
        cache_lookup: CacheLookupResult,
        metrics: PerformanceMetrics,
        *,
        language: str,
        model_name: str,
        export_mode: str,
        template: str,
        ctx: QueueRunContext,
    ) -> tuple[str | None, str, bool]:
        """Obtém texto bruto: cache, Whisper ou extração/OCR. Retorna ``None`` se fluxo encerrado cedo."""
        ext = job.extension
        source_kind = ""
        reused = False

        if cache_lookup.hit and export_mode == "notebooklm":
            cached_out = self._cache.read_stage(cache_lookup.file_hash, "notebooklm")
            if cached_out:
                metrics.cache_hit = True
                metrics.reused_pipeline = True
                job.cache_status = "hit"
                ctx.set_last_cache_status("hit")
                for stage in cache_lookup.reused_stages:
                    self._persistent.update_job_checkpoint(job, stage)
                job.job_progress = 0.85
                ctx.on_notify(job)
                self._write_cached_export(job, cached_out, metrics, ctx.queue_restored, ctx)
                return None, "", True

        text = ""
        if cache_lookup.raw_text:
            text = cache_lookup.raw_text
            metrics.cache_hit = cache_lookup.hit
            metrics.reused_pipeline = True
            job.cache_status = "hit" if cache_lookup.hit else "partial"
            ctx.set_last_cache_status(job.cache_status or "hit")
            reused = True
            for stage in cache_lookup.reused_stages:
                self._persistent.update_job_checkpoint(job, stage)
            if "whisper" in cache_lookup.reused_stages:
                self._persistent.update_job_checkpoint(job, "whisper", progress=0.4)
            if "ocr" in cache_lookup.reused_stages:
                self._persistent.update_job_checkpoint(job, "ocr", progress=0.4)
        else:
            job.cache_status = "miss"
            ctx.set_last_cache_status("miss")

        if not text:
            text, source_kind = self._extract_fresh_text(
                job,
                ext=ext,
                metrics=metrics,
                language=language,
                model_name=model_name,
                export_mode=export_mode,
                template=template,
            )

        return text, source_kind, reused

    def _extract_fresh_text(
        self,
        job: TranscriptionJob,
        *,
        ext: str,
        metrics: PerformanceMetrics,
        language: str,
        model_name: str,
        export_mode: str,
        template: str,
    ) -> tuple[str, str]:
        """Transcrição Whisper ou extração de documento/imagem; persiste estágio no cache."""
        if ext in (AUDIO_EXTENSIONS | VIDEO_EXTENSIONS):
            metrics.start_whisper()
            text = self._transcription.transcribe_media(
                job.file_path, language=language, model_name=model_name
            )
            metrics.stop_whisper()
            source_kind = "whisper"
            self._persistent.update_job_checkpoint(job, "whisper", progress=0.45)
            self._cache.save_stage(
                job.file_path,
                "whisper",
                text,
                export_mode=export_mode,
                template=template,
                language=language,
            )
            return text, source_kind

        if self._extraction.can_extract(job):
            metrics.start_ocr()
            text = self._extraction.extract(job, language=language)
            metrics.stop_ocr()
            source_kind = "ocr"
            self._persistent.update_job_checkpoint(job, "ocr", progress=0.45)
            self._cache.save_stage(
                job.file_path,
                "ocr",
                text,
                export_mode=export_mode,
                template=template,
                language=language,
            )
            return text, source_kind

        raise ValueError("Tipo de arquivo não suportado para transcrição.")

    def _try_cached_export_shortcut(
        self,
        job: TranscriptionJob,
        cache_lookup: CacheLookupResult,
        reused: bool,
        export_mode: str,
        metrics: PerformanceMetrics,
        recovery_used: bool,
        ctx: QueueRunContext,
    ) -> bool:
        if not (
            reused
            and export_mode != "raw"
            and cache_lookup.fingerprint
            and self._cache.read_stage(
                cache_lookup.file_hash,
                export_mode if export_mode in ("clean", "semantic") else "notebooklm",
            )
        ):
            return False

        stage_key = (
            "notebooklm"
            if export_mode == "notebooklm"
            else "semantic"
            if export_mode == "ai_ready"
            else "clean"
        )
        cached_content = self._cache.read_stage(cache_lookup.file_hash, stage_key)
        if cached_content and export_mode == "notebooklm":
            self._write_cached_export(job, cached_content, metrics, recovery_used, ctx)
            return True
        return False

    def _export_and_finalize(
        self,
        job: TranscriptionJob,
        *,
        text: str,
        source_kind: str,
        cache_lookup: CacheLookupResult,
        metrics: PerformanceMetrics,
        language: str,
        model_name: str,
        export_mode: str,
        template: str,
        recovery_used: bool,
        ctx: QueueRunContext,
    ) -> None:
        output_dir = self.settings.resolve_output_dir(job.file_path)
        fmt = self.settings.default_export_format  # type: ignore[arg-type]
        lib_ctx = self._library_export_context(job)

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
            library_context=lib_ctx,
        )
        metrics.stop_semantic()
        metrics.stop_export()
        metrics.finish_total()

        if stage:
            self._persistent.update_job_checkpoint(job, "clean", progress=0.7)
            if export_mode in ("ai_ready", "notebooklm", "study_mode"):
                self._persistent.update_job_checkpoint(job, "semantic", progress=0.85)
            if export_mode == "study_mode":
                self._persistent.update_job_checkpoint(job, "study", progress=0.9)
            if export_mode in ("notebooklm", "study_mode"):
                self._persistent.update_job_checkpoint(job, "notebooklm", progress=0.93)

        study_exports: dict[str, str] = {}
        if stage and stage.metadata.get("study_package"):
            study_exports = self._write_study_exports(job.output_path, stage.metadata["study_package"])

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
        ctx.on_completed()
        pipeline_stage = stage.pipeline_stage if stage else export_mode
        semantic_meta: dict = stage.metadata if stage else {}
        job.semantic_metadata = {
            "reference_count": semantic_meta.get("reference_count", 0),
            "highlight_count": semantic_meta.get("highlight_count", 0),
            "chunk_count": semantic_meta.get("chunk_count", 0),
            "topics": semantic_meta.get("topics", []),
            "semantic_ready": semantic_meta.get("semantic_ready", False),
        }
        if semantic_meta.get("study_ready") or semantic_meta.get("study_package"):
            job.study_metadata = {
                "study_ready": True,
                "flashcards_count": semantic_meta.get("flashcards_count", 0),
                "quizzes_count": semantic_meta.get("quizzes_count", 0),
                "difficulty": semantic_meta.get("difficulty", ""),
                "study_exports": study_exports,
                "study_package": semantic_meta.get("study_package", {}),
            }

        catalog_id, rel_summary, graph_fields, dataset_meta = self._run_knowledge_post_processing(
            job,
            export_mode=export_mode,
            file_hash=job.file_hash or (cache_lookup.file_hash if cache_lookup.fingerprint else ""),
            pipeline_stage=pipeline_stage,
            stage_metadata=semantic_meta,
        )
        if dataset_meta:
            self._persistent.update_job_checkpoint(job, "dataset", progress=0.98)
            pipeline_stage = "dataset"

        hist_fields = metrics.to_history_fields()
        ws_name, col_name = self._library_names()
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
            restored_queue="sim" if ctx.recovery_meta.get("restored_queue") else "não",
            processing_time=hist_fields["processing_time"],
            reused_pipeline=hist_fields["reused_pipeline"],
            tempo_whisper=hist_fields["tempo_whisper"],
            tempo_ocr=hist_fields["tempo_ocr"],
            tempo_semantic=hist_fields["tempo_semantic"],
            workspace=ws_name,
            collection=col_name,
            catalog_id=catalog_id,
            semantic_relationships=rel_summary,
            flashcards_count=str(job.study_metadata.get("flashcards_count", "")),
            quizzes_count=str(job.study_metadata.get("quizzes_count", "")),
            study_mode="sim" if export_mode == "study_mode" else "",
            difficulty=str(job.study_metadata.get("difficulty", "")),
            study_exports=StudyExporter.paths_display(study_exports) if study_exports else "",
            graph_node_id=graph_fields.get("graph_node_id", ""),
            related_documents_count=graph_fields.get("related_documents_count", ""),
            semantic_search_hits=graph_fields.get("semantic_search_hits", ""),
            graph_updated_at=graph_fields.get("graph_updated_at", ""),
            knowledge_readiness_score=str(dataset_meta.get("knowledge_readiness_score", "")),
            dataset_id=dataset_meta.get("dataset_id", ""),
        )

    def _write_cached_export(
        self,
        job: TranscriptionJob,
        content: str,
        metrics: PerformanceMetrics,
        recovery_used: bool,
        ctx: QueueRunContext,
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
        ctx.on_completed()
        catalog_id, rel_summary, graph_fields, _dataset_meta = self._run_knowledge_post_processing(
            job,
            export_mode="notebooklm",
            file_hash=job.file_hash,
            pipeline_stage="notebooklm",
            stage_metadata=job.semantic_metadata,
        )
        ws_name, col_name = self._library_names()
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
            workspace=ws_name,
            collection=col_name,
            catalog_id=catalog_id,
            semantic_relationships=rel_summary,
            graph_node_id=graph_fields.get("graph_node_id", ""),
            related_documents_count=graph_fields.get("related_documents_count", ""),
            semantic_search_hits=graph_fields.get("semantic_search_hits", ""),
            graph_updated_at=graph_fields.get("graph_updated_at", ""),
        )
        ctx.on_notify(job)

    def _run_knowledge_post_processing(
        self,
        job: TranscriptionJob,
        *,
        export_mode: str,
        file_hash: str,
        pipeline_stage: str,
        stage_metadata: dict,
    ) -> tuple[str, str, dict[str, str], dict]:
        """Catalogação, grafo e datasets — somente se ``features.knowledge_pipeline`` ou modo avançado."""
        if not self.settings.should_run_knowledge_pipeline(export_mode):
            self._logger.debug(
                "Pipeline de conhecimento ignorado (modo=%s, flag=%s).",
                export_mode,
                self.settings.knowledge_pipeline,
            )
            return "", "", {}, {}

        if self.settings.knowledge_pipeline_auto_enabled(export_mode):
            self._logger.info(
                "Pipeline de conhecimento ativado temporariamente para modo %s.",
                export_mode,
            )

        catalog_id, rel_summary, graph_fields = self._register_in_library(
            job,
            file_hash=file_hash,
            pipeline_stage=pipeline_stage,
            stage_metadata=stage_metadata,
        )

        dataset_meta: dict = {}
        if catalog_id and export_mode in ("ai_ready", "notebooklm", "study_mode"):
            dataset_meta = self._update_datasets(
                job,
                catalog_id=catalog_id,
                stage_metadata=stage_metadata,
            )

        return catalog_id, rel_summary, graph_fields, dataset_meta

    def _library_names(self) -> tuple[str, str]:
        lib = get_library()
        _, ws_name = lib.resolve_workspace(self.settings.workspace_id)
        _, col_name = lib.resolve_collection(
            self.settings.collection_id,
            self.settings.collection_name,
        )
        return ws_name, col_name

    def _library_export_context(
        self,
        job: TranscriptionJob,
        *,
        semantic_metadata: dict | None = None,
    ) -> dict:
        lib = get_library()
        _, ws_name = lib.resolve_workspace(self.settings.workspace_id)
        _, col_name = lib.resolve_collection(
            self.settings.collection_id,
            self.settings.collection_name,
        )
        meta = semantic_metadata or {}
        chunk_count = int(meta.get("chunk_count", 0))
        topics = list(meta.get("topics") or [])
        score = 0.0
        if meta:
            from src.library.catalog.catalog_registry import CatalogRegistry

            score = CatalogRegistry.compute_semantic_score(
                reference_count=int(meta.get("reference_count", 0)),
                highlight_count=int(meta.get("highlight_count", 0)),
                topic_count=len(topics),
                chunk_count=chunk_count,
            )
        return self.settings.library_context_for_export(
            workspace_name=ws_name,
            collection_name=col_name,
            semantic_score=score,
            chunk_count=chunk_count,
            topics=topics,
        )

    def _write_study_exports(self, output_path: str, package: dict) -> dict[str, str]:
        try:
            study = StudyResult.from_package(package)
            return StudyExporter.write_exports(output_path, study)
        except OSError as exc:
            self._logger.warning("Exportações de estudo falharam: %s", exc)
            return {}

    def _update_datasets(
        self,
        job: TranscriptionJob,
        *,
        catalog_id: str,
        stage_metadata: dict,
    ) -> dict:
        try:
            ws_name, col_name = self._library_names()
            engine = get_dataset_engine()
            result = engine.build_from_document(
                document_id=catalog_id,
                title=os.path.splitext(job.file_name)[0],
                source_path=job.file_path,
                workspace=ws_name,
                collection=col_name,
                author=self.settings.library_author,
                speaker=self.settings.library_speaker,
                stage_metadata=stage_metadata,
                semantic_metadata=job.semantic_metadata,
                catalog_id=catalog_id,
            )
            DatasetExporter().export_all()
            job.dataset_metadata = result.to_metadata()
            return result.to_metadata()
        except Exception as exc:
            self._logger.warning("Atualização de datasets falhou: %s", exc)
            return {}

    def _register_in_library(
        self,
        job: TranscriptionJob,
        *,
        file_hash: str,
        pipeline_stage: str,
        stage_metadata: dict,
    ) -> tuple[str, str, dict[str, str]]:
        try:
            if not file_hash:
                fp = self._cache.fingerprint(job.file_path)
                file_hash = fp.sha256
            lib = get_library()
            entry, _rels = lib.register_processed_document(
                source_path=job.file_path,
                output_path=job.output_path,
                file_hash=file_hash,
                workspace_id=self.settings.workspace_id,
                collection_id=self.settings.collection_id,
                collection_name=self.settings.collection_name,
                speaker=self.settings.library_speaker,
                author=self.settings.library_author,
                tags=self.settings.parse_library_tags(),
                category=self.settings.library_category,
                knowledge_type=self.settings.knowledge_type,
                export_mode=self.settings.export_mode,
                template=self.settings.content_template,
                pipeline_stage=pipeline_stage,
                semantic_metadata=job.semantic_metadata,
                stage_metadata=stage_metadata,
            )
            rel_summary = lib.relationships.format_for_history(entry.id)
            graph_fields: dict[str, str] = {}
            try:
                from src.knowledge_graph import get_knowledge_graph

                graph_fields = get_knowledge_graph().history_fields_for_document(entry.id)
            except Exception:
                pass
            return entry.id, rel_summary, graph_fields
        except Exception as exc:
            self._logger.warning("Catalogação na biblioteca falhou: %s", exc)
            return "", "", {}

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
