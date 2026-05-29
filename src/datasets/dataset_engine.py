"""Orquestrador do Knowledge Dataset Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.datasets.builders.chunk_dataset_builder import ChunkDatasetBuilder
from src.datasets.builders.knowledge_dataset_builder import KnowledgeDatasetBuilder
from src.datasets.builders.knowledge_index_builder import KnowledgeIndexBuilder
from src.datasets.readiness import compute_knowledge_readiness_score
from src.datasets.registry.dataset_registry import DatasetRegistry, get_dataset_registry

_engine: "DatasetEngine | None" = None


def get_dataset_engine() -> "DatasetEngine":
    global _engine
    if _engine is None:
        _engine = DatasetEngine()
    return _engine


@dataclass
class DatasetBuildResult:
    dataset_id: str = ""
    document_id: str = ""
    chunk_count: int = 0
    knowledge_readiness_score: int = 0
    dataset_ready: bool = False
    chunk_ids: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "document_id": self.document_id,
            "chunk_count": self.chunk_count,
            "knowledge_readiness_score": self.knowledge_readiness_score,
            "dataset_ready": self.dataset_ready,
        }


class DatasetEngine:
    def __init__(self, registry: DatasetRegistry | None = None) -> None:
        self._registry = registry or get_dataset_registry()
        self._knowledge_builder = KnowledgeDatasetBuilder()
        self._chunk_builder = ChunkDatasetBuilder()
        self._index_builder = KnowledgeIndexBuilder()

    def build_from_document(
        self,
        *,
        document_id: str,
        title: str,
        source_path: str,
        workspace: str = "",
        collection: str = "",
        author: str = "",
        speaker: str = "",
        stage_metadata: dict[str, Any] | None = None,
        semantic_metadata: dict[str, Any] | None = None,
        catalog_id: str | None = None,
    ) -> DatasetBuildResult:
        meta = dict(stage_metadata or {})
        sem = dict(semantic_metadata or {})

        topics = list(meta.get("topics") or sem.get("topics") or [])
        refs = meta.get("bible_references") or meta.get("references") or []
        highlights = meta.get("highlights") or []
        chunks = list(meta.get("chunks") or [])

        study_pkg = meta.get("study_package") or {}
        flashcards = list(study_pkg.get("flashcards") or meta.get("flashcards") or [])
        quizzes = list(study_pkg.get("quizzes") or meta.get("quizzes") or [])
        difficulty = str(
            study_pkg.get("difficulty") or meta.get("difficulty") or "básico"
        )

        existing = self._registry.get_knowledge_by_document(document_id)
        dataset_id = str(existing.get("dataset_id")) if existing else None

        knowledge = self._knowledge_builder.build(
            document_id=document_id,
            title=title,
            workspace=workspace,
            collection=collection,
            author=author,
            speaker=speaker,
            topics=topics,
            references=refs,
            difficulty=difficulty,
            highlights=highlights if isinstance(highlights, list) else [],
            chunks=chunks,
            flashcards=flashcards,
            quizzes=quizzes,
            metadata={
                "catalog_id": catalog_id or document_id,
                "source_path": source_path,
                "export_mode": meta.get("export_mode", ""),
                "template": meta.get("template", ""),
                "pipeline_stage": meta.get("pipeline_stage", ""),
                "semantic_ready": bool(meta.get("semantic_ready") or sem.get("semantic_ready")),
                "chunk_count": len(chunks),
                "flashcards_count": len(flashcards),
                "quizzes_count": len(quizzes),
            },
            dataset_id=dataset_id,
        )

        readiness = compute_knowledge_readiness_score(knowledge)
        knowledge["metadata"]["knowledge_readiness_score"] = readiness

        saved = self._registry.upsert_knowledge(
            knowledge,
            source_document=source_path,
        )

        chunk_records = self._chunk_builder.build_all(
            document_id=document_id,
            workspace=workspace,
            collection=collection,
            topics=topics,
            references=refs,
            chunks=chunks,
        )
        saved_chunks = self._registry.upsert_chunks(
            chunk_records,
            source_document=source_path,
        )

        index = self._index_builder.build(
            self._registry.knowledge_datasets,
            self._registry.chunk_datasets,
        )
        self._registry.save_index(index)

        return DatasetBuildResult(
            dataset_id=str(saved.get("dataset_id", "")),
            document_id=document_id,
            chunk_count=len(saved_chunks),
            knowledge_readiness_score=readiness,
            dataset_ready=bool(chunks or topics),
            chunk_ids=[str(c.get("chunk_id", "")) for c in saved_chunks],
        )

    def rebuild_global_index(self) -> dict[str, Any]:
        index = self._index_builder.build(
            self._registry.knowledge_datasets,
            self._registry.chunk_datasets,
        )
        self._registry.save_index(index)
        return index
