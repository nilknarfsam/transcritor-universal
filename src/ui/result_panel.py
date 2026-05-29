from __future__ import annotations

import tkinter.filedialog as fd
from typing import Callable, Optional

import customtkinter as ctk

from src.core.export_service import ExportService
from src.core.settings_service import SettingsService
from src.models.transcription_job import JobStatus, TranscriptionJob
from src.semantic.semantic_engine import analyze_text
from src.ui.design.fonts import badge, body_small, caption, mono, panel_title
from src.ui.design.spacing import Layout
from src.ui.design.theme_manager import ThemeManager

PREVIEW_CHAR_LIMIT = 12_000


class ResultPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        theme: ThemeManager,
        settings: SettingsService,
        on_status: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.theme = theme
        self.settings = settings
        self.on_status = on_status
        self._export = ExportService()
        self._current_job: Optional[TranscriptionJob] = None
        self._current_text = ""
        self._preview_truncated = False
        self._semantic_summary: dict = {}

        self._apply_frame_style()
        self._build_content()

    def _apply_frame_style(self) -> None:
        self.configure(**self.theme.frame_kwargs(elevated=True))

    def refresh_theme(self) -> None:
        self._apply_frame_style()
        colors = self.theme.colors()
        self.meta_label.configure(text_color=colors["text_muted"])
        self.preview_info.configure(text_color=colors["text_muted"])
        self.semantic_label.configure(text_color=colors["text_secondary"])
        if self._semantic_summary.get("semantic_ready"):
            self.semantic_badge.configure(
                fg_color=colors["primary"],
                text_color="#FFFFFF",
            )

    def _build_content(self) -> None:
        colors = self.theme.colors()

        title_row = ctk.CTkFrame(self, fg_color="transparent")
        title_row.pack(fill="x", padx=Layout.LG, pady=(Layout.MD, Layout.SM))

        ctk.CTkLabel(
            title_row,
            text="Resultado",
            font=panel_title(),
            text_color=colors["text_primary"],
        ).pack(side="left")

        self.semantic_badge = ctk.CTkLabel(
            title_row,
            text="Semantic Ready",
            font=badge(),
            text_color="#FFFFFF",
            fg_color=colors["border"],
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.semantic_badge.pack(side="left", padx=(Layout.SM, 0))
        self.semantic_badge.pack_forget()

        self.study_badge = ctk.CTkLabel(
            title_row,
            text="Study Ready",
            font=badge(),
            text_color="#FFFFFF",
            fg_color=colors["border"],
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.study_badge.pack(side="left", padx=(Layout.XS, 0))
        self.study_badge.pack_forget()

        self.meta_label = ctk.CTkLabel(
            self,
            text="Selecione um item da fila para visualizar.",
            text_color=colors["text_muted"],
            font=body_small(),
            anchor="w",
            wraplength=360,
        )
        self.meta_label.pack(fill="x", padx=Layout.LG, pady=(0, Layout.XS))

        self.semantic_label = ctk.CTkLabel(
            self,
            text="",
            text_color=colors["text_secondary"],
            font=caption(),
            anchor="w",
            wraplength=360,
            justify="left",
        )
        self.semantic_label.pack(fill="x", padx=Layout.LG, pady=(0, Layout.SM))

        preview_bar = ctk.CTkFrame(self, fg_color="transparent")
        preview_bar.pack(fill="x", padx=Layout.LG, pady=(0, Layout.XS))

        self.preview_info = ctk.CTkLabel(
            preview_bar,
            text="",
            text_color=colors["text_muted"],
            font=caption(),
            anchor="w",
        )
        self.preview_info.pack(side="left", fill="x", expand=True)

        self.btn_load_full = ctk.CTkButton(
            preview_bar,
            text="Carregar texto completo",
            width=170,
            height=26,
            font=body_small(),
            command=self._load_full_text,
            **self.theme.ghost_button_kwargs(),
        )
        self.btn_load_full.pack(side="right")
        self.btn_load_full.pack_forget()

        self.text_box = ctk.CTkTextbox(
            self,
            height=160,
            font=mono(12),
            wrap="word",
            fg_color=colors["surface"],
            border_color=colors["border"],
            border_width=1,
        )
        self.text_box.pack(fill="both", expand=True, padx=Layout.LG, pady=(0, Layout.SM))
        self.text_box.insert("1.0", "O texto processado aparecerá aqui.")
        self.text_box.configure(state="disabled")

        export_row = ctk.CTkFrame(self, fg_color="transparent")
        export_row.pack(fill="x", padx=Layout.LG, pady=(0, Layout.MD))

        self.btn_txt = ctk.CTkButton(
            export_row,
            text="Exportar TXT",
            width=110,
            state="disabled",
            command=lambda: self.export_manual("txt"),
            **self.theme.ghost_button_kwargs(),
        )
        self.btn_txt.pack(side="left", padx=Layout.XS)

        self.btn_json = ctk.CTkButton(
            export_row,
            text="Exportar JSON",
            width=110,
            state="disabled",
            command=lambda: self.export_manual("json"),
            **self.theme.ghost_button_kwargs(),
        )
        self.btn_json.pack(side="left", padx=Layout.XS)

        self.btn_md = ctk.CTkButton(
            export_row,
            text="Exportar MD",
            width=110,
            state="disabled",
            command=lambda: self.export_manual("md"),
            **self.theme.primary_button_kwargs(),
        )
        self.btn_md.pack(side="left", padx=Layout.XS)

    def show_job(self, job: Optional[TranscriptionJob]) -> None:
        self._current_job = job
        self._preview_truncated = False
        self._semantic_summary = {}
        self.btn_load_full.pack_forget()
        self.preview_info.configure(text="")
        self.semantic_badge.pack_forget()
        self.study_badge.pack_forget()
        self.semantic_label.configure(text="")

        if not job:
            self._set_text_content(
                "O texto processado aparecerá aqui.",
                full_text="",
                meta="Selecione um item da fila para visualizar.",
            )
            self._set_export_enabled(False)
            return

        if job.status == JobStatus.PROCESSING:
            self._set_text_content(
                "Aguarde, processando…",
                full_text="",
                meta=f"Processando: {job.file_name}",
            )
            self._set_export_enabled(False)
            return

        if job.status == JobStatus.ERROR:
            detail = job.error_message or "Erro desconhecido."
            if job.error_code:
                detail = f"[{job.error_code}] {detail}"
            self._set_text_content(detail, full_text="", meta=f"Erro: {job.file_name}")
            self._set_export_enabled(False)
            return

        if job.status == JobStatus.CANCELLED:
            self._set_text_content(
                job.error_message or "Item cancelado.",
                full_text="",
                meta=f"Cancelado: {job.file_name}",
            )
            self._set_export_enabled(False)
            return

        if job.status == JobStatus.COMPLETED:
            meta = f"{job.file_name} — salvo em: {job.output_path or '—'}"
            self._update_semantic_preview(job)
            self._update_study_preview(job)
            self._set_text_content(job.result_text or "(vazio)", full_text=job.result_text, meta=meta)
            self._set_export_enabled(bool((job.result_text or "").strip()))
            return

        self._set_text_content(
            "Aguardando processamento na fila.",
            full_text="",
            meta=f"{job.file_name} — {job.status.value}",
        )
        self._set_export_enabled(False)

    def _update_study_preview(self, job: TranscriptionJob) -> None:
        sm = job.study_metadata or {}
        if not sm.get("study_ready"):
            self.study_badge.pack_forget()
            return
        from src.ui.design.colors import SEMANTIC

        colors = self.theme.colors()
        self.study_badge.configure(fg_color=SEMANTIC["success"])
        self.study_badge.pack(side="left", padx=(Layout.XS, 0))
        extra = (
            f"  ·  Study: {sm.get('flashcards_count', 0)} flashcards, "
            f"{sm.get('quizzes_count', 0)} quizzes, {sm.get('difficulty', '—')}"
        )
        current = self.semantic_label.cget("text")
        if extra.strip() not in (current or ""):
            self.semantic_label.configure(text=(current or "") + extra)

    def _update_semantic_preview(self, job: TranscriptionJob) -> None:
        text = job.result_text or ""
        if not text.strip():
            return

        if job.semantic_metadata.get("semantic_ready"):
            sm = job.semantic_metadata
            self._semantic_summary = dict(sm)
        else:
            analysis = analyze_text(text)
            self._semantic_summary = analysis.to_metadata()

        colors = self.theme.colors()
        refs = self._semantic_summary.get("reference_count", 0)
        hi = self._semantic_summary.get("highlight_count", 0)
        chunks = self._semantic_summary.get("chunk_count", 0)
        topics = self._semantic_summary.get("topics", [])
        if isinstance(topics, str):
            topics_list = [t.strip() for t in topics.split(",") if t.strip()]
        else:
            topics_list = list(topics)[:5]

        self.semantic_badge.configure(fg_color=colors["primary"])
        self.semantic_badge.pack(side="left", padx=(Layout.SM, 0))

        topic_text = ", ".join(topics_list) if topics_list else "—"
        self.semantic_label.configure(
            text=(
                f"Referências: {refs}  ·  Highlights: {hi}  ·  "
                f"Chunks: {chunks}  ·  Tópicos: {topic_text}"
            )
        )

    def _set_text_content(self, display_text: str, *, full_text: str, meta: str) -> None:
        self.meta_label.configure(text=meta)
        self._current_text = full_text if full_text != "" else display_text

        if len(display_text) > PREVIEW_CHAR_LIMIT:
            shown = display_text[:PREVIEW_CHAR_LIMIT]
            remaining = len(display_text) - PREVIEW_CHAR_LIMIT
            self._preview_truncated = True
            self._current_text = display_text
            display_text = (
                f"{shown}\n\n"
                f"… preview limitado ({remaining:,} caracteres ocultos). "
                f"Use «Carregar texto completo» ou exporte o arquivo."
            )
            self.preview_info.configure(
                text=f"Exibindo {PREVIEW_CHAR_LIMIT:,} de {len(self._current_text):,} caracteres"
            )
            self.btn_load_full.pack(side="right")
        else:
            self.preview_info.configure(
                text=f"{len(display_text):,} caracteres" if display_text.strip() else ""
            )

        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", display_text)
        self.text_box.configure(state="disabled")

    def _load_full_text(self) -> None:
        if not self._current_text:
            return
        self._preview_truncated = False
        self.btn_load_full.pack_forget()
        self.preview_info.configure(text=f"Texto completo: {len(self._current_text):,} caracteres")
        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", self._current_text)
        self.text_box.configure(state="disabled")
        self.text_box.see("1.0")

    def _set_export_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.btn_txt.configure(state=state)
        self.btn_json.configure(state=state)
        self.btn_md.configure(state=state)

    def export_manual(self, fmt: str) -> None:
        if not self._current_text.strip():
            return

        extensions = {
            "txt": [("Arquivo TXT", "*.txt")],
            "json": [("JSON", "*.json")],
            "md": [("Markdown", "*.md")],
        }
        default_ext = f".{fmt}"
        path = fd.asksaveasfilename(defaultextension=default_ext, filetypes=extensions.get(fmt, []))
        if path:
            source = self._current_job.file_path if self._current_job else path
            self._export.save(
                path,
                self._current_text,
                fmt,  # type: ignore[arg-type]
                source_path=source,
                export_mode=self.settings.export_mode,
                content_template=self.settings.content_template,
                language=self.settings.language,
                model=self.settings.whisper_model,
            )
            if self.on_status:
                self.on_status(f"Arquivo salvo: {path}")

    def export_via_shortcut(self) -> None:
        import tkinter.simpledialog as sd

        opcoes = {"1": "txt", "2": "json", "3": "md"}
        escolha = sd.askstring(
            "Exportar",
            "Escolha o formato:\n1 - TXT\n2 - JSON\n3 - Markdown",
            parent=self.winfo_toplevel(),
        )
        if escolha and escolha.strip() in opcoes:
            self.export_manual(opcoes[escolha.strip()])
