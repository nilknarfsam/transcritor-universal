"""Busca textual local no catálogo — sem embeddings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from src.library.catalog.catalog_registry import CatalogEntry, CatalogRegistry

SortField = Literal["title", "created_at", "semantic_score", "updated_at"]
SortOrder = Literal["asc", "desc"]


@dataclass
class SearchResult:
    entry: CatalogEntry
    score: float
    matched_fields: list[str]


class LibrarySearchEngine:
    def __init__(self, catalog: CatalogRegistry) -> None:
        self._catalog = catalog

    def search(
        self,
        query: str = "",
        *,
        workspace_id: str = "",
        collection_id: str = "",
        speaker: str = "",
        author: str = "",
        sort_by: SortField = "updated_at",
        sort_order: SortOrder = "desc",
        limit: int = 200,
    ) -> list[SearchResult]:
        q = query.strip().lower()
        results: list[SearchResult] = []

        for entry in self._catalog.all_entries:
            if workspace_id and entry.workspace_id != workspace_id:
                continue
            if collection_id and entry.collection_id != collection_id:
                continue
            if speaker and speaker.lower() not in entry.speaker.lower():
                continue
            if author and author.lower() not in entry.author.lower():
                continue

            matched: list[str] = []
            score = 0.0

            if q:
                score, matched = self._match_query(entry, q)
                if score <= 0:
                    continue
            else:
                score = 1.0

            results.append(SearchResult(entry=entry, score=score, matched_fields=matched))

        results.sort(
            key=lambda r: self._sort_key(r.entry, sort_by),
            reverse=(sort_order == "desc"),
        )
        return results[:limit]

    @staticmethod
    def _sort_key(entry: CatalogEntry, field: SortField) -> Any:
        if field == "title":
            return entry.title.lower()
        if field == "semantic_score":
            return entry.semantic_score
        if field == "created_at":
            return entry.created_at
        return entry.updated_at

    @staticmethod
    def _match_query(entry: CatalogEntry, q: str) -> tuple[float, list[str]]:
        matched: list[str] = []
        score = 0.0
        checks: list[tuple[str, str, float]] = [
            ("title", entry.title, 10.0),
            ("speaker", entry.speaker, 8.0),
            ("author", entry.author, 8.0),
            ("collection", entry.collection_name, 6.0),
            ("workspace", entry.workspace_name, 5.0),
            ("category", entry.category, 4.0),
        ]
        for field, value, weight in checks:
            if value and q in value.lower():
                matched.append(field)
                score += weight

        for topic in entry.topics:
            if q in str(topic).lower():
                matched.append("topics")
                score += 5.0
                break

        for tag in entry.tags:
            if q in str(tag).lower():
                matched.append("tags")
                score += 4.0
                break

        for ref in entry.references:
            if q in str(ref).lower():
                matched.append("references")
                score += 6.0
                break

        return score, matched

    def list_topics(self, *, workspace_id: str = "", limit: int = 50) -> list[tuple[str, int]]:
        counts: dict[str, int] = {}
        for entry in self._catalog.all_entries:
            if workspace_id and entry.workspace_id != workspace_id:
                continue
            for t in entry.topics:
                key = str(t).strip()
                if key:
                    counts[key] = counts.get(key, 0) + 1
        return sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:limit]
