"""Orquestrador do grafo de conhecimento — persistência e rebuild."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.knowledge_graph.navigation.related_documents import RelatedDocumentsFinder
    from src.knowledge_graph.navigation.topic_navigator import TopicNavigator
    from src.knowledge_graph.search.semantic_search import SemanticSearchEngine

from src.core.settings_service import DATA_DIR, SettingsService
from src.knowledge_graph.edges.edge_builder import EdgeBuilder
from src.knowledge_graph.graph_stats import compute_graph_stats
from src.knowledge_graph.nodes.node_builder import NodeBuilder, document_node_id

GRAPH_DIR = DATA_DIR / "knowledge_graph"
GRAPH_FILE = GRAPH_DIR / "graph.json"
GRAPH_EXPORT_FILE = GRAPH_DIR / "graph_export.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_study_sidecars(output_path: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not output_path:
        return [], []
    base = str(Path(output_path).with_suffix(""))
    flashcards: list[dict[str, Any]] = []
    quizzes: list[dict[str, Any]] = []
    fc_path = Path(f"{base}_flashcards.json")
    qz_path = Path(f"{base}_quizzes.json")
    if fc_path.is_file():
        try:
            with open(fc_path, encoding="utf-8") as f:
                data = json.load(f)
            flashcards = list(data.get("flashcards") or [])
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    if qz_path.is_file():
        try:
            with open(qz_path, encoding="utf-8") as f:
                data = json.load(f)
            quizzes = list(data.get("quizzes") or [])
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    return flashcards, quizzes


class GraphEngine:
    def __init__(self) -> None:
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: dict[str, dict[str, Any]] = {}
        self._updated_at: str = ""
        self._stats: dict[str, Any] = {}
        self._node_builder = NodeBuilder()
        self._edge_builder = EdgeBuilder()
        self._search: SemanticSearchEngine | None = None
        self._related: RelatedDocumentsFinder | None = None
        self._topics: TopicNavigator | None = None
        GRAPH_DIR.mkdir(parents=True, exist_ok=True)
        self.load()

    @property
    def search(self) -> "SemanticSearchEngine":
        if self._search is None:
            from src.knowledge_graph.search.semantic_search import SemanticSearchEngine

            self._search = SemanticSearchEngine(self)
        return self._search

    @property
    def related(self) -> "RelatedDocumentsFinder":
        if self._related is None:
            from src.knowledge_graph.navigation.related_documents import RelatedDocumentsFinder

            self._related = RelatedDocumentsFinder(self)
        return self._related

    @property
    def topics(self) -> "TopicNavigator":
        if self._topics is None:
            from src.knowledge_graph.navigation.topic_navigator import TopicNavigator

            self._topics = TopicNavigator(self)
        return self._topics

    @property
    def nodes(self) -> dict[str, dict[str, Any]]:
        return self._nodes

    @property
    def edges(self) -> dict[str, dict[str, Any]]:
        return self._edges

    @property
    def updated_at(self) -> str:
        return self._updated_at

    @property
    def stats(self) -> dict[str, Any]:
        return self._stats

    def load(self) -> None:
        if not GRAPH_FILE.exists():
            self._nodes = {}
            self._edges = {}
            self._updated_at = ""
            self._stats = {}
            return
        try:
            with open(GRAPH_FILE, encoding="utf-8") as f:
                data = json.load(f)
            self._nodes = data.get("nodes", {}) if isinstance(data.get("nodes"), dict) else {}
            self._edges = data.get("edges", {}) if isinstance(data.get("edges"), dict) else {}
            self._updated_at = str(data.get("updated_at", ""))
            self._stats = data.get("stats", {}) if isinstance(data.get("stats"), dict) else {}
        except (json.JSONDecodeError, OSError, TypeError):
            self._nodes = {}
            self._edges = {}
            self._updated_at = ""
            self._stats = {}

    def save(self) -> None:
        GRAPH_DIR.mkdir(parents=True, exist_ok=True)
        self._stats = compute_graph_stats(self._nodes, self._edges)
        self._updated_at = _utc_now()
        payload = {
            "version": 1,
            "nodes": self._nodes,
            "edges": self._edges,
            "updated_at": self._updated_at,
            "stats": self._stats,
        }
        with open(GRAPH_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        return self._nodes.get(node_id)

    def document_node_id(self, catalog_id: str) -> str:
        return document_node_id(catalog_id)

    def rebuild(self, *, settings: SettingsService | None = None) -> dict[str, Any]:
        """Rebuild seguro a partir de catálogo, workspaces, coleções, histórico e exports de estudo."""
        from src.library import get_library

        lib = get_library()
        lib.catalog.load()
        lib.workspaces.load()
        lib.collections.load()

        self._node_builder.clear()
        self._edge_builder.clear()

        ws_items = lib.workspaces._items if hasattr(lib.workspaces, "_items") else {}
        col_items = lib.collections._items if hasattr(lib.collections, "_items") else {}

        self._node_builder.build_workspace_nodes(ws_items)
        self._node_builder.build_collection_nodes(col_items)

        entries = lib.catalog.all_entries
        study_from_history = self._study_hints_from_history(settings)

        for entry in entries:
            flashcards, quizzes = _load_study_sidecars(entry.output_path)
            if not flashcards and not quizzes:
                hint = study_from_history.get(entry.id, {})
                flashcards = hint.get("flashcards", [])
                quizzes = hint.get("quizzes", [])

            self._node_builder.build_document_nodes(
                entry,
                flashcards=flashcards,
                quizzes=quizzes,
            )
            self._edge_builder.build_document_edges(
                entry,
                flashcard_count=len(flashcards),
                quiz_count=len(quizzes),
            )

        for ws in ws_items.values():
            ws_id = str(ws.get("id", ""))
            for col_id in list(ws.get("collection_ids") or []):
                self._edge_builder.add_edge_unique(
                    f"workspace:{ws_id}",
                    f"collection:{col_id}",
                    "belongs_to_collection",
                    metadata={"link": "workspace_collection"},
                )

        self._edge_builder.build_cross_document_edges(entries)

        self._nodes = self._node_builder.nodes
        self._edges = self._edge_builder.edges
        self.save()
        return self._stats

    @staticmethod
    def _study_hints_from_history(
        settings: SettingsService | None,
    ) -> dict[str, dict[str, list]]:
        """Mapeia catalog_id → exports de estudo a partir do histórico (quando sidecars ausentes)."""
        hints: dict[str, dict[str, list]] = {}
        if settings is None:
            return hints
        for row in settings.history:
            cid = str(row.get("catalog_id", "")).strip()
            if not cid:
                continue
            fc = int(row.get("flashcards_count", "0") or 0)
            qz = int(row.get("quizzes_count", "0") or 0)
            if fc or qz:
                hints.setdefault(cid, {"flashcards": [], "quizzes": []})
        return hints

    def on_document_registered(self, catalog_id: str) -> dict[str, Any]:
        """Atualização incremental após novo documento no catálogo."""
        return self.rebuild()

    def history_fields_for_document(self, catalog_id: str) -> dict[str, str]:
        if not catalog_id:
            return {}
        node_id = document_node_id(catalog_id)
        related = self.related.find_related(catalog_id, limit=50)
        return {
            "graph_node_id": node_id,
            "related_documents_count": str(len(related)),
            "semantic_search_hits": "0",
            "graph_updated_at": self._updated_at or _utc_now(),
        }

    def export_markdown(self) -> str:
        from src.knowledge_graph.exporters.graph_exporter import GraphExporter

        exporter = GraphExporter(self)
        path = exporter.write()
        return str(path)

    def export_knowledge_report(self) -> str:
        from src.knowledge_graph.exporters.knowledge_report_exporter import KnowledgeReportExporter

        exporter = KnowledgeReportExporter(self)
        path = exporter.write()
        return str(path)
