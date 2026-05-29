from __future__ import annotations

import os
import subprocess
import sys
from typing import Callable, Optional

import customtkinter as ctk

from src.knowledge_graph import get_knowledge_graph
from src.library import get_library
from src.library.search.search_engine import SearchResult
from src.ui.design.fonts import body_small, caption, panel_title
from src.ui.design.spacing import Layout
from src.ui.design.theme_manager import ThemeManager


class LibraryPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        settings,
        theme: ThemeManager,
        on_status: Optional[Callable[[str], None]] = None,
        on_show_related: Optional[Callable[[str, str], None]] = None,
        on_open_workspace: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.settings = settings
        self.theme = theme
        self.on_status = on_status
        self.on_show_related = on_show_related
        self.on_open_workspace = on_open_workspace
        self._library = get_library()
        self._graph = get_knowledge_graph()
        self._selected_id: Optional[str] = None
        self._selected_title: str = ""
        self._result_rows: dict[str, ctk.CTkFrame] = {}

        self._apply_frame_style()
        self._build_header()
        self._build_stats()
        self._build_filters()
        self._build_semantic_search()
        self._build_list()
        self._build_connected()
        self._build_topics()
        self._build_actions()
        self.refresh()

    def _apply_frame_style(self) -> None:
        self.configure(**self.theme.frame_kwargs(elevated=True))

    def refresh_theme(self) -> None:
        self._apply_frame_style()
        colors = self.theme.colors()
        self.stats_label.configure(text_color=colors["text_secondary"])
        self.topics_label.configure(text_color=colors["text_muted"])
        self.refresh()

    def _build_header(self) -> None:
        colors = self.theme.colors()
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=Layout.LG, pady=(Layout.LG, Layout.SM))

        ctk.CTkLabel(
            header,
            text="Biblioteca de Conhecimento",
            font=panel_title(),
            text_color=colors["text_primary"],
        ).pack(side="left")

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

    def _build_filters(self) -> None:
        colors = self.theme.colors()
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=Layout.LG, pady=(0, Layout.SM))
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row, text="Busca", font=body_small(), text_color=colors["text_secondary"]).grid(
            row=0, column=0, sticky="w", padx=(0, Layout.SM)
        )
        self.search_entry = ctk.CTkEntry(row, placeholder_text="título, tópico, tag, referência…")
        self.search_entry.grid(row=0, column=1, sticky="ew", pady=Layout.XS)
        self.search_entry.bind("<KeyRelease>", lambda _e: self.refresh())

        filt = ctk.CTkFrame(self, fg_color="transparent")
        filt.pack(fill="x", padx=Layout.LG, pady=(0, Layout.SM))

        ws_values = ["(todos)"] + [name for _, name in self._library.workspaces.list_names()]
        self.workspace_var = ctk.StringVar(value="(todos)")
        ctk.CTkLabel(filt, text="Workspace", font=body_small()).pack(side="left", padx=(0, Layout.XS))
        self.workspace_menu = ctk.CTkOptionMenu(
            filt,
            values=ws_values,
            variable=self.workspace_var,
            command=lambda _v: self.refresh(),
            width=160,
        )
        self.workspace_menu.pack(side="left", padx=(0, Layout.MD))

        col_values = ["(todas)"] + self._library.collections.list_names()
        self.collection_var = ctk.StringVar(value="(todas)")
        ctk.CTkLabel(filt, text="Coleção", font=body_small()).pack(side="left", padx=(0, Layout.XS))
        self.collection_menu = ctk.CTkOptionMenu(
            filt,
            values=col_values,
            variable=self.collection_var,
            command=lambda _v: self.refresh(),
            width=140,
        )
        self.collection_menu.pack(side="left")

    def _build_semantic_search(self) -> None:
        colors = self.theme.colors()
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=Layout.LG, pady=(0, Layout.SM))
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            row,
            text="Busca semântica",
            font=body_small(),
            text_color=colors["text_secondary"],
        ).grid(row=0, column=0, sticky="w", padx=(0, Layout.SM))
        self.semantic_entry = ctk.CTkEntry(
            row,
            placeholder_text="tópicos, referências, chunks, flashcards…",
        )
        self.semantic_entry.grid(row=0, column=1, sticky="ew")
        self.semantic_entry.bind("<Return>", lambda _e: self._run_semantic_search())
        ctk.CTkButton(
            row,
            text="Buscar",
            width=72,
            command=self._run_semantic_search,
            **self.theme.accent_button_kwargs(),
        ).grid(row=0, column=2, padx=(Layout.SM, 0))

    def _build_connected(self) -> None:
        self.connected_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.connected_frame.pack(fill="x", padx=Layout.LG, pady=(0, Layout.SM))

    def _build_list(self) -> None:
        self.scroll = ctk.CTkScrollableFrame(self, label_text="Documentos", fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=Layout.LG, pady=(0, Layout.SM))

    def _build_topics(self) -> None:
        colors = self.theme.colors()
        self.topics_label = ctk.CTkLabel(
            self,
            text="",
            font=caption(),
            text_color=colors["text_muted"],
            anchor="w",
            wraplength=700,
            justify="left",
        )
        self.topics_label.pack(fill="x", padx=Layout.LG, pady=(0, Layout.SM))

    def _build_actions(self) -> None:
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=Layout.LG, pady=(0, Layout.LG))

        ctk.CTkButton(
            actions,
            text="Abrir Markdown",
            width=140,
            command=self._open_selected,
            **self.theme.accent_button_kwargs(),
        ).pack(side="left", padx=(0, Layout.SM))

        ctk.CTkButton(
            actions,
            text="Ver relacionados",
            width=120,
            command=self._show_related,
            **self.theme.ghost_button_kwargs(),
        ).pack(side="left", padx=(0, Layout.SM))

        ctk.CTkButton(
            actions,
            text="No Workspace",
            width=110,
            command=self._open_in_workspace,
            **self.theme.ghost_button_kwargs(),
        ).pack(side="left", padx=(0, Layout.SM))

        ctk.CTkButton(
            actions,
            text="Atualizar",
            width=100,
            command=self.refresh,
            **self.theme.ghost_button_kwargs(),
        ).pack(side="left")

    def _workspace_filter_id(self) -> str:
        name = self.workspace_var.get()
        if name == "(todos)":
            return ""
        for ws_id, ws_name in self._library.workspaces.list_names():
            if ws_name == name:
                return ws_id
        return ""

    def _collection_filter_id(self) -> str:
        name = self.collection_var.get()
        if name == "(todas)":
            return ""
        col = self._library.collections.get_by_name(name)
        return str(col["id"]) if col else ""

    def refresh(self) -> None:
        self._library.collections.load()
        self._library.workspaces.load()
        self._library.catalog.load()
        self._graph.load()

        ws_values = ["(todos)"] + [name for _, name in self._library.workspaces.list_names()]
        self.workspace_menu.configure(values=ws_values)
        col_values = ["(todas)"] + self._library.collections.list_names()
        self.collection_menu.configure(values=col_values)

        stats = self._library.stats()
        self.stats_label.configure(text=stats.to_display())

        query = self.search_entry.get().strip()
        results = self._library.search_documents(
            query=query,
            workspace_id=self._workspace_filter_id(),
            collection_id=self._collection_filter_id(),
            sort_by="updated_at",
            sort_order="desc",
        )

        topics = self._library.search.list_topics(
            workspace_id=self._workspace_filter_id(),
            limit=12,
        )
        if topics:
            top_str = " · ".join(f"{t} ({n})" for t, n in topics[:8])
            self.topics_label.configure(text=f"Tópicos: {top_str}")
        else:
            self.topics_label.configure(text="Tópicos: —")

        for w in self.scroll.winfo_children():
            w.destroy()
        self._result_rows.clear()

        if not results:
            ctk.CTkLabel(
                self.scroll,
                text="Nenhum documento no catálogo. Processe arquivos na fila.",
                font=body_small(),
                text_color=self.theme.colors()["text_muted"],
            ).pack(anchor="w", pady=Layout.MD)
            return

        for result in results:
            self._add_row(result)

    def _add_row(self, result: SearchResult) -> None:
        entry = result.entry
        colors = self.theme.colors()
        selected = self._selected_id == entry.id

        row = ctk.CTkFrame(
            self.scroll,
            fg_color=colors["card_selected"] if selected else colors["card_bg"],
            corner_radius=Layout.CORNER_RADIUS_CARD,
            border_width=1 if selected else 0,
            border_color=colors["primary"] if selected else colors["border"],
        )
        row.pack(fill="x", pady=Layout.XS)
        self._result_rows[entry.id] = row

        meta = (
            f"{entry.workspace_name or '—'} · {entry.collection_name or '—'} · "
            f"{entry.pipeline_stage or entry.export_mode} · score {entry.semantic_score}"
        )
        if result.matched_fields:
            meta += f" · match: {', '.join(result.matched_fields)}"

        title_lbl = ctk.CTkLabel(
            row,
            text=entry.title[:64],
            font=body_small(),
            text_color=colors["text_primary"],
            anchor="w",
        )
        title_lbl.pack(fill="x", padx=Layout.SM, pady=(Layout.SM, 0))
        ctk.CTkLabel(
            row,
            text=meta,
            font=caption(),
            text_color=colors["text_muted"],
            anchor="w",
        ).pack(fill="x", padx=Layout.SM, pady=(0, Layout.SM))

        for widget in (row, title_lbl):
            widget.bind("<Button-1>", lambda _e, eid=entry.id: self._select(eid))

    def _select(self, catalog_id: str) -> None:
        self._selected_id = catalog_id
        entry = self._library.catalog.get(catalog_id)
        self._selected_title = entry.title if entry else catalog_id
        colors = self.theme.colors()
        for eid, row in self._result_rows.items():
            if eid == catalog_id:
                row.configure(fg_color=colors["card_selected"], border_width=1, border_color=colors["primary"])
            else:
                row.configure(fg_color=colors["card_bg"], border_width=0)

    def _run_semantic_search(self) -> None:
        query = self.semantic_entry.get().strip()
        if not query:
            return
        self._graph.load()
        result = self._graph.search.search(query, limit=12)
        self._render_connected_results(result.documents, result.chunks, result.topics)
        if self.on_status:
            self.on_status(f"Busca semântica: {result.total_hits} hit(s).")

    def _open_in_workspace(self) -> None:
        if not self._selected_id:
            if self.on_status:
                self.on_status("Selecione um documento na biblioteca.")
            return
        if self.on_open_workspace:
            self.on_open_workspace(self._selected_id)

    def _show_related(self) -> None:
        if not self._selected_id:
            if self.on_status:
                self.on_status("Selecione um documento na biblioteca.")
            return
        self._graph.load()
        related = self._graph.related.find_related(self._selected_id)
        items = [
            {
                "label": r.get("title", r.get("document_id", "")),
                "score": r.get("score", 0),
                "reasons": r.get("reasons", []),
            }
            for r in related
        ]
        self._render_connected_results(items, [], [])
        if self.on_show_related:
            self.on_show_related(self._selected_id, self._selected_title)

    def _render_connected_results(
        self,
        documents: list,
        chunks: list,
        topics: list,
    ) -> None:
        for w in self.connected_frame.winfo_children():
            w.destroy()
        colors = self.theme.colors()
        if not documents and not chunks and not topics:
            return
        ctk.CTkLabel(
            self.connected_frame,
            text="Resultados conectados",
            font=body_small(),
            text_color=colors["text_primary"],
        ).pack(anchor="w")
        for doc in documents[:8]:
            label = doc.get("label") or doc.get("title", "")
            score = doc.get("score", "")
            reasons = ", ".join(doc.get("reasons", []))
            line = f"· {label}"
            if score:
                line += f" ({score})"
            if reasons:
                line += f" — {reasons}"
            ctk.CTkLabel(
                self.connected_frame,
                text=line,
                font=caption(),
                text_color=colors["text_muted"],
                anchor="w",
                wraplength=680,
                justify="left",
            ).pack(anchor="w")
        for ch in chunks[:4]:
            ctk.CTkLabel(
                self.connected_frame,
                text=f"· chunk: {str(ch.get('label', ''))[:60]}",
                font=caption(),
                text_color=colors["text_muted"],
                anchor="w",
            ).pack(anchor="w")
        for tp in topics[:4]:
            ctk.CTkLabel(
                self.connected_frame,
                text=f"· tópico: {tp.get('label', '')}",
                font=caption(),
                text_color=colors["text_muted"],
                anchor="w",
            ).pack(anchor="w")

    def _open_selected(self) -> None:
        if not self._selected_id:
            if self.on_status:
                self.on_status("Selecione um documento na biblioteca.")
            return
        path = self._library.open_output_path(self._selected_id)
        if not path:
            if self.on_status:
                self.on_status("Arquivo de saída não encontrado.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
            if self.on_status:
                self.on_status(f"Abrindo: {os.path.basename(path)}")
        except OSError as exc:
            if self.on_status:
                self.on_status(f"Erro ao abrir arquivo: {exc}")
