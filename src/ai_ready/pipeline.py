"""Pipeline AI-ready — RAW → CACHE CHECK → CLEAN → AI_READY → SEMANTIC → STUDY → NOTEBOOKLM → DATASET.

CACHE CHECK: ``QueueManager`` / ``CacheEngine``. STUDY: modo ``study_mode``. DATASET: ``DatasetEngine``.
"""

from __future__ import annotations

from src.ai_ready.exporters.notebooklm_exporter import ExportContext, NotebookLMExporter, export_notebooklm
from src.ai_ready.formatters.markdown_formatter import beautify_markdown
from src.ai_ready.stages import ContentStage, StageResult

_exporter = NotebookLMExporter()


def build_raw_stage(text: str, *, source: str = "") -> StageResult:
    """Encapsula conteúdo bruto da transcrição ou extração."""
    metadata: dict[str, str] = {}
    if source:
        metadata["source"] = source
    return StageResult(stage=ContentStage.RAW, content=text, metadata=metadata)


def build_clean_stage(raw: StageResult) -> StageResult:
    """Normaliza e embeleza conteúdo bruto."""
    cleaned = beautify_markdown(raw.content)
    return StageResult(
        stage=ContentStage.CLEAN,
        content=cleaned,
        metadata={**raw.metadata, "derived_from": ContentStage.RAW.value},
    )


def build_ai_ready_stage(clean: StageResult, *, template: str = "generic", source: str = "") -> StageResult:
    """Aplica template semântico ao conteúdo limpo."""
    ctx = ExportContext(
        source_path=source or str(clean.metadata.get("source", "")),
        content_template=template,
        export_mode="ai_ready",
    )
    result = _exporter.export(clean.content, ctx)
    return StageResult(
        stage=ContentStage.AI_READY,
        content=result.content,
        metadata={**clean.metadata, **result.metadata, "derived_from": ContentStage.CLEAN.value},
    )


def build_notebooklm_stage(
    text: str,
    ctx: ExportContext,
) -> StageResult:
    """Pipeline completo até exportação NotebookLM-ready."""
    return export_notebooklm(text, ctx)


def build_semantic_stage(text: str, ctx: ExportContext) -> StageResult:
    """Executa camada semântica sobre conteúdo bruto."""
    from src.ai_ready.exporters.notebooklm_exporter import NotebookLMExporter

    exporter = NotebookLMExporter()
    ai_ready = exporter.export(text, ExportContext(**{**ctx.__dict__, "export_mode": "ai_ready"}))
    return exporter._apply_semantic(text, ctx, ai_ready)  # noqa: SLF001


def process_for_export(text: str, ctx: ExportContext) -> StageResult:
    """Ponto de entrada unificado — respeita export_mode do contexto."""
    return _exporter.export(text, ctx)
