"""Painel de detalhe de documento catalogado."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

import customtkinter as ctk

from src.knowledge_graph import get_knowledge_graph
from src.knowledge_graph.graph_engine import _load_study_sidecars
from src.library import get_library
from src.ui.components.knowledge_widgets import EmptyState, SectionHeader
from src.ui.design.fonts import body_small, caption
from src.ui.design.spacing import Layout
from src.ui.design.theme_manager import ThemeManager


class DocumentDetailPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        theme: ThemeManager,
        on_status: Optional[Callable[[str], None]] = None,
        on_show_related: Optional[Callable[[str, str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.theme = theme
        self.on_status = on_status
        self.on_show_related = on_show_related
        self._library = get_library()
        self._graph = get_knowledge_graph()
        self._catalog_id: Optional[str] = None

        self.configure(**self.theme.frame_kwargs(elevated=True))
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="Detalhe")
        self._scroll.pack(fill="both", expand=True, padx=Layout.SM, pady=Layout.SM)
        self.show_empty()

    def show_empty(self, message: str = "Selecione um resultado para ver detalhes.") -> None:
        self._catalog_id = None
        for w in self._scroll.winfo_children():
            w.destroy()
        EmptyState(
            self._scroll,
            message,
            self.theme,
            hint="Use a busca unificada ou clique em um card de documento.",
        ).pack(fill="both", expand=True, pady=Layout.XL)

    def show_catalog(self, catalog_id: str) -> None:
        self._library.catalog.load()
        self._graph.load()
        entry = self._library.catalog.get(catalog_id)
        if not entry:
            self.show_empty("Documento não encontrado no catálogo.")
            return

        self._catalog_id = catalog_id
        flashcards, quizzes = _load_study_sidecars(entry.output_path)
        related = self._graph.related.find_related(catalog_id, limit=8)

        for w in self._scroll.winfo_children():
            w.destroy()

        colors = self.theme.colors()
        SectionHeader(
            self._scroll,
            entry.title[:80],
            self.theme,
            subtitle=f"{entry.workspace_name} · {entry.collection_name}",
        ).pack(fill="x", pady=(0, Layout.SM))

        actions = ctk.CTkFrame(self._scroll, fg_color="transparent")
        actions.pack(fill="x", pady=(0, Layout.SM))
        ctk.CTkButton(
            actions,
            text="Abrir Markdown",
            width=120,
            command=self._open_markdown,
            **self.theme.accent_button_kwargs(),
        ).pack(side="left", padx=(0, Layout.XS))
        ctk.CTkButton(
            actions,
            text="Abrir pasta",
            width=90,
            command=self._open_folder,
            **self.theme.ghost_button_kwargs(),
        ).pack(side="left", padx=(0, Layout.XS))
        ctk.CTkButton(
            actions,
            text="Copiar caminho",
            width=100,
            command=self._copy_path,
            **self.theme.ghost_button_kwargs(),
        ).pack(side="left", padx=(0, Layout.XS))
        ctk.CTkButton(
            actions,
            text="Exportar resumo",
            width=110,
            command=lambda: self._export_summary(entry, flashcards, quizzes, related),
            **self.theme.ghost_button_kwargs(),
        ).pack(side="left")

        self._field_block("Caminho exportado", entry.output_path or "—")
        self._list_block("Tags", entry.tags)
        self._list_block("Tópicos", entry.topics)
        self._list_block("Referências", entry.references[:12])
        self._list_block("Highlights", [str(h)[:80] for h in entry.highlights[:8]])
        self._list_block("Chunks", [str(c.get("title", c.get("chunk_id", "")))[:60] for c in entry.chunks[:10] if isinstance(c, dict)])
        if flashcards:
            self._list_block(
                "Flashcards",
                [f"{fc.get('question', '')[:50]}…" for fc in flashcards[:6]],
            )
        if quizzes:
            self._list_block(
                "Quizzes",
                [str(q.get("question", ""))[:60] for q in quizzes[:6]],
            )

        if related:
            ctk.CTkLabel(
                self._scroll,
                text="Documentos relacionados",
                font=body_small(),
                text_color=colors["text_primary"],
                anchor="w",
            ).pack(fill="x", pady=(Layout.SM, Layout.XS))
            for rel in related:
                reasons = ", ".join(rel.get("reasons", []))
                line = f"· {rel.get('title', rel.get('document_id', ''))} ({rel.get('score', 0):.1f})"
                if reasons:
                    line += f" — {reasons}"
                lbl = ctk.CTkLabel(
                    self._scroll,
                    text=line,
                    font=caption(),
                    text_color=colors["text_muted"],
                    anchor="w",
                    wraplength=340,
                    cursor="hand2",
                )
                lbl.pack(fill="x")
                rid = rel.get("document_id", "")
                if rid:
                    lbl.bind(
                        "<Button-1>",
                        lambda _e, cid=rid: self.show_catalog(cid),
                    )
            ctk.CTkButton(
                self._scroll,
                text="Ver todos no Grafo",
                width=140,
                command=lambda: self.on_show_related and self.on_show_related(
                    catalog_id, entry.title
                ),
                **self.theme.ghost_button_kwargs(),
            ).pack(anchor="w", pady=Layout.SM)

        meta = (
            f"Pipeline: {entry.pipeline_stage or entry.export_mode} · "
            f"Template: {entry.template} · Score: {entry.semantic_score}"
        )
        ctk.CTkLabel(
            self._scroll,
            text=meta,
            font=caption(),
            text_color=colors["text_muted"],
            anchor="w",
        ).pack(fill="x", pady=Layout.SM)

    def _field_block(self, label: str, value: str) -> None:
        colors = self.theme.colors()
        ctk.CTkLabel(
            self._scroll,
            text=label,
            font=body_small(),
            text_color=colors["text_secondary"],
            anchor="w",
        ).pack(fill="x", pady=(Layout.XS, 0))
        ctk.CTkLabel(
            self._scroll,
            text=value[:200] if value else "—",
            font=caption(),
            text_color=colors["text_muted"],
            anchor="w",
            wraplength=340,
            justify="left",
        ).pack(fill="x")

    def _list_block(self, label: str, items: list) -> None:
        if not items:
            return
        colors = self.theme.colors()
        ctk.CTkLabel(
            self._scroll,
            text=label,
            font=body_small(),
            text_color=colors["text_secondary"],
            anchor="w",
        ).pack(fill="x", pady=(Layout.SM, Layout.XS))
        for item in items:
            ctk.CTkLabel(
                self._scroll,
                text=f"  · {item}",
                font=caption(),
                text_color=colors["text_muted"],
                anchor="w",
                wraplength=320,
            ).pack(fill="x")

    def _open_markdown(self) -> None:
        if not self._catalog_id:
            return
        path = self._library.open_output_path(self._catalog_id)
        if not path:
            self._status("Arquivo de saída não encontrado.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
            self._status(f"Abrindo: {os.path.basename(path)}")
        except OSError as exc:
            self._status(f"Erro: {exc}")

    def _open_folder(self) -> None:
        if not self._catalog_id:
            return
        path = self._library.open_output_path(self._catalog_id)
        if not path:
            self._status("Caminho não disponível.")
            return
        folder = os.path.dirname(os.path.abspath(path))
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", folder], check=False)
            else:
                subprocess.run(["xdg-open", folder], check=False)
            self._status("Pasta aberta.")
        except OSError as exc:
            self._status(f"Erro: {exc}")

    def _copy_path(self) -> None:
        if not self._catalog_id:
            return
        entry = self._library.catalog.get(self._catalog_id)
        if not entry or not entry.output_path:
            self._status("Sem caminho para copiar.")
            return
        try:
            self.winfo_toplevel().clipboard_clear()
            self.winfo_toplevel().clipboard_append(os.path.abspath(entry.output_path))
            self._status("Caminho copiado.")
        except Exception:
            self._status("Não foi possível copiar.")

    def _export_summary(self, entry, flashcards, quizzes, related) -> None:
        if not entry.output_path:
            self._status("Sem arquivo de saída.")
            return
        base = Path(entry.output_path).with_suffix("")
        out = Path(f"{base}_knowledge_summary.md")
        lines = [
            f"# {entry.title}",
            "",
            f"- Workspace: {entry.workspace_name}",
            f"- Coleção: {entry.collection_name}",
            f"- Tópicos: {', '.join(entry.topics)}",
            f"- Referências: {len(entry.references)}",
            f"- Chunks: {entry.chunk_count}",
            f"- Flashcards: {len(flashcards)}",
            f"- Quizzes: {len(quizzes)}",
            "",
            "## Relacionados",
            "",
        ]
        for rel in related:
            lines.append(f"- {rel.get('title', '')} ({rel.get('score', 0):.1f})")
        try:
            out.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self._status(f"Resumo: {out.name}")
        except OSError as exc:
            self._status(f"Erro ao exportar: {exc}")

    def _status(self, msg: str) -> None:
        if self.on_status:
            self.on_status(msg)
