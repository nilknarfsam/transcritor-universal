"""Busca unificada — catálogo + grafo semântico com filtros."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.library.catalog.catalog_registry import CatalogEntry
from src.library.search.search_engine import SearchResult

NODE_TYPE_LABELS = {
    "(todos)": "",
    "document": "document",
    "topic": "topic",
    "tag": "tag",
    "chunk": "chunk",
    "flashcard": "flashcard",
    "quiz": "quiz",
    "bible_reference": "bible_reference",
    "speaker": "speaker",
    "author": "author",
    "collection": "collection",
    "workspace": "workspace",
    "highlight": "highlight",
}


@dataclass
class UnifiedSearchHit:
    hit_id: str
    result_type: str
    title: str
    score: float
    match_reason: str
    workspace: str = ""
    collection: str = ""
    topics: list[str] = field(default_factory=list)
    catalog_id: str = ""
    export_mode: str = ""
    template: str = ""
    difficulty: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_card_dict(self) -> dict[str, Any]:
        return {
            "hit_id": self.hit_id,
            "result_type": self.result_type,
            "title": self.title,
            "score": self.score,
            "match_reason": self.match_reason,
            "workspace": self.workspace,
            "collection": self.collection,
            "topics": self.topics,
            "catalog_id": self.catalog_id,
        }


@dataclass
class UnifiedSearchResult:
    query: str
    hits: list[UnifiedSearchHit] = field(default_factory=list)
    total: int = 0
    filters_applied: dict[str, str] = field(default_factory=dict)


class UnifiedSearchEngine:
    def search(
        self,
        query: str = "",
        *,
        workspace_id: str = "",
        collection_id: str = "",
        node_type: str = "",
        template: str = "",
        export_mode: str = "",
        difficulty: str = "",
        limit: int = 60,
    ) -> UnifiedSearchResult:
        from src.knowledge_graph import get_knowledge_graph
        from src.library import get_library

        lib = get_library()
        lib.catalog.load()
        graph = get_knowledge_graph()
        graph.load()

        q = query.strip()
        node_filter = NODE_TYPE_LABELS.get(node_type, node_type) if node_type else ""
        hits: list[UnifiedSearchHit] = []
        seen: set[str] = set()

        if q:
            catalog_hits = self._from_catalog_search(
                lib, q, workspace_id, collection_id, template, export_mode, difficulty
            )
            graph_hits = self._from_graph_search(graph, q, workspace_id, collection_id)
            for hit in catalog_hits + graph_hits:
                key = f"{hit.result_type}:{hit.hit_id}"
                if key in seen:
                    continue
                if node_filter and hit.result_type != node_filter:
                    continue
                seen.add(key)
                hits.append(hit)
        else:
            for entry in lib.catalog.all_entries:
                if workspace_id and entry.workspace_id != workspace_id:
                    continue
                if collection_id and entry.collection_id != collection_id:
                    continue
                if template and template != "(todos)" and entry.template != template:
                    continue
                if export_mode and export_mode != "(todos)" and entry.export_mode != export_mode:
                    continue
                diff = self._difficulty_for_entry(entry)
                if difficulty and difficulty != "(todos)" and diff != difficulty:
                    continue
                hit = self._entry_to_hit(entry, score=1.0, reason="catalog_list")
                if node_filter and hit.result_type != node_filter:
                    continue
                key = f"{hit.result_type}:{hit.hit_id}"
                if key not in seen:
                    seen.add(key)
                    hits.append(hit)

        hits.sort(key=lambda h: (-h.score, h.title.lower()))
        return UnifiedSearchResult(
            query=query,
            hits=hits[:limit],
            total=len(hits),
            filters_applied={
                "workspace_id": workspace_id,
                "collection_id": collection_id,
                "node_type": node_type,
                "template": template,
                "export_mode": export_mode,
                "difficulty": difficulty,
            },
        )

    def _from_catalog_search(
        self,
        lib,
        query: str,
        workspace_id: str,
        collection_id: str,
        template: str,
        export_mode: str,
        difficulty: str,
    ) -> list[UnifiedSearchHit]:
        results: list[SearchResult] = lib.search_documents(
            query=query,
            workspace_id=workspace_id,
            collection_id=collection_id,
            limit=80,
        )
        hits: list[UnifiedSearchHit] = []
        for result in results:
            entry = result.entry
            if template and template != "(todos)" and entry.template != template:
                continue
            if export_mode and export_mode != "(todos)" and entry.export_mode != export_mode:
                continue
            diff = self._difficulty_for_entry(entry)
            if difficulty and difficulty != "(todos)" and diff != difficulty:
                continue
            reason = ", ".join(result.matched_fields) if result.matched_fields else "catalog_match"
            hits.append(self._entry_to_hit(entry, score=result.score, reason=reason))
            hits.extend(self._highlights_from_entry(entry, query))
        return hits

    def _from_graph_search(
        self,
        graph,
        query: str,
        workspace_id: str,
        collection_id: str,
    ) -> list[UnifiedSearchHit]:
        from src.library import get_library

        lib = get_library()
        sem = graph.search.search(query, limit=50)
        hits: list[UnifiedSearchHit] = []

        buckets = [
            ("document", sem.documents),
            ("topic", sem.topics),
            ("tag", sem.topics),
            ("chunk", sem.chunks),
            ("flashcard", sem.flashcards),
            ("quiz", sem.quizzes),
            ("bible_reference", sem.references),
            ("collection", sem.collections),
            ("workspace", sem.workspaces),
        ]
        for rtype, items in buckets:
            if rtype == "tag":
                continue
            for item in items:
                meta = item.get("metadata") or {}
                cid = str(meta.get("catalog_id", "") or item.get("catalog_id", ""))
                ws, col = "", ""
                if cid:
                    entry = lib.catalog.get(cid)
                    if entry:
                        if workspace_id and entry.workspace_id != workspace_id:
                            continue
                        if collection_id and entry.collection_id != collection_id:
                            continue
                        ws, col = entry.workspace_name, entry.collection_name
                reasons = ", ".join(item.get("reasons", [])[:3]) or "semantic_match"
                hits.append(
                    UnifiedSearchHit(
                        hit_id=str(item.get("node_id") or item.get("catalog_id") or item.get("label", "")),
                        result_type=rtype,
                        title=str(item.get("label", ""))[:120],
                        score=float(item.get("score", 1.0)),
                        match_reason=reasons,
                        workspace=ws,
                        collection=col,
                        catalog_id=cid,
                        metadata=meta,
                    )
                )

        for item in sem.topics:
            hits.append(
                UnifiedSearchHit(
                    hit_id=str(item.get("node_id", "")),
                    result_type="topic",
                    title=str(item.get("label", "")),
                    score=float(item.get("score", 1.0)),
                    match_reason="topic_match",
                    metadata=item.get("metadata") or {},
                )
            )
        return hits

    @staticmethod
    def _entry_to_hit(entry: CatalogEntry, *, score: float, reason: str) -> UnifiedSearchHit:
        return UnifiedSearchHit(
            hit_id=entry.id,
            result_type="document",
            title=entry.title,
            score=score,
            match_reason=reason,
            workspace=entry.workspace_name,
            collection=entry.collection_name,
            topics=list(entry.topics[:6]),
            catalog_id=entry.id,
            export_mode=entry.export_mode,
            template=entry.template,
            difficulty=UnifiedSearchEngine._difficulty_for_entry(entry),
            metadata={"output_path": entry.output_path},
        )

    @staticmethod
    def _highlights_from_entry(entry: CatalogEntry, query: str) -> list[UnifiedSearchHit]:
        q = query.lower()
        hits: list[UnifiedSearchHit] = []
        for i, hl in enumerate(entry.highlights):
            text = str(hl)
            if q in text.lower():
                hits.append(
                    UnifiedSearchHit(
                        hit_id=f"{entry.id}:hl:{i}",
                        result_type="highlight",
                        title=text[:100],
                        score=3.0,
                        match_reason="highlight_match",
                        workspace=entry.workspace_name,
                        collection=entry.collection_name,
                        catalog_id=entry.id,
                    )
                )
        return hits

    @staticmethod
    def _difficulty_for_entry(entry: CatalogEntry) -> str:
        from src.knowledge_graph.graph_engine import _load_study_sidecars

        _, quizzes = _load_study_sidecars(entry.output_path)
        if quizzes:
            return str(quizzes[0].get("difficulty", "")) or ""
        if entry.export_mode == "study_mode":
            return "intermediário"
        return ""
