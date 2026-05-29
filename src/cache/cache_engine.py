"""Engine de cache — lookup, armazenamento e reutilização de estágios do pipeline."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.cache.cache_registry import CACHE_STAGES, CacheRegistry
from src.cache.hash_manager import FileFingerprint, file_fingerprint
from src.core.settings_service import DATA_DIR

CACHE_DIR = DATA_DIR / "cache"


@dataclass
class CacheLookupResult:
    hit: bool = False
    partial: bool = False
    raw_text: str = ""
    reused_stages: list[str] = field(default_factory=list)
    file_hash: str = ""
    fingerprint: FileFingerprint | None = None


class CacheEngine:
    def __init__(self) -> None:
        self._registry = CacheRegistry()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def registry(self) -> CacheRegistry:
        return self._registry

    def fingerprint(self, path: str) -> FileFingerprint:
        return file_fingerprint(path)

    def _cache_root(self, file_hash: str) -> Path:
        return CACHE_DIR / file_hash

    def _stage_path(self, file_hash: str, stage: str) -> Path:
        ext = "json" if stage == "chunks" else "txt" if stage in ("whisper", "ocr") else "md"
        return self._cache_root(file_hash) / f"{stage}.{ext}"

    def lookup(
        self,
        path: str,
        *,
        export_mode: str,
        template: str,
        language: str,
    ) -> CacheLookupResult:
        fp = self.fingerprint(path)
        entry = self._registry.get(fp.sha256)
        result = CacheLookupResult(file_hash=fp.sha256, fingerprint=fp)

        if not entry:
            return result

        if not self._config_matches(entry, export_mode, template, language):
            return result

        if not os.path.isfile(path):
            return result

        try:
            if entry.get("size_bytes") != fp.size_bytes:
                return result
        except (TypeError, ValueError):
            return result

        reused: list[str] = []
        raw_text = ""

        for stage in ("whisper", "ocr"):
            text = self.read_stage(fp.sha256, stage)
            if text:
                raw_text = text
                reused.append(stage)

        if not raw_text:
            return result

        for stage in ("clean", "semantic", "notebooklm"):
            if self.read_stage(fp.sha256, stage):
                reused.append(stage)

        if "chunks" in entry.get("paths", {}) or self._stage_path(fp.sha256, "chunks").is_file():
            reused.append("chunks")

        result.raw_text = raw_text
        result.reused_stages = reused
        result.partial = bool(reused)
        result.hit = self._is_full_hit(export_mode, reused)
        return result

    @staticmethod
    def _config_matches(
        entry: dict[str, Any],
        export_mode: str,
        template: str,
        language: str,
    ) -> bool:
        return (
            str(entry.get("export_mode", "")).lower() == (export_mode or "raw").lower()
            and str(entry.get("template", "generic")) == (template or "generic")
            and str(entry.get("language", "auto")) == (language or "auto")
        )

    @staticmethod
    def _is_full_hit(export_mode: str, reused: list[str]) -> bool:
        mode = (export_mode or "raw").lower()
        if mode == "raw":
            return bool(reused) and ("whisper" in reused or "ocr" in reused)
        if mode == "clean":
            return "clean" in reused
        if mode == "ai_ready":
            return "semantic" in reused or "notebooklm" in reused
        if mode == "notebooklm":
            return "notebooklm" in reused
        return False

    def read_stage(self, file_hash: str, stage: str) -> str:
        if stage not in CACHE_STAGES:
            return ""
        path = self._stage_path(file_hash, stage)
        if not path.is_file():
            return ""
        try:
            if stage == "chunks":
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                return json.dumps(data, ensure_ascii=False)
            with open(path, encoding="utf-8") as f:
                return f.read()
        except (OSError, json.JSONDecodeError):
            return ""

    def save_stage(
        self,
        path: str,
        stage: str,
        content: str,
        *,
        export_mode: str,
        template: str,
        language: str,
        pipeline_stage: str = "",
    ) -> str:
        if stage not in CACHE_STAGES:
            return ""
        fp = self.fingerprint(path)
        root = self._cache_root(fp.sha256)
        root.mkdir(parents=True, exist_ok=True)
        out = self._stage_path(fp.sha256, stage)
        if stage == "chunks":
            try:
                payload = json.loads(content) if content.strip().startswith(("[", "{")) else content
            except json.JSONDecodeError:
                payload = {"chunks": content}
            with open(out, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        else:
            with open(out, "w", encoding="utf-8") as f:
                f.write(content)
        self._registry.upsert(
            fp.sha256,
            file_name=fp.file_name,
            size_bytes=fp.size_bytes,
            export_mode=export_mode,
            template=template,
            language=language,
            pipeline_stage=pipeline_stage or stage,
            paths={stage: str(out)},
        )
        return fp.sha256

    def save_pipeline_artifacts(
        self,
        path: str,
        *,
        raw_text: str,
        stage_result_content: str | None,
        stage_name: str,
        export_mode: str,
        template: str,
        language: str,
        chunks_json: str = "",
        source_kind: str,
    ) -> None:
        """Persiste estágios após processamento."""
        if source_kind == "whisper" and raw_text:
            self.save_stage(
                path, "whisper", raw_text,
                export_mode=export_mode, template=template, language=language,
            )
        elif source_kind == "ocr" and raw_text:
            self.save_stage(
                path, "ocr", raw_text,
                export_mode=export_mode, template=template, language=language,
            )

        if not stage_result_content:
            return

        mode = (export_mode or "raw").lower()
        if mode in ("clean", "ai_ready", "notebooklm"):
            self.save_stage(
                path, "clean", stage_result_content,
                export_mode=export_mode, template=template, language=language,
                pipeline_stage="clean",
            )
        if mode in ("ai_ready", "notebooklm"):
            self.save_stage(
                path, "semantic", stage_result_content,
                export_mode=export_mode, template=template, language=language,
                pipeline_stage="semantic",
            )
        if mode == "notebooklm":
            self.save_stage(
                path, "notebooklm", stage_result_content,
                export_mode=export_mode, template=template, language=language,
                pipeline_stage="notebooklm",
            )
        if chunks_json:
            self.save_stage(
                path, "chunks", chunks_json,
                export_mode=export_mode, template=template, language=language,
            )

    def clear_all(self) -> tuple[int, int]:
        """Remove registry e arquivos em data/cache/. Retorna (itens, bytes estimados)."""
        stats = self._registry.stats()
        count = self._registry.clear()
        if CACHE_DIR.is_dir():
            shutil.rmtree(CACHE_DIR, ignore_errors=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return count, int(stats.get("disk_bytes", 0))

    def stats(self) -> dict[str, Any]:
        return self._registry.stats()
