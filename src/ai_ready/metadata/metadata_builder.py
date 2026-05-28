"""Gerador de metadata YAML padronizada — sem dependências externas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

FIELD_ORDER = (
    "title",
    "source",
    "author",
    "speaker",
    "created_at",
    "processed_at",
    "language",
    "content_type",
    "topics",
    "tags",
    "duration",
    "model",
    "pipeline_stage",
)


@dataclass
class MetadataBuilder:
    """Monta metadata opcional para frontmatter YAML."""

    title: str = ""
    source: str = ""
    author: str = ""
    speaker: str = ""
    created_at: str = ""
    processed_at: str = ""
    language: str = ""
    content_type: str = ""
    topics: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    duration: str = ""
    model: str = ""
    pipeline_stage: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for key in FIELD_ORDER:
            value = getattr(self, key)
            if value is None:
                continue
            if isinstance(value, list):
                if value:
                    data[key] = value
            elif isinstance(value, str):
                if value.strip():
                    data[key] = value.strip()
            elif value:
                data[key] = value
        return data

    @classmethod
    def from_source_path(
        cls,
        source_path: str,
        *,
        language: str = "",
        content_type: str = "generic",
        model: str = "",
        pipeline_stage: str = "",
        speaker: str = "",
        author: str = "",
    ) -> "MetadataBuilder":
        import os

        base = os.path.splitext(os.path.basename(source_path))[0]
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return cls(
            title=base.replace("_", " ").replace("-", " ").strip(),
            source=source_path,
            author=author,
            speaker=speaker,
            processed_at=now,
            language=language if language and language != "auto" else "",
            content_type=content_type,
            model=model,
            pipeline_stage=pipeline_stage,
        )


def _yaml_escape(value: str) -> str:
    if not value:
        return '""'
    if any(c in value for c in ":{}[]&*#?|-<>=!%@`\"',"):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def build_metadata_yaml(metadata: dict[str, Any] | MetadataBuilder) -> str:
    """Serializa metadata como bloco YAML frontmatter."""
    if isinstance(metadata, MetadataBuilder):
        data = metadata.to_dict()
    else:
        data = {k: metadata[k] for k in FIELD_ORDER if k in metadata and metadata[k]}

    lines = ["---"]
    for key in FIELD_ORDER:
        if key not in data:
            continue
        value = data[key]
        if isinstance(value, list):
            if not value:
                continue
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {_yaml_escape(str(item))}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {_yaml_escape(str(value))}")
    lines.append("---")
    return "\n".join(lines)
