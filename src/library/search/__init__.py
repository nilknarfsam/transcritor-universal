"""Busca na biblioteca — import leve para evitar ciclo library ↔ knowledge_graph."""

from src.library.search.search_engine import LibrarySearchEngine, SearchResult

__all__ = [
    "LibrarySearchEngine",
    "SearchResult",
    "UnifiedSearchEngine",
    "UnifiedSearchHit",
    "UnifiedSearchResult",
]


def __getattr__(name: str):
    if name in ("UnifiedSearchEngine", "UnifiedSearchHit", "UnifiedSearchResult"):
        from src.library.search.unified_search_engine import (
            UnifiedSearchEngine,
            UnifiedSearchHit,
            UnifiedSearchResult,
        )
        return {
            "UnifiedSearchEngine": UnifiedSearchEngine,
            "UnifiedSearchHit": UnifiedSearchHit,
            "UnifiedSearchResult": UnifiedSearchResult,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
