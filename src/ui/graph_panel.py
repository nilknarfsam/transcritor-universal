"""Painel Grafo / Conexões — navegação premium e relações."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from src.knowledge_graph import get_knowledge_graph
from src.knowledge_graph.graph_stats import stats_display
from src.ui.components.knowledge_widgets import EmptyState, ResultCard, SectionHeader
from src.ui.design.fonts import body_small, caption, panel_title
from src.ui.design.spacing import Layout
from src.ui.design.theme_manager import ThemeManager

RELATION_FILTERS = [
    "(todas)",
    "related_by_topic",
    "related_by_reference",
    "related_by_speaker",
    "related_by_collection",
]


class GraphPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        theme: ThemeManager,
        on_status: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.theme = theme
        self.on_status = on_status
        self._graph = get_knowledge_graph()
        self._relation_filter = ctk.StringVar(value="(todas)")

        self._apply_frame_style()
        self._build_header()
        self._build_stats()
        self._build_topic_cards()
        self._build_relation_filter()
        self._build_search()
        self._build_results()
        self._build_topic()
        self.refresh()

    def _apply_frame_style(self) -> None:
        self.configure(**self.theme.frame_kwargs(elevated=True))

    def refresh_theme(self) -> None:
        self._apply_frame_style()
        colors = self.theme.colors()
        self.stats_label.configure(text_color=colors["text_secondary"])
        self.refresh()

    def _build_header(self) -> None:
        colors = self.theme.colors()
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=Layout.LG, pady=(Layout.LG, Layout.SM))
        ctk.CTkLabel(
            header,
            text="Grafo / Conexões",
            font=panel_title(),
            text_color=colors["text_primary"],
        ).pack(side="left")
        ctk.CTkButton(
            header,
            text="Relatório",
            width=88,
            command=self._export_report,
            **self.theme.ghost_button_kwargs(),
        ).pack(side="right", padx=(Layout.XS, 0))
        ctk.CTkButton(
            header,
            text="Exportar grafo",
            width=110,
            command=self._export,
            **self.theme.ghost_button_kwargs(),
        ).pack(side="right", padx=(Layout.XS, 0))
        ctk.CTkButton(
            header,
            text="Rebuild",
            width=80,
            command=self._rebuild,
            **self.theme.ghost_button_kwargs(),
        ).pack(side="right")

    def _build_stats(self) -> None:
        colors = self.theme.colors()
        self.stats_label = ctk.CTkLabel(
            self,
            text="",
            font=caption(),
            text_color=colors["text_secondary"],
            anchor="w",
            justify="left",
        )
        self.stats_label.pack(fill="x", padx=Layout.LG, pady=(0, Layout.SM))

    def _build_topic_cards(self) -> None:
        self.topics_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.topics_frame.pack(fill="x", padx=Layout.LG, pady=(0, Layout.SM))

    def _build_relation_filter(self) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=Layout.LG, pady=(0, Layout.SM))
        colors = self.theme.colors()
        ctk.CTkLabel(
            row,
            text="Filtrar relação",
            font=body_small(),
            text_color=colors["text_secondary"],
        ).pack(side="left", padx=(0, Layout.SM))
        ctk.CTkOptionMenu(
            row,
            values=RELATION_FILTERS,
            variable=self._relation_filter,
            command=lambda _v: self._refresh_related_view(),
            width=180,
            **self.theme.option_menu_kwargs(),
        ).pack(side="left")

    def _build_search(self) -> None:
        colors = self.theme.colors()
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=Layout.LG, pady=(0, Layout.SM))
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            row,
            text="Busca no grafo",
            font=body_small(),
            text_color=colors["text_secondary"],
        ).grid(row=0, column=0, sticky="w", padx=(0, Layout.SM))
        self.search_entry = ctk.CTkEntry(
            row,
            placeholder_text="tópico, referência, tag, chunk…",
        )
        self.search_entry.grid(row=0, column=1, sticky="ew")
        self.search_entry.bind("<Return>", lambda _e: self._run_search())
        ctk.CTkButton(
            row,
            text="Buscar",
            width=80,
            command=self._run_search,
            **self.theme.accent_button_kwargs(),
        ).grid(row=0, column=2, padx=(Layout.SM, 0))

    def _build_results(self) -> None:
        self.results_scroll = ctk.CTkScrollableFrame(
            self,
            label_text="Conexões e resultados",
            fg_color="transparent",
        )
        self.results_scroll.pack(fill="both", expand=True, padx=Layout.LG, pady=(0, Layout.SM))

    def _build_topic(self) -> None:
        colors = self.theme.colors()
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=Layout.LG, pady=(0, Layout.LG))
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            row,
            text="Navegar tópico",
            font=body_small(),
            text_color=colors["text_secondary"],
        ).grid(row=0, column=0, sticky="w", padx=(0, Layout.SM))
        self.topic_entry = ctk.CTkEntry(row, placeholder_text="ex.: ressurreição")
        self.topic_entry.grid(row=0, column=1, sticky="ew")
        ctk.CTkButton(
            row,
            text="Explorar",
            width=80,
            command=self._explore_topic,
            **self.theme.ghost_button_kwargs(),
        ).grid(row=0, column=2, padx=(Layout.SM, 0))

    def refresh(self) -> None:
        self._graph.load()
        self.stats_label.configure(text=stats_display(self._graph.stats))
        self._render_topic_cards()

    def _render_topic_cards(self) -> None:
        for w in self.topics_frame.winfo_children():
            w.destroy()
        top = (self._graph.stats or {}).get("top_topics", [])[:6]
        if not top:
            return
        colors = self.theme.colors()
        ctk.CTkLabel(
            self.topics_frame,
            text="Tópicos mais conectados",
            font=body_small(),
            text_color=colors["text_primary"],
        ).pack(anchor="w", pady=(0, Layout.XS))
        row = ctk.CTkFrame(self.topics_frame, fg_color="transparent")
        row.pack(fill="x")
        for item in top:
            label = str(item.get("label", ""))
            count = item.get("connections", 0)
            card = ctk.CTkFrame(
                row,
                fg_color=colors["card_bg"],
                corner_radius=Layout.CORNER_RADIUS_CARD,
                border_width=1,
                border_color=colors["border"],
            )
            card.pack(side="left", padx=(0, Layout.XS), pady=Layout.XS)
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(padx=Layout.SM, pady=Layout.SM)
            ctk.CTkLabel(
                inner,
                text=label[:20],
                font=body_small(),
                text_color=colors["text_primary"],
            ).pack()
            ctk.CTkLabel(
                inner,
                text=f"{count} links",
                font=caption(),
                text_color=colors["text_muted"],
            ).pack()
            card.bind(
                "<Button-1>",
                lambda _e, t=label: self._explore_topic_named(t),
            )

    def _explore_topic_named(self, topic: str) -> None:
        self.topic_entry.delete(0, "end")
        self.topic_entry.insert(0, topic)
        self._explore_topic()

    def _rebuild(self) -> None:
        try:
            self._graph.rebuild()
            self.refresh()
            if self.on_status:
                self.on_status("Grafo reconstruído com segurança.")
        except OSError as exc:
            if self.on_status:
                self.on_status(f"Erro ao reconstruir: {exc}")

    def _export(self) -> None:
        try:
            path = self._graph.export_markdown()
            if self.on_status:
                self.on_status(f"Grafo exportado: {path}")
        except OSError as exc:
            if self.on_status:
                self.on_status(f"Erro: {exc}")

    def _export_report(self) -> None:
        try:
            path = self._graph.export_knowledge_report()
            if self.on_status:
                self.on_status(f"Relatório: {path}")
        except OSError as exc:
            if self.on_status:
                self.on_status(f"Erro: {exc}")

    def _run_search(self) -> None:
        query = self.search_entry.get().strip()
        for w in self.results_scroll.winfo_children():
            w.destroy()

        if not query:
            EmptyState(
                self.results_scroll,
                "Digite um termo para buscar no grafo.",
                self.theme,
            ).pack(fill="x", pady=Layout.MD)
            return

        result = self._graph.search.search(query)
        SectionHeader(
            self.results_scroll,
            f"Resultados ({result.total_hits})",
            self.theme,
        ).pack(fill="x", pady=(0, Layout.SM))

        for doc in result.documents[:12]:
            self._add_result_card(
                str(doc.get("label", "")),
                "document",
                float(doc.get("score", 0)),
                ", ".join(doc.get("reasons", [])) or "semantic",
            )
        for chunk in result.chunks[:6]:
            self._add_result_card(str(chunk.get("label", ""))[:70], "chunk", float(chunk.get("score", 0)), "chunk")
        if result.connection_reasons:
            ctk.CTkLabel(
                self.results_scroll,
                text=f"Motivos: {', '.join(result.connection_reasons[:10])}",
                font=caption(),
                text_color=self.theme.colors()["text_muted"],
                wraplength=680,
            ).pack(anchor="w", pady=Layout.SM)

        if self.on_status:
            self.on_status(f"Grafo: {result.total_hits} hit(s).")

    def _add_result_card(self, title: str, rtype: str, score: float, reason: str) -> None:
        ResultCard(
            self.results_scroll,
            theme=self.theme,
            title=title,
            result_type=rtype,
            score=score,
            match_reason=reason,
        ).pack(fill="x", pady=Layout.XS)

    def _explore_topic(self) -> None:
        topic = self.topic_entry.get().strip()
        if not topic:
            return
        nav = self._graph.topics.explore(topic)
        for w in self.results_scroll.winfo_children():
            w.destroy()
        SectionHeader(
            self.results_scroll,
            f"Tópico: {nav.get('topic', topic)}",
            self.theme,
            subtitle=f"{nav.get('total_connections', 0)} conexões",
        ).pack(fill="x", pady=(0, Layout.SM))
        for doc in nav.get("documents", [])[:10]:
            self._add_result_card(
                str(doc.get("title", "")),
                "document",
                1.0,
                str(doc.get("collection", "")),
            )
        if self.on_status:
            self.on_status(f"Tópico «{topic}»: {nav.get('total_connections', 0)} itens.")

    def show_related(self, catalog_id: str, title: str = "") -> None:
        self._current_catalog_id = catalog_id
        self._current_title = title
        for w in self.results_scroll.winfo_children():
            w.destroy()
        SectionHeader(
            self.results_scroll,
            f"Relacionados: {title[:50] or catalog_id}",
            self.theme,
        ).pack(fill="x", pady=(0, Layout.SM))
        self._render_related_cards(catalog_id)

    def _refresh_related_view(self) -> None:
        if hasattr(self, "_current_catalog_id"):
            self.show_related(self._current_catalog_id, getattr(self, "_current_title", ""))

    def _render_related_cards(self, catalog_id: str) -> None:
        related = self._graph.related.find_related(catalog_id)
        filt = self._relation_filter.get()
        colors = self.theme.colors()

        if not related:
            EmptyState(
                self.results_scroll,
                "Nenhum documento relacionado.",
                self.theme,
                hint="Adicione tópicos ou referências compartilhadas.",
            ).pack(fill="x", pady=Layout.MD)
            return

        for rel in related:
            reasons = rel.get("reasons", [])
            if filt != "(todas)":
                mapped = filt.replace("related_by_", "shared_")
                if not any(mapped in r or filt in r for r in reasons):
                    continue
            reason_text = ", ".join(reasons)
            card = ctk.CTkFrame(
                self.results_scroll,
                fg_color=colors["card_bg"],
                corner_radius=Layout.CORNER_RADIUS_CARD,
                border_width=1,
                border_color=colors["border"],
            )
            card.pack(fill="x", pady=Layout.XS)
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=Layout.SM, pady=Layout.SM)
            ctk.CTkLabel(
                inner,
                text=rel.get("title", rel.get("document_id", ""))[:60],
                font=body_small(),
                text_color=colors["text_primary"],
                anchor="w",
            ).pack(fill="x")
            ctk.CTkLabel(
                inner,
                text=f"Score {rel.get('score', 0):.1f} · {reason_text}",
                font=caption(),
                text_color=colors["accent"],
                anchor="w",
                wraplength=650,
            ).pack(fill="x")
