from __future__ import annotations

import json
import os
import re
from typing import Literal, Optional

from src.ai_ready.exporters.notebooklm_exporter import ExportContext
from src.ai_ready.pipeline import process_for_export
from src.ai_ready.stages import StageResult

ExportFormat = Literal["txt", "md", "json"]


class ExportService:
    """Formata e grava transcrições em TXT, Markdown ou JSON (modo raw ou pipeline AI-ready)."""

    @staticmethod
    def format_content(text: str, fmt: ExportFormat) -> str:
        """Formatação legada — usada quando export_mode é raw."""
        if fmt == "json":
            return json.dumps({"transcricao": text}, ensure_ascii=False, indent=2)
        if fmt == "md":
            return f"# Transcrição\n\n{text}"
        return text

    @staticmethod
    def extension_for(fmt: ExportFormat) -> str:
        return f".{fmt}"

    @staticmethod
    def build_output_path(source_path: str, output_dir: str, fmt: ExportFormat) -> str:
        base = os.path.splitext(os.path.basename(source_path))[0]
        return os.path.join(output_dir, f"{base}{ExportService.extension_for(fmt)}")

    @staticmethod
    def _strip_markdown(text: str) -> str:
        text = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
        return text.strip()

    def process_content(
        self,
        text: str,
        fmt: ExportFormat,
        *,
        source_path: str = "",
        export_mode: str = "raw",
        content_template: str = "generic",
        language: str = "auto",
        model: str = "",
        library_context: dict | None = None,
    ) -> tuple[str, Optional[StageResult]]:
        mode = (export_mode or "raw").lower()

        if mode == "raw":
            return self.format_content(text, fmt), None

        lib = library_context or {}
        ctx = ExportContext(
            source_path=source_path,
            language=language,
            model=model,
            content_template=content_template,
            export_mode=mode,
            speaker=str(lib.get("speaker", "")),
            author=str(lib.get("author", "")),
            workspace=str(lib.get("workspace", "")),
            collection=str(lib.get("collection", "")),
            category=str(lib.get("category", "")),
            knowledge_type=str(lib.get("knowledge_type", "document")),
            semantic_score=float(lib.get("semantic_score", 0) or 0),
            chunk_count=int(lib.get("chunk_count", 0) or 0),
            tags=list(lib.get("tags") or []),
            topics=list(lib.get("topics") or []) or None,
        )
        result = process_for_export(text, ctx)

        if fmt == "json":
            payload = {
                "metadata": result.metadata,
                "content": result.content,
                "pipeline_stage": result.pipeline_stage,
            }
            return json.dumps(payload, ensure_ascii=False, indent=2), result

        if fmt == "txt":
            return self._strip_markdown(result.content), result

        return result.content, result

    def save(
        self,
        path: str,
        text: str,
        fmt: ExportFormat,
        *,
        source_path: str = "",
        export_mode: str = "raw",
        content_template: str = "generic",
        language: str = "auto",
        model: str = "",
        library_context: dict | None = None,
    ) -> tuple[str, Optional[StageResult]]:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        content, stage = self.process_content(
            text,
            fmt,
            source_path=source_path or path,
            export_mode=export_mode,
            content_template=content_template,
            language=language,
            model=model,
            library_context=library_context,
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path, stage

    def save_auto(
        self,
        source_path: str,
        text: str,
        output_dir: str,
        fmt: ExportFormat,
        *,
        export_mode: str = "raw",
        content_template: str = "generic",
        language: str = "auto",
        model: str = "",
        library_context: dict | None = None,
    ) -> tuple[str, Optional[StageResult]]:
        out_path = self.build_output_path(source_path, output_dir, fmt)
        return self.save(
            out_path,
            text,
            fmt,
            source_path=source_path,
            export_mode=export_mode,
            content_template=content_template,
            language=language,
            model=model,
            library_context=library_context,
        )
