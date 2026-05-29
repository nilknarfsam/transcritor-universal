"""Registro persistente de entradas de cache em data/cache_registry.json."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.settings_service import DATA_DIR

REGISTRY_FILE = DATA_DIR / "cache_registry.json"
CACHE_STAGES = ("whisper", "ocr", "clean", "semantic", "notebooklm", "chunks")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CacheRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, dict[str, Any]] = {}
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.load()

    def load(self) -> None:
        if not REGISTRY_FILE.exists():
            self._entries = {}
            return
        try:
            with open(REGISTRY_FILE, encoding="utf-8") as f:
                data = json.load(f)
            raw = data.get("entries", data) if isinstance(data, dict) else {}
            self._entries = raw if isinstance(raw, dict) else {}
        except (json.JSONDecodeError, OSError, TypeError):
            self._entries = {}

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "entries": self._entries}, f, ensure_ascii=False, indent=2)

    @property
    def entries(self) -> dict[str, dict[str, Any]]:
        return dict(self._entries)

    def get(self, file_hash: str) -> dict[str, Any] | None:
        entry = self._entries.get(file_hash)
        return dict(entry) if isinstance(entry, dict) else None

    def upsert(
        self,
        file_hash: str,
        *,
        file_name: str,
        size_bytes: int,
        export_mode: str,
        template: str,
        language: str,
        pipeline_stage: str = "",
        paths: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        existing = self._entries.get(file_hash, {})
        merged_paths = dict(existing.get("paths", {}))
        if paths:
            merged_paths.update(paths)
        entry = {
            "hash": file_hash,
            "file_name": file_name,
            "size_bytes": size_bytes,
            "processed_at": _utc_now(),
            "export_mode": export_mode,
            "template": template,
            "language": language,
            "pipeline_stage": pipeline_stage or existing.get("pipeline_stage", ""),
            "paths": merged_paths,
        }
        self._entries[file_hash] = entry
        self.save()
        return entry

    def remove(self, file_hash: str) -> bool:
        if file_hash not in self._entries:
            return False
        del self._entries[file_hash]
        self.save()
        return True

    def clear(self) -> int:
        count = len(self._entries)
        self._entries = {}
        self.save()
        return count

    def stats(self) -> dict[str, Any]:
        total_size = 0
        for entry in self._entries.values():
            paths = entry.get("paths", {})
            if isinstance(paths, dict):
                for p in paths.values():
                    if isinstance(p, str) and Path(p).is_file():
                        try:
                            total_size += Path(p).stat().st_size
                        except OSError:
                            pass
        return {
            "item_count": len(self._entries),
            "disk_bytes": total_size,
        }
