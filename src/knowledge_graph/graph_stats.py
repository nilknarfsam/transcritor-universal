"""Estatísticas do grafo de conhecimento."""

from __future__ import annotations

from collections import Counter
from typing import Any


def compute_graph_stats(
    nodes: dict[str, dict[str, Any]],
    edges: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    node_types = Counter(str(n.get("type", "")) for n in nodes.values())
    relations = Counter(str(e.get("relation", "")) for e in edges.values())

    doc_ids = {nid for nid, n in nodes.items() if n.get("type") == "document"}
    connected_docs: set[str] = set()
    for edge in edges.values():
        rel = str(edge.get("relation", ""))
        if not rel.startswith("related_by"):
            continue
        src, tgt = str(edge.get("source", "")), str(edge.get("target", ""))
        if src in doc_ids:
            connected_docs.add(src)
        if tgt in doc_ids:
            connected_docs.add(tgt)

    topic_counts: Counter[str] = Counter()
    ref_counts: Counter[str] = Counter()
    col_counts: Counter[str] = Counter()

    for node in nodes.values():
        ntype = str(node.get("type", ""))
        label = str(node.get("label", ""))
        if ntype == "topic" and label:
            topic_counts[label.lower()] += _degree(node["node_id"], edges)
        elif ntype == "bible_reference" and label:
            ref_counts[label.lower()] += _degree(node["node_id"], edges)
        elif ntype == "collection" and label:
            col_counts[label.lower()] += _degree(node["node_id"], edges)

    return {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "documents": node_types.get("document", 0),
        "connected_documents": len(connected_docs),
        "topics": node_types.get("topic", 0),
        "chunks": node_types.get("chunk", 0),
        "flashcards": node_types.get("flashcard", 0),
        "quizzes": node_types.get("quiz", 0),
        "top_topics": [
            {"label": k, "connections": v}
            for k, v in topic_counts.most_common(12)
        ],
        "top_references": [
            {"label": k, "connections": v}
            for k, v in ref_counts.most_common(12)
        ],
        "top_collections": [
            {"label": k, "connections": v}
            for k, v in col_counts.most_common(8)
        ],
        "relations": dict(relations.most_common()),
    }


def _degree(node_id: str, edges: dict[str, dict[str, Any]]) -> int:
    count = 0
    for edge in edges.values():
        if edge.get("source") == node_id or edge.get("target") == node_id:
            count += 1
    return count


def stats_display(stats: dict[str, Any]) -> str:
    if not stats:
        return "Grafo vazio — processe documentos para construir conexões."
    return (
        f"Nós: {stats.get('total_nodes', 0)} · "
        f"Arestas: {stats.get('total_edges', 0)} · "
        f"Documentos: {stats.get('documents', 0)} · "
        f"Conectados: {stats.get('connected_documents', 0)} · "
        f"Tópicos: {stats.get('topics', 0)} · "
        f"Chunks: {stats.get('chunks', 0)}"
    )
