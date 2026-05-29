"""Catálogo de documentos processados — unidades de conhecimento."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.settings_service import DATA_DIR

LIBRARY_DIR = DATA_DIR / "library"
CATALOG_FILE = LIBRARY_DIR / "catalog.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CatalogEntry:
    id: str
    title: str
    source_path: str
    output_path: str = ""
    file_hash: str = ""
    workspace_id: str = ""
    workspace_name: str = ""
    collection_id: str = ""
    collection_name: str = ""
    speaker: str = ""
    author: str = ""
    topics: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    chunks: list[Any] = field(default_factory=list)
    timestamps: list[str] = field(default_factory=list)
    export_mode: str = ""
    template: str = ""
    pipeline_stage: str = ""
    category: str = ""
    knowledge_type: str = "document"
    semantic_score: float = 0.0
    chunk_count: int = 0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source_path": self.source_path,
            "output_path": self.output_path,
            "file_hash": self.file_hash,
            "workspace_id": self.workspace_id,
            "workspace_name": self.workspace_name,
            "collection_id": self.collection_id,
            "collection_name": self.collection_name,
            "speaker": self.speaker,
            "author": self.author,
            "topics": self.topics,
            "tags": self.tags,
            "references": self.references,
            "highlights": self.highlights,
            "chunks": self.chunks,
            "timestamps": self.timestamps,
            "export_mode": self.export_mode,
            "template": self.template,
            "pipeline_stage": self.pipeline_stage,
            "category": self.category,
            "knowledge_type": self.knowledge_type,
            "semantic_score": self.semantic_score,
            "chunk_count": self.chunk_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CatalogEntry":
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")),
            source_path=str(data.get("source_path", "")),
            output_path=str(data.get("output_path", "")),
            file_hash=str(data.get("file_hash", "")),
            workspace_id=str(data.get("workspace_id", "")),
            workspace_name=str(data.get("workspace_name", "")),
            collection_id=str(data.get("collection_id", "")),
            collection_name=str(data.get("collection_name", "")),
            speaker=str(data.get("speaker", "")),
            author=str(data.get("author", "")),
            topics=list(data.get("topics") or []),
            tags=list(data.get("tags") or []),
            references=list(data.get("references") or []),
            highlights=list(data.get("highlights") or []),
            chunks=list(data.get("chunks") or []),
            timestamps=list(data.get("timestamps") or []),
            export_mode=str(data.get("export_mode", "")),
            template=str(data.get("template", "")),
            pipeline_stage=str(data.get("pipeline_stage", "")),
            category=str(data.get("category", "")),
            knowledge_type=str(data.get("knowledge_type", "document")),
            semantic_score=float(data.get("semantic_score", 0) or 0),
            chunk_count=int(data.get("chunk_count", 0) or 0),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )


class CatalogRegistry:
    def __init__(self) -> None:
        self._documents: dict[str, dict[str, Any]] = {}
        LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
        self.load()

    def load(self) -> None:
        if not CATALOG_FILE.exists():
            self._documents = {}
            return
        try:
            with open(CATALOG_FILE, encoding="utf-8") as f:
                data = json.load(f)
            raw = data.get("documents", data) if isinstance(data, dict) else {}
            self._documents = raw if isinstance(raw, dict) else {}
        except (json.JSONDecodeError, OSError, TypeError):
            self._documents = {}

    def save(self) -> None:
        LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
        with open(CATALOG_FILE, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "documents": self._documents}, f, ensure_ascii=False, indent=2)

    @property
    def all_entries(self) -> list[CatalogEntry]:
        return [CatalogEntry.from_dict(v) for v in self._documents.values()]

    def get(self, catalog_id: str) -> CatalogEntry | None:
        raw = self._documents.get(catalog_id)
        return CatalogEntry.from_dict(raw) if isinstance(raw, dict) else None

    def find_by_hash(self, file_hash: str) -> CatalogEntry | None:
        if not file_hash:
            return None
        for raw in self._documents.values():
            if str(raw.get("file_hash", "")) == file_hash:
                return CatalogEntry.from_dict(raw)
        return None

    def register(self, entry: CatalogEntry) -> CatalogEntry:
        now = _utc_now()
        existing = self.find_by_hash(entry.file_hash) if entry.file_hash else None
        if existing:
            entry.id = existing.id
            entry.created_at = existing.created_at or now
        else:
            if not entry.id:
                entry.id = f"doc-{uuid.uuid4().hex[:12]}"
            entry.created_at = entry.created_at or now
        entry.updated_at = now
        self._documents[entry.id] = entry.to_dict()
        self.save()
        return entry

    def remove(self, catalog_id: str) -> bool:
        if catalog_id not in self._documents:
            return False
        del self._documents[catalog_id]
        self.save()
        return True

    def count(self) -> int:
        return len(self._documents)

    @staticmethod
    def title_from_path(path: str) -> str:
        base = os.path.splitext(os.path.basename(path))[0]
        return base.replace("_", " ").replace("-", " ").strip()

    @staticmethod
    def compute_semantic_score(
        *,
        reference_count: int = 0,
        highlight_count: int = 0,
        topic_count: int = 0,
        chunk_count: int = 0,
    ) -> float:
        score = (
            min(reference_count, 20) * 2.0
            + min(highlight_count, 15) * 1.5
            + min(topic_count, 10) * 2.5
            + min(chunk_count, 30) * 0.5
        )
        return round(min(100.0, score), 1)
