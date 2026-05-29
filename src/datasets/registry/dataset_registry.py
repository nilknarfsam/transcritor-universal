"""Registro persistente de datasets de conhecimento."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.settings_service import DATA_DIR

DATASETS_DIR = DATA_DIR / "datasets"
KNOWLEDGE_DATASETS_FILE = DATASETS_DIR / "knowledge_datasets.json"
CHUNK_DATASETS_FILE = DATASETS_DIR / "chunk_datasets.json"
KNOWLEDGE_INDEX_FILE = DATASETS_DIR / "knowledge_index.json"
DATASET_VERSION = "1.0"

_registry: "DatasetRegistry | None" = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_dataset_registry() -> "DatasetRegistry":
    global _registry
    if _registry is None:
        _registry = DatasetRegistry()
    return _registry


class DatasetRegistry:
    def __init__(self) -> None:
        self._knowledge: dict[str, dict[str, Any]] = {}
        self._chunks: dict[str, dict[str, Any]] = {}
        self._index: dict[str, Any] = {}
        DATASETS_DIR.mkdir(parents=True, exist_ok=True)
        self.load()

    def load(self) -> None:
        self._knowledge = self._read_json(KNOWLEDGE_DATASETS_FILE, default={})
        self._chunks = self._read_json(CHUNK_DATASETS_FILE, default={})
        self._index = self._read_json(KNOWLEDGE_INDEX_FILE, default={})

    @staticmethod
    def _read_json(path: Path, *, default: Any) -> Any:
        if not path.is_file():
            return default
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, type(default)) else default
        except (json.JSONDecodeError, OSError):
            return default

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @property
    def knowledge_datasets(self) -> dict[str, dict[str, Any]]:
        return dict(self._knowledge)

    @property
    def chunk_datasets(self) -> dict[str, dict[str, Any]]:
        return dict(self._chunks)

    @property
    def knowledge_index(self) -> dict[str, Any]:
        return dict(self._index)

    def get_knowledge(self, dataset_id: str) -> dict[str, Any] | None:
        return self._knowledge.get(dataset_id)

    def get_knowledge_by_document(self, document_id: str) -> dict[str, Any] | None:
        for rec in self._knowledge.values():
            if rec.get("document_id") == document_id:
                return rec
        return None

    def upsert_knowledge(
        self,
        dataset: dict[str, Any],
        *,
        source_document: str,
    ) -> dict[str, Any]:
        now = _utc_now()
        dataset_id = str(dataset.get("dataset_id") or f"ds-{uuid.uuid4().hex[:12]}")
        existing = self._knowledge.get(dataset_id, {})
        record = {
            **dataset,
            "dataset_id": dataset_id,
            "source_document": source_document,
            "dataset_version": DATASET_VERSION,
            "created_at": existing.get("created_at") or now,
            "updated_at": now,
        }
        self._knowledge[dataset_id] = record
        self._persist_knowledge()
        return record

    def upsert_chunks(
        self,
        chunk_records: list[dict[str, Any]],
        *,
        source_document: str,
    ) -> list[dict[str, Any]]:
        now = _utc_now()
        saved: list[dict[str, Any]] = []
        for chunk in chunk_records:
            chunk_id = str(chunk.get("chunk_id") or f"ch-{uuid.uuid4().hex[:12]}")
            existing = self._chunks.get(chunk_id, {})
            record = {
                **chunk,
                "chunk_id": chunk_id,
                "source_document": source_document,
                "dataset_version": DATASET_VERSION,
                "created_at": existing.get("created_at") or now,
                "updated_at": now,
            }
            self._chunks[chunk_id] = record
            saved.append(record)
        if saved:
            self._persist_chunks()
        return saved

    def save_index(self, index: dict[str, Any]) -> None:
        self._index = {
            **index,
            "updated_at": _utc_now(),
            "dataset_version": DATASET_VERSION,
        }
        self._write_json(KNOWLEDGE_INDEX_FILE, self._index)

    def _persist_knowledge(self) -> None:
        self._write_json(KNOWLEDGE_DATASETS_FILE, self._knowledge)

    def _persist_chunks(self) -> None:
        self._write_json(CHUNK_DATASETS_FILE, self._chunks)

    def remove_by_document(self, document_id: str) -> None:
        self._knowledge = {
            k: v for k, v in self._knowledge.items() if v.get("document_id") != document_id
        }
        self._chunks = {
            k: v for k, v in self._chunks.items() if v.get("document_id") != document_id
        }
        self._persist_knowledge()
        self._persist_chunks()
