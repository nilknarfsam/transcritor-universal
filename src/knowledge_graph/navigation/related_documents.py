"""Documentos relacionados via grafo e facetas compartilhadas."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from src.knowledge_graph.nodes.node_builder import document_node_id, make_node_id

if TYPE_CHECKING:
    from src.knowledge_graph.graph_engine import GraphEngine


class RelatedDocumentsFinder:
    def __init__(self, graph: "GraphEngine") -> None:
        self._graph = graph

    def find_related(
        self,
        catalog_id: str,
        *,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        from src.library import get_library

        lib = get_library()
        source = lib.catalog.get(catalog_id)
        if not source:
            return []

        scores: dict[str, dict[str, Any]] = {}
        doc_nid = document_node_id(catalog_id)

        for edge in self._graph.edges.values():
            rel = str(edge.get("relation", ""))
            if not rel.startswith("related_by"):
                continue
            src, tgt = str(edge.get("source", "")), str(edge.get("target", ""))
            other_nid = ""
            if src == doc_nid:
                other_nid = tgt
            elif tgt == doc_nid:
                other_nid = src
            else:
                continue
            if not other_nid.startswith("document:"):
                continue
            other_cid = other_nid.split(":", 1)[-1]
            if other_cid == catalog_id:
                continue
            weight = float(edge.get("weight", 1.0))
            meta = edge.get("metadata") or {}
            reasons = self._reasons_from_edge(rel, meta)
            if other_cid not in scores:
                scores[other_cid] = {
                    "document_id": other_cid,
                    "score": 0.0,
                    "reasons": [],
                }
            scores[other_cid]["score"] += weight
            for r in reasons:
                if r not in scores[other_cid]["reasons"]:
                    scores[other_cid]["reasons"].append(r)

        graph_ids = set(scores.keys())
        pairwise = self._pairwise_score(source, lib.catalog.all_entries, exclude_id=catalog_id)
        for cid, data in pairwise.items():
            if cid in scores:
                scores[cid]["score"] += data["score"]
                for r in data["reasons"]:
                    if r not in scores[cid]["reasons"]:
                        scores[cid]["reasons"].append(r)
            else:
                scores[cid] = data

        keyword_related = self._keyword_chunk_similarity(source, lib.catalog.all_entries)
        for cid, bonus in keyword_related.items():
            if cid in scores:
                scores[cid]["score"] += bonus
                if "similar_chunks" not in scores[cid]["reasons"]:
                    scores[cid]["reasons"].append("similar_chunks")
            elif bonus > 0.5:
                scores[cid] = {
                    "document_id": cid,
                    "score": bonus,
                    "reasons": ["similar_chunks"],
                }

        ranked = sorted(scores.values(), key=lambda x: -x["score"])
        for item in ranked:
            entry = lib.catalog.get(item["document_id"])
            if entry:
                item["title"] = entry.title
        return ranked[:limit]

    @staticmethod
    def _reasons_from_edge(relation: str, meta: dict[str, Any]) -> list[str]:
        mapping = {
            "related_by_topic": "shared_topics",
            "related_by_reference": "shared_references",
            "related_by_speaker": "shared_speaker",
            "related_by_collection": "shared_collection",
        }
        reasons = [mapping.get(relation, relation)]
        if meta.get("shared_topics"):
            reasons.append(f"topics:{','.join(meta['shared_topics'][:3])}")
        if meta.get("shared_references"):
            reasons.append(f"refs:{','.join(meta['shared_references'][:2])}")
        return reasons

    @staticmethod
    def _pairwise_score(
        source,
        entries: list,
        *,
        exclude_id: str,
    ) -> dict[str, dict[str, Any]]:
        scores: dict[str, dict[str, Any]] = {}
        topics_a = {t.lower() for t in source.topics if t}
        refs_a = {r.lower() for r in source.references if r}
        tags_a = {t.lower() for t in source.tags if t}

        for other in entries:
            if other.id == exclude_id or other.id == source.id:
                continue
            reasons: list[str] = []
            score = 0.0
            shared_topics = topics_a & {t.lower() for t in other.topics if t}
            if shared_topics:
                score += len(shared_topics) * 1.2
                reasons.append("shared_topics")
            shared_refs = refs_a & {r.lower() for r in other.references if r}
            if shared_refs:
                score += len(shared_refs) * 1.3
                reasons.append("shared_references")
            if (
                source.speaker.strip()
                and source.speaker.strip().lower() == other.speaker.strip().lower()
            ):
                score += 1.5
                reasons.append("shared_speaker")
            if source.collection_id and source.collection_id == other.collection_id:
                score += 1.0
                reasons.append("shared_collection")
            shared_tags = tags_a & {t.lower() for t in other.tags if t}
            if shared_tags:
                score += len(shared_tags) * 0.8
                reasons.append("shared_tags")
            if score > 0:
                scores[other.id] = {
                    "document_id": other.id,
                    "score": round(score, 2),
                    "reasons": reasons,
                }
        return scores

    @staticmethod
    def _keyword_chunk_similarity(source, entries: list) -> dict[str, float]:
        """Chunks semelhantes por palavras-chave (determinístico)."""
        def tokens(text: str) -> set[str]:
            return {w for w in re.findall(r"\w{4,}", text.lower()) if len(w) >= 4}

        source_tokens: set[str] = set()
        for ch in source.chunks or []:
            if isinstance(ch, dict):
                source_tokens |= tokens(str(ch.get("content", "")))
                source_tokens |= tokens(str(ch.get("title", "")))
        if not source_tokens:
            source_tokens = tokens(source.title)

        bonuses: dict[str, float] = {}
        for other in entries:
            if other.id == source.id:
                continue
            other_tokens: set[str] = set()
            for ch in other.chunks or []:
                if isinstance(ch, dict):
                    other_tokens |= tokens(str(ch.get("content", "")))
            overlap = source_tokens & other_tokens
            if len(overlap) >= 3:
                bonuses[other.id] = min(4.0, len(overlap) * 0.15)
        return bonuses
