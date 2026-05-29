"""Knowledge Readiness Score — preparação do documento para consumo por IA."""

from __future__ import annotations

from typing import Any


def compute_knowledge_readiness_score(dataset: dict[str, Any]) -> int:
    """Escala 0–100 com base em metadados, chunks, tópicos, referências e estudo."""
    score = 0.0
    weights = {
        "metadata": 15,
        "chunks": 25,
        "topics": 15,
        "references": 10,
        "flashcards": 15,
        "quizzes": 10,
        "relationships": 10,
    }

    meta = dataset.get("metadata") or {}
    if meta or dataset.get("title"):
        filled = sum(1 for k in ("export_mode", "template", "pipeline_stage", "semantic_ready") if meta.get(k))
        score += weights["metadata"] * min(1.0, (filled + (1 if dataset.get("title") else 0)) / 4)

    chunks = dataset.get("chunks") or []
    if chunks:
        score += weights["chunks"] * min(1.0, len(chunks) / 5)

    topics = dataset.get("topics") or []
    if topics:
        score += weights["topics"] * min(1.0, len(topics) / 3)

    refs = dataset.get("references") or []
    if refs:
        score += weights["references"] * min(1.0, len(refs) / 2)

    flashcards = dataset.get("flashcards") or []
    if flashcards:
        score += weights["flashcards"] * min(1.0, len(flashcards) / 5)

    quizzes = dataset.get("quizzes") or []
    if quizzes:
        score += weights["quizzes"] * min(1.0, len(quizzes) / 3)

    rel_score = 0.0
    if dataset.get("workspace"):
        rel_score += 0.25
    if dataset.get("collection"):
        rel_score += 0.25
    if dataset.get("author") or dataset.get("speaker"):
        rel_score += 0.25
    if highlights := dataset.get("highlights"):
        if highlights:
            rel_score += 0.25
    score += weights["relationships"] * rel_score

    return int(min(100, max(0, round(score))))
