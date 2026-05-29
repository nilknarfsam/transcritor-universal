"""Navegação por tópico no grafo de conhecimento."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.knowledge_graph.nodes.node_builder import document_node_id, make_node_id

if TYPE_CHECKING:
    from src.knowledge_graph.graph_engine import GraphEngine


class TopicNavigator:
    def __init__(self, graph: "GraphEngine") -> None:
        self._graph = graph

    def explore(self, topic: str, *, limit: int = 30) -> dict[str, Any]:
        """Lista entidades conectadas a um tópico."""
        key = topic.strip()
        if not key:
            return self._empty(topic)

        topic_nid = make_node_id("topic", key)
        topic_lower = key.lower()
        from src.library import get_library

        lib = get_library()

        documents: list[dict[str, Any]] = []
        chunks: list[dict[str, Any]] = []
        flashcards: list[dict[str, Any]] = []
        quizzes: list[dict[str, Any]] = []
        references: list[dict[str, Any]] = []
        collections: list[dict[str, Any]] = []
        seen_docs: set[str] = set()

        for edge in self._graph.edges.values():
            if edge.get("target") != topic_nid and edge.get("source") != topic_nid:
                continue
            other_nid = (
                edge["source"] if edge["target"] == topic_nid else edge["target"]
            )
            self._collect_from_node(
                str(other_nid),
                documents,
                chunks,
                flashcards,
                quizzes,
                references,
                collections,
                seen_docs,
                limit,
                lib,
            )

        for entry in lib.catalog.all_entries:
            matched = any(t.lower() == topic_lower for t in entry.topics)
            if not matched:
                for ch in entry.chunks or []:
                    if isinstance(ch, dict) and any(
                        str(t).lower() == topic_lower for t in (ch.get("topics") or [])
                    ):
                        matched = True
                        break
            if matched and entry.id not in seen_docs:
                seen_docs.add(entry.id)
                documents.append({
                    "catalog_id": entry.id,
                    "title": entry.title,
                    "workspace": entry.workspace_name,
                    "collection": entry.collection_name,
                })

        for node in self._graph.nodes.values():
            if node.get("type") != "topic":
                continue
            if topic_lower in str(node.get("label", "")).lower():
                if node.get("node_id") != topic_nid:
                    continue
                break

        for ref in self._references_for_topic(topic_lower, lib):
            if len(references) < limit:
                references.append(ref)

        return {
            "topic": key,
            "topic_node_id": topic_nid,
            "documents": documents[:limit],
            "chunks": chunks[:limit],
            "flashcards": flashcards[:limit],
            "quizzes": quizzes[:limit],
            "references": references[:limit],
            "collections": collections[:limit],
            "total_connections": (
                len(documents) + len(chunks) + len(flashcards) + len(quizzes)
            ),
        }

    def _collect_from_node(
        self,
        node_id: str,
        documents: list,
        chunks: list,
        flashcards: list,
        quizzes: list,
        references: list,
        collections: list,
        seen_docs: set[str],
        limit: int,
        lib,
    ) -> None:
        node = self._graph.get_node(node_id)
        if not node:
            if node_id.startswith("document:"):
                cid = node_id.split(":", 1)[-1]
                entry = lib.catalog.get(cid)
                if entry and cid not in seen_docs:
                    seen_docs.add(cid)
                    documents.append({
                        "catalog_id": cid,
                        "title": entry.title,
                        "workspace": entry.workspace_name,
                        "collection": entry.collection_name,
                    })
            return

        ntype = node.get("type")
        meta = node.get("metadata") or {}

        if ntype == "document":
            cid = str(meta.get("catalog_id", node_id.split(":", 1)[-1]))
            if cid not in seen_docs:
                seen_docs.add(cid)
                entry = lib.catalog.get(cid)
                documents.append({
                    "catalog_id": cid,
                    "title": entry.title if entry else node.get("label"),
                    "workspace": entry.workspace_name if entry else "",
                    "collection": entry.collection_name if entry else "",
                })
            self._expand_document(
                node_id,
                chunks,
                flashcards,
                quizzes,
                references,
                collections,
                limit,
            )
        elif ntype == "chunk" and len(chunks) < limit:
            chunks.append({"node_id": node_id, "label": node.get("label"), "metadata": meta})
        elif ntype == "flashcard" and len(flashcards) < limit:
            flashcards.append({"node_id": node_id, "label": node.get("label"), "metadata": meta})
        elif ntype == "quiz" and len(quizzes) < limit:
            quizzes.append({"node_id": node_id, "label": node.get("label"), "metadata": meta})
        elif ntype == "bible_reference" and len(references) < limit:
            references.append({"node_id": node_id, "label": node.get("label")})
        elif ntype == "collection" and len(collections) < limit:
            collections.append({"node_id": node_id, "label": node.get("label")})

    def _expand_document(
        self,
        doc_nid: str,
        chunks: list,
        flashcards: list,
        quizzes: list,
        references: list,
        collections: list,
        limit: int,
    ) -> None:
        for edge in self._graph.edges.values():
            if edge.get("source") != doc_nid:
                continue
            tgt = str(edge.get("target", ""))
            rel = str(edge.get("relation", ""))
            node = self._graph.get_node(tgt)
            if not node:
                continue
            ntype = node.get("type")
            item = {"node_id": tgt, "label": node.get("label"), "relation": rel}
            if ntype == "chunk" and len(chunks) < limit:
                chunks.append(item)
            elif ntype == "flashcard" and len(flashcards) < limit:
                flashcards.append(item)
            elif ntype == "quiz" and len(quizzes) < limit:
                quizzes.append(item)
            elif ntype == "bible_reference" and len(references) < limit:
                references.append(item)
            elif ntype == "collection" and len(collections) < limit:
                collections.append(item)

    @staticmethod
    def _references_for_topic(topic_lower: str, lib) -> list[dict[str, str]]:
        refs: list[dict[str, str]] = []
        seen: set[str] = set()
        for entry in lib.catalog.all_entries:
            if not any(t.lower() == topic_lower for t in entry.topics):
                continue
            for r in entry.references:
                rl = r.lower()
                if rl not in seen:
                    seen.add(rl)
                    refs.append({"reference": r, "document_id": entry.id, "title": entry.title})
        return refs

    @staticmethod
    def _empty(topic: str) -> dict[str, Any]:
        return {
            "topic": topic,
            "topic_node_id": "",
            "documents": [],
            "chunks": [],
            "flashcards": [],
            "quizzes": [],
            "references": [],
            "collections": [],
            "total_connections": 0,
        }
