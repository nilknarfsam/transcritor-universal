"""Knowledge Graph Foundation — busca semântica local e grafo de conhecimento."""

from __future__ import annotations

from typing import Optional

from src.knowledge_graph.graph_engine import GraphEngine

_instance: Optional[GraphEngine] = None


def get_knowledge_graph() -> GraphEngine:
    global _instance
    if _instance is None:
        _instance = GraphEngine()
    return _instance


__all__ = ["GraphEngine", "get_knowledge_graph"]
