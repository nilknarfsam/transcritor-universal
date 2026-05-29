"""Relatório Markdown de conhecimento — visão geral do workspace."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.core.settings_service import DATA_DIR
from src.knowledge.dashboard_stats import compute_dashboard_stats
from src.knowledge_graph.graph_stats import compute_graph_stats

if TYPE_CHECKING:
    from src.knowledge_graph.graph_engine import GraphEngine

REPORT_FILE = DATA_DIR / "knowledge_graph" / "knowledge_report.md"


class KnowledgeReportExporter:
    def __init__(self, graph: "GraphEngine") -> None:
        self._graph = graph

    def render(self) -> str:
        from src.library import get_library

        lib = get_library()
        lib.catalog.load()
        lib.workspaces.load()
        lib.collections.load()
        dash = compute_dashboard_stats()
        gstats = self._graph.stats or compute_graph_stats(
            self._graph.nodes, self._graph.edges
        )
        lines = [
            "# Visão Geral",
            "",
            f"- **Documentos:** {dash.documents}",
            f"- **Chunks:** {dash.chunks}",
            f"- **Flashcards:** {dash.flashcards}",
            f"- **Quizzes:** {dash.quizzes}",
            f"- **Tópicos no grafo:** {dash.topics}",
            f"- **Relações:** {dash.relations}",
            f"- **Grafo atualizado:** {self._graph.updated_at or '—'}",
            "",
            "# Workspaces",
            "",
        ]
        for ws in lib.workspaces.all:
            lines.append(f"- **{ws.get('name', '')}** (`{ws.get('id', '')}`)")
        if not lib.workspaces.all:
            lines.append("_Nenhum workspace._")

        lines.extend(["", "# Collections", ""])
        for col in lib.collections.all:
            lines.append(f"- **{col.get('name', '')}** — tags: {', '.join(col.get('tags') or [])}")
        if not lib.collections.all:
            lines.append("_Nenhuma coleção._")

        lines.extend(["", "# Tópicos Mais Frequentes", ""])
        lines.extend(self._bullets(gstats.get("top_topics", [])))

        lines.extend(["", "# Documentos Mais Conectados", ""])
        lines.extend(self._connected_documents())

        lines.extend(["", "# Estatísticas", ""])
        lines.append(f"- Nós no grafo: {gstats.get('total_nodes', 0)}")
        lines.append(f"- Arestas: {gstats.get('total_edges', 0)}")
        lines.append(f"- Documentos conectados: {gstats.get('connected_documents', 0)}")
        lines.append(
            f"- Tempo médio de processamento (histórico): "
            f"{dash.avg_processing_seconds:.1f}s"
            if dash.avg_processing_seconds
            else "- Tempo médio: —"
        )
        lines.append(
            f"- Cache hits (histórico): {dash.cache_hits}/{dash.cache_total}"
            if dash.cache_total
            else "- Cache hits: —"
        )

        lines.extend(["", "# Recomendações de Organização", ""])
        lines.extend(self._recommendations(dash, gstats, lib))
        return "\n".join(lines) + "\n"

    def write(self) -> Path:
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REPORT_FILE.write_text(self.render(), encoding="utf-8")
        return REPORT_FILE

    def _connected_documents(self) -> list[str]:
        related_counts: list[tuple[str, str, int]] = []
        for node in self._graph.nodes.values():
            if node.get("type") != "document":
                continue
            cid = str(node.get("metadata", {}).get("catalog_id", ""))
            if not cid:
                continue
            n = sum(
                1
                for e in self._graph.edges.values()
                if str(e.get("relation", "")).startswith("related_by")
                and (e.get("source") == node.get("node_id") or e.get("target") == node.get("node_id"))
            )
            if n:
                related_counts.append((cid, str(node.get("label", cid)), n))
        related_counts.sort(key=lambda x: -x[2])
        if not related_counts:
            return ["_Processe mais documentos para gerar conexões._"]
        return [f"- **{title}** — {count} relação(ões)" for _, title, count in related_counts[:15]]

    @staticmethod
    def _bullets(items: list[dict[str, Any]]) -> list[str]:
        if not items:
            return ["_Sem dados._"]
        return [f"- **{it.get('label', '—')}** — {it.get('connections', 0)} conexões" for it in items]

    @staticmethod
    def _recommendations(dash, gstats: dict, lib) -> list[str]:
        recs: list[str] = []
        if dash.documents < 3:
            recs.append("- Processe mais arquivos na fila para enriquecer o catálogo.")
        if int(gstats.get("connected_documents", 0)) < dash.documents // 2:
            recs.append("- Use tópicos e tags consistentes para aumentar relações entre documentos.")
        if dash.collections < 2:
            recs.append("- Crie coleções temáticas (Teologia, Cursos, Reuniões) antes de processar.")
        empty_ws = [ws for ws in lib.workspaces.all if not ws.get("collection_ids")]
        if empty_ws:
            recs.append(
                f"- Vincule coleções aos workspaces: {', '.join(str(w.get('name', '')) for w in empty_ws[:3])}."
            )
        if dash.flashcards == 0:
            recs.append("- Experimente o modo **study_mode** para gerar flashcards e quizzes.")
        if not recs:
            recs.append("- Biblioteca bem organizada. Continue usando workspaces e coleções por contexto.")
        return recs
