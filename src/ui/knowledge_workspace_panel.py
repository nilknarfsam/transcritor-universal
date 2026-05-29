"""Workspace premium — busca unificada, cards e detalhe."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from src.knowledge import compute_dashboard_stats
from src.library.search.unified_search_engine import UnifiedSearchEngine, UnifiedSearchHit
from src.ui.components.knowledge_widgets import EmptyState, ResultCard, SectionHeader, StatCard
from src.ui.design.fonts import body_small, caption, panel_title
from src.ui.design.spacing import Layout
from src.ui.design.theme_manager import ThemeManager
from src.ui.document_detail_panel import DocumentDetailPanel


class KnowledgeWorkspacePanel(ctk.CTkFrame):
    NODE_TYPES = [
        "(todos)",
        "document",
        "topic",
        "chunk",
        "flashcard",
        "quiz",
        "highlight",
        "bible_reference",
        "tag",
        "speaker",
        "author",
        "collection",
        "workspace",
    ]
    TEMPLATES = ["(todos)", "generic", "sermon", "podcast", "course"]
    EXPORT_MODES = ["(todos)", "raw", "clean", "ai_ready", "notebooklm", "study_mode"]
    DIFFICULTIES = ["(todos)", "básico", "intermediário", "avançado"]

    def __init__(
        self,
        master,
        settings,
        theme: ThemeManager,
        on_status: Optional[Callable[[str], None]] = None,
        on_show_related: Optional[Callable[[str, str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.settings = settings
        self.theme = theme
        self.on_status = on_status
        self.on_show_related = on_show_related
        self._search_engine = UnifiedSearchEngine()
        self._selected_hit_id: Optional[str] = None
        self._card_widgets: dict[str, ResultCard] = {}
        self._loading = False

        self.configure(fg_color="transparent")
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        self._build_dashboard_strip()
        self._build_left_column()
        self._build_detail_column()
        self._restore_preferences()
        self.refresh_dashboard()
        self.after(100, self._run_search)

    def _build_dashboard_strip(self) -> None:
        self.dashboard_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dashboard_frame.grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=Layout.LG, pady=(Layout.LG, Layout.SM)
        )
        colors = self.theme.colors()
        header = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(
            header,
            text="Workspace de Conhecimento",
            font=panel_title(),
            text_color=colors["text_primary"],
        ).pack(side="left")
        self.loading_label = ctk.CTkLabel(
            header,
            text="",
            font=caption(),
            text_color=colors["accent"],
        )
        self.loading_label.pack(side="right", padx=Layout.SM)

        self.stats_row = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        self.stats_row.pack(fill="x", pady=(Layout.SM, 0))

    def _build_left_column(self) -> None:
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(Layout.LG, Layout.SM), pady=(0, Layout.LG))
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        search_box = ctk.CTkFrame(left, **self.theme.frame_kwargs(elevated=True))
        search_box.grid(row=0, column=0, sticky="ew", pady=(0, Layout.SM))
        search_box.grid_columnconfigure(1, weight=1)

        colors = self.theme.colors()
        inner = ctk.CTkFrame(search_box, fg_color="transparent")
        inner.pack(fill="x", padx=Layout.SM, pady=Layout.SM)
        inner.grid_columnconfigure(1, weight=1)

        SectionHeader(
            inner,
            "Busca unificada",
            self.theme,
            subtitle="Documentos, tópicos, chunks, flashcards, quizzes e mais",
        ).grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, Layout.SM))

        ctk.CTkLabel(inner, text="Termo", font=body_small(), text_color=colors["text_secondary"]).grid(
            row=1, column=0, sticky="w", padx=(0, Layout.XS)
        )
        self.query_entry = ctk.CTkEntry(inner, placeholder_text="Pesquisar conhecimento…")
        self.query_entry.grid(row=1, column=1, sticky="ew", pady=Layout.XS)
        self.query_entry.bind("<Return>", lambda _e: self._run_search())
        ctk.CTkButton(
            inner,
            text="Buscar",
            width=72,
            command=self._run_search,
            **self.theme.accent_button_kwargs(),
        ).grid(row=1, column=2, padx=(Layout.SM, 0))

        filt = ctk.CTkFrame(inner, fg_color="transparent")
        filt.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(Layout.SM, 0))

        self.ws_var = ctk.StringVar(value="(todos)")
        self.col_var = ctk.StringVar(value="(todas)")
        self.type_var = ctk.StringVar(value="(todos)")
        self.template_var = ctk.StringVar(value="(todos)")
        self.mode_var = ctk.StringVar(value="(todos)")
        self.diff_var = ctk.StringVar(value="(todos)")

        self._filter_row(filt, "Workspace", self.ws_var, self._workspace_names(), 0)
        self._filter_row(filt, "Coleção", self.col_var, self._collection_names(), 1)
        self._filter_row(filt, "Tipo", self.type_var, self.NODE_TYPES, 2)
        self._filter_row(filt, "Template", self.template_var, self.TEMPLATES, 3)
        self._filter_row(filt, "Modo", self.mode_var, self.EXPORT_MODES, 4)
        self._filter_row(filt, "Dificuldade", self.diff_var, self.DIFFICULTIES, 5)

        self.results_label = ctk.CTkLabel(
            left,
            text="",
            font=caption(),
            text_color=colors["text_muted"],
            anchor="w",
        )
        self.results_label.grid(row=1, column=0, sticky="ew", pady=(0, Layout.XS))

        self.results_scroll = ctk.CTkScrollableFrame(
            left,
            label_text="Resultados",
            fg_color="transparent",
        )
        self.results_scroll.grid(row=2, column=0, sticky="nsew")

    def _filter_row(
        self,
        parent: ctk.CTkFrame,
        label: str,
        variable: ctk.StringVar,
        values: list[str],
        row: int,
    ) -> None:
        ctk.CTkLabel(parent, text=label, font=caption(), width=72).grid(
            row=row, column=0, sticky="w", pady=2
        )
        menu = ctk.CTkOptionMenu(
            parent,
            values=values,
            variable=variable,
            command=lambda _v: self._save_preferences(),
            width=120,
            **self.theme.option_menu_kwargs(),
        )
        menu.grid(row=row, column=1, sticky="w", padx=(0, Layout.SM), pady=2)

    def _build_detail_column(self) -> None:
        self.detail_panel = DocumentDetailPanel(
            self,
            self.theme,
            on_status=self.on_status,
            on_show_related=self.on_show_related,
        )
        self.detail_panel.grid(row=1, column=1, sticky="nsew", padx=(Layout.SM, Layout.LG), pady=(0, Layout.LG))

    def refresh_theme(self) -> None:
        self.refresh_dashboard()
        self._run_search()

    def refresh_dashboard(self) -> None:
        for w in self.stats_row.winfo_children():
            w.destroy()
        dash = compute_dashboard_stats(self.settings)
        for label, value, _key in dash.to_cards()[:8]:
            card = StatCard(self.stats_row, label, value, self.theme)
            card.pack(side="left", padx=(0, Layout.SM), fill="y")

    def refresh(self) -> None:
        self.refresh_dashboard()
        self._run_search()

    def _restore_preferences(self) -> None:
        self.query_entry.insert(0, self.settings.ui_last_search_query)
        self.ws_var.set(self.settings.ui_search_filter_workspace)
        self.col_var.set(self.settings.ui_search_filter_collection)
        self.type_var.set(self.settings.ui_search_filter_node_type)
        self.template_var.set(self.settings.ui_search_filter_template)
        self.mode_var.set(self.settings.ui_search_filter_export_mode)
        self.diff_var.set(self.settings.ui_search_filter_difficulty)

    def _save_preferences(self) -> None:
        self.settings.ui_last_search_query = self.query_entry.get().strip()
        self.settings.ui_search_filter_workspace = self.ws_var.get()
        self.settings.ui_search_filter_collection = self.col_var.get()
        self.settings.ui_search_filter_node_type = self.type_var.get()
        self.settings.ui_search_filter_template = self.template_var.get()
        self.settings.ui_search_filter_export_mode = self.mode_var.get()
        self.settings.ui_search_filter_difficulty = self.diff_var.get()

    def _workspace_names(self) -> list[str]:
        from src.library import get_library

        return ["(todos)"] + [n for _, n in get_library().workspaces.list_names()]

    def _collection_names(self) -> list[str]:
        from src.library import get_library

        return ["(todas)"] + get_library().collections.list_names()

    def _resolve_ws_id(self, name: str) -> str:
        if name == "(todos)":
            return ""
        from src.library import get_library

        for ws_id, ws_name in get_library().workspaces.list_names():
            if ws_name == name:
                return ws_id
        return ""

    def _resolve_col_id(self, name: str) -> str:
        if name == "(todas)":
            return ""
        from src.library import get_library

        col = get_library().collections.get_by_name(name)
        return str(col["id"]) if col else ""

    def _set_loading(self, active: bool) -> None:
        self._loading = active
        self.loading_label.configure(text="Buscando…" if active else "")

    def _run_search(self) -> None:
        if self._loading:
            return
        self._set_loading(True)
        self._save_preferences()
        query = self.query_entry.get().strip()
        try:
            result = self._search_engine.search(
                query,
                workspace_id=self._resolve_ws_id(self.ws_var.get()),
                collection_id=self._resolve_col_id(self.col_var.get()),
                node_type=self.type_var.get(),
                template=self.template_var.get(),
                export_mode=self.mode_var.get(),
                difficulty=self.diff_var.get(),
            )
            self._render_results(result.hits, result.total, query)
            if self.on_status:
                self.on_status(f"Busca: {result.total} resultado(s).")
        finally:
            self._set_loading(False)

    def _render_results(self, hits: list[UnifiedSearchHit], total: int, query: str) -> None:
        for w in self.results_scroll.winfo_children():
            w.destroy()
        self._card_widgets.clear()

        qdisp = f"«{query}»" if query else "(filtros)"
        self.results_label.configure(text=f"{total} resultado(s) para {qdisp}")

        if not hits:
            EmptyState(
                self.results_scroll,
                "Nenhum resultado encontrado.",
                self.theme,
                hint="Processe arquivos na fila ou ajuste os filtros.",
            ).pack(fill="x", pady=Layout.LG)
            return

        for hit in hits:
            self._add_card(hit)

    def _add_card(self, hit: UnifiedSearchHit) -> None:
        selected = self._selected_hit_id == hit.hit_id
        card = ResultCard(
            self.results_scroll,
            theme=self.theme,
            title=hit.title,
            result_type=hit.result_type,
            score=hit.score,
            match_reason=hit.match_reason,
            workspace=hit.workspace,
            collection=hit.collection,
            topics=hit.topics,
            selected=selected,
            on_select=lambda h=hit: self._select_hit(h),
            on_open=lambda h=hit: self._open_hit(h) if h.catalog_id else None,
            on_related=lambda h=hit: self._related_hit(h) if h.catalog_id else None,
        )
        card.pack(fill="x", pady=Layout.XS)
        self._card_widgets[hit.hit_id] = card

    def _select_hit(self, hit: UnifiedSearchHit) -> None:
        self._selected_hit_id = hit.hit_id
        colors = self.theme.colors()
        for hid, card in self._card_widgets.items():
            if hid == hit.hit_id:
                card.configure(
                    fg_color=colors["card_selected"],
                    border_width=1,
                    border_color=colors["primary"],
                )
            else:
                card.configure(fg_color=colors["card_bg"], border_width=0)

        if hit.catalog_id:
            self.detail_panel.show_catalog(hit.catalog_id)
        elif hit.result_type == "topic":
            from src.knowledge_graph import get_knowledge_graph

            nav = get_knowledge_graph().topics.explore(hit.title)
            self.detail_panel.show_empty(
                f"Tópico «{hit.title}»: {nav.get('total_connections', 0)} conexões. "
                "Use a aba Grafo para explorar."
            )
        else:
            self.detail_panel.show_empty(f"Selecionado: {hit.result_type} — {hit.title[:60]}")

    def _open_hit(self, hit: UnifiedSearchHit) -> None:
        if hit.catalog_id:
            self.detail_panel.show_catalog(hit.catalog_id)
            self.detail_panel._open_markdown()

    def _related_hit(self, hit: UnifiedSearchHit) -> None:
        if hit.catalog_id and self.on_show_related:
            self.on_show_related(hit.catalog_id, hit.title)

    def focus_catalog(self, catalog_id: str) -> None:
        """Abre detalhe de um documento (ex.: vindo da Biblioteca)."""
        self.detail_panel.show_catalog(catalog_id)
        self._selected_hit_id = catalog_id
