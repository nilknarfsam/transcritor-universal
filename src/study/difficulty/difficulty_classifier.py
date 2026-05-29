"""Classificação de dificuldade — básico, intermediário, avançado."""

from __future__ import annotations

import re
from typing import Any

_HEADER = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_SENTENCE = re.compile(r"[.!?]+")


def classify_difficulty(
    text: str,
    *,
    topics: list[str] | None = None,
    reference_count: int = 0,
    chunk_count: int = 0,
) -> str:
    """Retorna: básico | intermediário | avançado."""
    text = text or ""
    length = len(text)
    headers = len(_HEADER.findall(text))
    sentences = len(_SENTENCE.findall(text)) or 1
    avg_len = length / max(sentences, 1)
    topic_n = len(topics or [])
    refs = reference_count
    chunks = chunk_count

    score = 0.0
    if length > 8000:
        score += 2
    elif length > 3000:
        score += 1
    if headers > 12:
        score += 2
    elif headers > 5:
        score += 1
    if avg_len > 120:
        score += 1.5
    elif avg_len > 80:
        score += 0.5
    if topic_n > 8:
        score += 1.5
    elif topic_n > 4:
        score += 0.5
    if refs > 10:
        score += 2
    elif refs > 3:
        score += 1
    if chunks > 15:
        score += 1

    if score >= 5:
        return "avançado"
    if score >= 2.5:
        return "intermediário"
    return "básico"


def difficulty_to_metadata_value(level: str) -> str:
    return level.strip().lower()
