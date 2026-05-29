"""Estágios do pipeline AI-ready (raw → clean → ai_ready → notebooklm)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ContentStage(str, Enum):
    RAW = "raw"
    CLEAN = "clean"
    AI_READY = "ai_ready"
    SEMANTIC = "semantic"
    STUDY = "study"
    NOTEBOOKLM = "notebooklm"
    DATASET = "dataset"


EXPORT_MODES = ("raw", "clean", "ai_ready", "notebooklm", "study_mode")
CONTENT_TEMPLATES = ("generic", "sermon", "podcast", "course")


@dataclass
class StageResult:
    """Resultado de um estágio do pipeline — base para exportação NotebookLM-ready."""

    stage: ContentStage
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not self.content.strip()

    @property
    def pipeline_stage(self) -> str:
        return self.stage.value
