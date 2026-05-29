"""Busca contextual local no grafo — sem embeddings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.knowledge_graph.nodes.node_builder import document_node_id, make_node_id

if TYPE_CHECKING:
    from src.knowledge_graph.graph_engine import GraphEngine


@dataclass
class SemanticSearchResult:
    query: str
    documents: list[dict[str, Any]] = field(default_factory=list)
    chunks: list[dict[str, Any]] = field(default_factory=list)
    flashcards: list[dict[str, Any]] = field(default_factory=list)
    quizzes: list[dict[str, Any]] = field(default_factory=list)
    topics: list[dict[str, Any]] = field(default_factory=list)
    references: list[dict[str, Any]] = field(default_factory=list)
    collections: list[dict[str, Any]] = field(default_factory=list)
    workspaces: list[dict[str, Any]] = field(default_factory=list)
    total_hits: int = 0
    connection_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "documents": self.documents,
            "chunks": self.chunks,
            "flashcards": self.flashcards,
            "quizzes": self.quizzes,
            "topics": self.topics,
            "references": self.references,
            "collections": self.collections,
            "workspaces": self.workspaces,
            "total_hits": self.total_hits,
            "connection_reasons": self.connection_reasons,
        }


class SemanticSearchEngine:
    _FIELD_WEIGHTS = {
        "document": 10.0,
        "topic": 8.0,
        "bible_reference": 7.5,
        "tag": 6.0,
        "chunk": 6.5,
        "flashcard": 5.5,
        "quiz": 5.5,
        "speaker": 5.0,
        "author": 5.0,
        "collection": 4.0,
        "workspace": 3.5,
    }

    def __init__(self, graph: "GraphEngine") -> None:
        self._graph = graph

    def search(self, query: str, *, limit: int = 40) -> SemanticSearchResult:
        q = query.strip().lower()
        result = SemanticSearchResult(query=query)
        if not q or not self._graph.nodes:
            return result

        scored: list[tuple[float, dict[str, Any], list[str]]] = []
        for node in self._graph.nodes.values():
            score, reasons = self._score_node(node, q)
            if score > 0:
                scored.append((score, node, reasons))

        scored.sort(key=lambda x: -x[0])
        reasons_set: set[str] = set()

        for score, node, reasons in scored[: limit * 3]:
            ntype = str(node.get("type", ""))
            item = {
                "node_id": node.get("node_id"),
                "label": node.get("label"),
                "score": round(score, 2),
                "reasons": reasons,
                "metadata": node.get("metadata", {}),
            }
            reasons_set.update(reasons)

            if ntype == "document":
                if len(result.documents) < limit:
                    cid = str(node.get("metadata", {}).get("catalog_id", ""))
                    item["catalog_id"] = cid
                    result.documents.append(item)
            elif ntype == "chunk" and len(result.chunks) < limit:
                result.chunks.append(item)
            elif ntype == "flashcard" and len(result.flashcards) < limit:
                result.flashcards.append(item)
            elif ntype == "quiz" and len(result.quizzes) < limit:
                result.quizzes.append(item)
            elif ntype == "topic" and len(result.topics) < limit:
                result.topics.append(item)
            elif ntype == "bible_reference" and len(result.references) < limit:
                result.references.append(item)
            elif ntype == "collection" and len(result.collections) < limit:
                result.collections.append(item)
            elif ntype == "workspace" and len(result.workspaces) < limit:
                result.workspaces.append(item)

        result.total_hits = len(scored)
        result.connection_reasons = sorted(reasons_set)
        return result

    def _score_node(self, node: dict[str, Any], q: str) -> tuple[float, list[str]]:
        label = str(node.get("label", "")).lower()
        ntype = str(node.get("type", ""))
        meta = node.get("metadata") or {}
        reasons: list[str] = []
        score = 0.0
        weight = self._FIELD_WEIGHTS.get(ntype, 3.0)

        if q in label:
            score += weight * 2.0
            reasons.append(f"label_match:{ntype}")

        for token in q.split():
            if len(token) < 2:
                continue
            if token in label:
                score += weight * 0.6
                reasons.append(f"token:{token}")

        meta_text = " ".join(str(v) for v in meta.values() if isinstance(v, (str, int, float))).lower()
        if q in meta_text:
            score += weight * 0.4
            reasons.append("metadata_match")

        if ntype == "chunk":
            topics = meta.get("topics") or []
            for t in topics:
                if q in str(t).lower():
                    score += 4.0
                    reasons.append("chunk_topic")

        if ntype == "flashcard" and q in str(meta.get("topic", "")).lower():
            score += 3.0
            reasons.append("flashcard_topic")

        return score, reasons

    def search_catalog_ids(self, query: str, *, limit: int = 20) -> list[str]:
        """IDs de catálogo ordenados por relevância na busca semântica."""
        res = self.search(query, limit=limit)
        ids: list[str] = []
        for doc in res.documents:
            cid = str(doc.get("catalog_id") or doc.get("metadata", {}).get("catalog_id", ""))
            if cid and cid not in ids:
                ids.append(cid)
        return ids
