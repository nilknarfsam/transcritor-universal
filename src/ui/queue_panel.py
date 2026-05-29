from __future__ import annotations

import os
import subprocess
import sys
from typing import Callable, Optional

import customtkinter as ctk

from src.core.queue_manager import QueueManager, QueueStats
from src.models.transcription_job import JobStatus, TranscriptionJob
from src.ui.components.queue_widgets import (
    ACCEPTED_FORMATS_HINT,
    JobDetailsPanel,
    QueueEmptyState,
    StatusBadge,
    _elapsed_label,
)
from src.ui.design.fonts import body_small, caption, panel_title
from src.ui.design.spacing import Layout
from src.ui.design.theme_manager import ThemeManager

_TABLE_COLUMNS = (
    ("Arquivo", 3),
    ("Tipo", 0),
    ("Status", 0),
    ("Progresso", 0),
    ("Saída", 2),
    ("Tempo", 0),
)


class QueuePanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        queue: QueueManager,
        theme: ThemeManager,
        on_selection_change: Optional[Callable[[Optional[TranscriptionJob]], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.queue = queue
        self.theme = theme
        self.on_selection_change = on_selection_change
        self._row_widgets: dict[str, ctk.CTkFrame] = {}

        self._on_add_files: Optional[Callable[[], None]] = None
        self._on_add_folder: Optional[Callable[[], None]] = None
        self._on_status: Optional[Callable[[str], None]] = None
        self._queue_restored = False

        self._apply_frame_style()
        self._build_toolbar()
        self._build_stats()
        self._build_intel_row()
        self._build_queue_card()
        self._build_details()
        self._build_execution_actions()
        self._build_secondary_actions()
        self.update_progress(0.0, self.queue.stats)
        self.refresh()

    def _apply_frame_style(self) -> None:
        self.configure(**self.theme.frame_kwargs(elevated=True))

    def refresh_theme(self) -> None:
        self._apply_frame_style()
        colors = self.theme.colors()
        self.stats_label.configure(text_color=colors["text_secondary"])
        self.cache_badge.configure(text_color=colors["text_muted"])
        self.queue_badge.configure(text_color=colors["accent"])
        self.cache_stats_label.configure(text_color=colors["text_secondary"])
        self.table_header.configure(fg_color=colors["table_header"])
        self.queue_card.configure(
            fg_color=colors["surface_elevated"],
            border_color=colors["border"],
        )
        self.details_panel.refresh_theme()
        self.refresh()

    def set_queue_restored(self, restored: bool) -> None:
        self._queue_restored = restored
        colors = self.theme.colors()
        if restored:
            self.queue_badge.configure(text="Fila restaurada", text_color=colors["accent"])
        else:
            self.queue_badge.configure(text="")

    def refresh_cache_stats(self) -> None:
        stats = self.queue.cache_engine.stats()
        count = int(stats.get("item_count", 0))
        size_b = int(stats.get("disk_bytes", 0))
        self.cache_stats_label.configure(
            text=f"Cache {count} itens · {self._format_bytes(size_b)}"
        )

    @staticmethod
    def _format_bytes(n: int) -> str:
        if n < 1024:
            return f"{n} B"
        if n < 1024 * 1024:
            return f"{n / 1024:.1f} KB"
        return f"{n / (1024 * 1024):.1f} MB"

    def _update_cache_badge(self) -> None:
        job = self.queue.selected_job
        status = self.queue.last_cache_status
        if job and job.cache_status:
            status = job.cache_status
        if status == "hit":
            self.cache_badge.configure(text="Cache HIT", text_color=self.theme.status_color("cache_hit"))
        elif status == "miss":
            self.cache_badge.configure(text="Cache MISS", text_color=self.theme.status_color("cache_miss"))
        elif status == "partial":
            self.cache_badge.configure(text="Cache PARTIAL", text_color=self.theme.colors()["accent"])
        else:
            self.cache_badge.configure(text="Cache: —", text_color=self.theme.colors()["text_muted"])

    def _build_toolbar(self) -> None:
        colors = self.theme.colors()
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=Layout.LG, pady=(Layout.LG, Layout.SM))

        ctk.CTkLabel(
            toolbar,
            text="Fila de transcrição",
            font=panel_title(),
            text_color=colors["text_primary"],
        ).pack(side="left")

        btn_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_frame.pack(side="right")

        ctk.CTkButton(
            btn_frame,
            text="Adicionar arquivos",
            width=140,
            command=self._on_add_clicked,
            **self.theme.ghost_button_kwargs(),
        ).pack(side="left", padx=(0, Layout.XS))

        ctk.CTkButton(
            btn_frame,
            text="Adicionar pasta",
            width=120,
            command=self._on_add_folder_clicked,
            **self.theme.ghost_button_kwargs(),
        ).pack(side="left", padx=Layout.XS)

        ctk.CTkButton(
            btn_frame,
            text="Remover selecionado",
            width=140,
            command=self._remove_selected,
            **self.theme.ghost_button_kwargs(),
        ).pack(side="left", padx=Layout.XS)

        ctk.CTkButton(
            btn_frame,
            text="Limpar fila",
            width=100,
            command=self._clear_queue,
            **self.theme.danger_button_kwargs(),
        ).pack(side="left", padx=(Layout.XS, 0))

        self.drop_hint = ctk.CTkLabel(
            self,
            text=ACCEPTED_FORMATS_HINT,
            text_color=colors["text_muted"],
            font=caption(),
        )
        self.drop_hint.pack(fill="x", padx=Layout.LG, pady=(0, Layout.XS))

    def _build_stats(self) -> None:
        colors = self.theme.colors()
        self.stats_label = ctk.CTkLabel(
            self,
            text=self._stats_text(QueueStats(0, 0, 0, 0, 0, 0)),
            font=caption(),
            text_color=colors["text_secondary"],
            anchor="w",
            justify="left",
        )
        self.stats_label.pack(fill="x", padx=Layout.LG, pady=(0, Layout.XS))

        self.overall_progress = ctk.CTkProgressBar(
            self,
            progress_color=colors["primary"],
            height=10,
        )
        self.overall_progress.set(0)
        self.overall_progress.pack(fill="x", padx=Layout.LG, pady=(0, Layout.SM))

    def _build_intel_row(self) -> None:
        colors = self.theme.colors()
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=Layout.LG, pady=(0, Layout.SM))

        self.cache_badge = ctk.CTkLabel(
            row,
            text="Cache: —",
            font=caption(),
            text_color=colors["text_muted"],
            anchor="w",
        )
        self.cache_badge.pack(side="left", padx=(0, Layout.MD))

        self.queue_badge = ctk.CTkLabel(
            row,
            text="",
            font=caption(),
            text_color=colors["accent"],
            anchor="w",
        )
        self.queue_badge.pack(side="left", padx=(0, Layout.MD))

        self.cache_stats_label = ctk.CTkLabel(
            row,
            text="Cache 0 itens · 0 B",
            font=caption(),
            text_color=colors["text_secondary"],
            anchor="e",
        )
        self.cache_stats_label.pack(side="right")

    def _build_queue_card(self) -> None:
        colors = self.theme.colors()
        self.queue_card = ctk.CTkFrame(
            self,
            fg_color=colors["surface_elevated"],
            border_color=colors["border"],
            border_width=1,
            corner_radius=Layout.CORNER_RADIUS,
        )
        self.queue_card.pack(fill="both", expand=True, padx=Layout.LG, pady=(0, Layout.SM))

        self.table_header = ctk.CTkFrame(
            self.queue_card,
            fg_color=colors["table_header"],
            corner_radius=Layout.CORNER_RADIUS_SM,
        )
        self.table_header.pack(fill="x", padx=Layout.SM, pady=(Layout.SM, Layout.XS))
        self._configure_table_grid(self.table_header)

        for col, (text, weight) in enumerate(_TABLE_COLUMNS):
            ctk.CTkLabel(
                self.table_header,
                text=text,
                anchor="w",
                font=body_small(),
                text_color=colors["text_secondary"],
            ).grid(row=0, column=col, padx=Layout.SM, pady=Layout.SM, sticky="ew")

        self.list_container = ctk.CTkFrame(self.queue_card, fg_color="transparent")
        self.list_container.pack(fill="both", expand=True, padx=Layout.SM, pady=(0, Layout.SM))

        self.empty_state = QueueEmptyState(self.list_container, self.theme)
        self.scroll = ctk.CTkScrollableFrame(self.list_container, fg_color="transparent")

    def _configure_table_grid(self, frame: ctk.CTkFrame) -> None:
        for col, (_text, weight) in enumerate(_TABLE_COLUMNS):
            if weight > 0:
                frame.grid_columnconfigure(col, weight=weight)
            else:
                minsizes = {1: 52, 2: 92, 3: 76, 5: 56}
                frame.grid_columnconfigure(col, weight=0, minsize=minsizes.get(col, 64))

    def _build_details(self) -> None:
        self.details_panel = JobDetailsPanel(self, self.theme)
        self.details_panel.pack(fill="x", padx=Layout.LG, pady=(0, Layout.SM))

    def _build_execution_actions(self) -> None:
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=Layout.LG, pady=(0, Layout.SM))

        self.btn_start = ctk.CTkButton(
            actions,
            text="Iniciar transcrição",
            width=180,
            height=36,
            command=self._start_queue,
            **self.theme.primary_button_kwargs(),
        )
        self.btn_start.pack(side="left", padx=(0, Layout.MD))

        self.btn_cancel = ctk.CTkButton(
            actions,
            text="Cancelar",
            width=110,
            height=36,
            command=self._cancel_queue,
            state="disabled",
            **self.theme.warning_button_kwargs(),
        )
        self.btn_cancel.pack(side="left", padx=(0, Layout.SM))

        self.btn_open_folder = ctk.CTkButton(
            actions,
            text="Abrir pasta de saída",
            width=150,
            height=36,
            command=self._open_output_folder,
            **self.theme.ghost_button_kwargs(),
        )
        self.btn_open_folder.pack(side="left", padx=Layout.XS)

    def _build_secondary_actions(self) -> None:
        actions2 = ctk.CTkFrame(self, fg_color="transparent")
        actions2.pack(fill="x", padx=Layout.LG, pady=(0, Layout.LG))

        ctk.CTkButton(
            actions2,
            text="Restaurar última fila",
            width=150,
            command=self._restore_queue,
            **self.theme.ghost_button_kwargs(),
        ).pack(side="left", padx=(0, Layout.SM))

        ctk.CTkButton(
            actions2,
            text="Limpar cache",
            width=110,
            command=self._clear_cache,
            **self.theme.warning_button_kwargs(),
        ).pack(side="left", padx=Layout.XS)

    def set_add_files_handler(self, handler: Callable[[], None]) -> None:
        self._on_add_files = handler

    def set_add_folder_handler(self, handler: Callable[[], None]) -> None:
        self._on_add_folder = handler

    def set_status_handler(self, handler: Callable[[str], None]) -> None:
        self._on_status = handler

    @staticmethod
    def _stats_text(stats: QueueStats) -> str:
        return (
            f"Total: {stats.total}  ·  Aguardando: {stats.waiting}  ·  "
            f"Processando: {stats.processing}  ·  Concluídos: {stats.completed}  ·  "
            f"Erros: {stats.errors}"
            + (f"  ·  Cancelados: {stats.cancelled}" if stats.cancelled else "")
        )

    def update_progress(self, value: float, stats: QueueStats) -> None:
        self.overall_progress.set(max(0.0, min(1.0, value)))
        self.stats_label.configure(text=self._stats_text(stats))
        processing = self.queue.is_processing
        self.btn_start.configure(state="disabled" if processing else "normal")
        self.btn_cancel.configure(state="normal" if processing else "disabled")

    def _on_add_clicked(self) -> None:
        if self._on_add_files:
            self._on_add_files()

    def _on_add_folder_clicked(self) -> None:
        if self._on_add_folder:
            self._on_add_folder()

    def _start_queue(self) -> None:
        if not self.queue.start_queue():
            if self._on_status and self.queue.is_processing:
                self._on_status("A fila já está em processamento.")

    def _cancel_queue(self) -> None:
        self.queue.cancel_queue()

    def _open_output_folder(self) -> None:
        job = self.queue.selected_job
        folder = self.queue.resolve_output_folder_for_job(job)
        if not folder:
            if self._on_status:
                self._on_status("Nenhuma pasta de saída disponível.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", folder], check=False)
            else:
                subprocess.run(["xdg-open", folder], check=False)
            if self._on_status:
                self._on_status(f"Pasta aberta: {folder}")
        except OSError as exc:
            if self._on_status:
                self._on_status(f"Não foi possível abrir a pasta: {exc}")

    def _remove_selected(self) -> None:
        if self.queue.remove_selected():
            self.refresh()

    def _clear_queue(self) -> None:
        self.queue.clear_queue()
        self.refresh()

    def _restore_queue(self) -> None:
        if self.queue.is_processing:
            if self._on_status:
                self._on_status("Aguarde o fim do processamento para restaurar a fila.")
            return
        if self.queue.restore_last_queue():
            self.set_queue_restored(True)
            self.refresh()
            if self._on_status:
                self._on_status("Última fila restaurada.")
        elif self._on_status:
            self._on_status("Nenhuma fila salva para restaurar.")

    def _clear_cache(self) -> None:
        if self.queue.is_processing:
            if self._on_status:
                self._on_status("Aguarde o fim do processamento para limpar o cache.")
            return
        items, _ = self.queue.clear_cache()
        self.refresh_cache_stats()
        self._update_cache_badge()
        if self._on_status:
            self._on_status(f"Cache limpo ({items} entrada(s) removidas).")

    def refresh(self) -> None:
        for widget in self.scroll.winfo_children():
            widget.destroy()
        self._row_widgets.clear()

        has_jobs = bool(self.queue.jobs)
        if has_jobs:
            self.empty_state.pack_forget()
            self.scroll.pack(fill="both", expand=True)
            for job in self.queue.jobs:
                self._create_row(job)
        else:
            self.scroll.pack_forget()
            self.empty_state.pack(fill="both", expand=True)

        self.update_progress(self.queue.get_overall_progress(), self.queue.stats)
        self._update_cache_badge()
        self.refresh_cache_stats()
        self.details_panel.show_job(self.queue.selected_job)

    def _status_key(self, status: JobStatus) -> str:
        return {
            JobStatus.WAITING: "waiting",
            JobStatus.PROCESSING: "processing",
            JobStatus.COMPLETED: "completed",
            JobStatus.ERROR: "error",
            JobStatus.CANCELLED: "cancelled",
        }.get(status, "waiting")

    def _create_row(self, job: TranscriptionJob) -> None:
        colors = self.theme.colors()
        selected = self.queue.selected_job
        is_selected = selected is not None and selected.id == job.id

        row = ctk.CTkFrame(
            self.scroll,
            fg_color=colors["card_selected"] if is_selected else colors["card_bg"],
            border_color=colors["primary"] if is_selected else colors["border"],
            border_width=1 if is_selected else 0,
            corner_radius=Layout.CORNER_RADIUS_CARD,
        )
        row.pack(fill="x", pady=Layout.XS)
        self._row_widgets[job.id] = row
        self._configure_table_grid(row)

        name = job.file_name
        if len(name) > 36:
            name = name[:33] + "…"

        ctk.CTkLabel(
            row,
            text=name,
            anchor="w",
            font=body_small(),
            text_color=colors["text_primary"],
        ).grid(row=0, column=0, padx=Layout.SM, pady=Layout.SM, sticky="ew")

        ctk.CTkLabel(
            row,
            text=job.file_type,
            anchor="w",
            font=body_small(),
            text_color=colors["text_secondary"],
        ).grid(row=0, column=1, padx=Layout.XS, pady=Layout.SM, sticky="w")

        status_badge = StatusBadge(row, self._status_key(job.status), self.theme)
        status_badge.grid(row=0, column=2, padx=Layout.XS, pady=Layout.SM, sticky="w")

        progress_cell = ctk.CTkFrame(row, fg_color="transparent")
        progress_cell.grid(row=0, column=3, padx=Layout.XS, pady=Layout.SM, sticky="w")
        if job.status == JobStatus.PROCESSING:
            bar = ctk.CTkProgressBar(
                progress_cell,
                width=64,
                height=8,
                progress_color=colors["primary"],
            )
            bar.set(max(0.05, min(1.0, job.job_progress)))
            bar.pack()
        else:
            ctk.CTkLabel(
                progress_cell,
                text=f"{int(job.job_progress * 100)}%" if job.job_progress else "—",
                font=caption(),
                text_color=colors["text_muted"],
            ).pack()

        out_display = job.output_path or "—"
        if len(out_display) > 32:
            out_display = "…" + out_display[-29:]

        ctk.CTkLabel(
            row,
            text=out_display,
            anchor="w",
            font=body_small(),
            text_color=colors["text_muted"],
        ).grid(row=0, column=4, padx=Layout.XS, pady=Layout.SM, sticky="ew")

        ctk.CTkLabel(
            row,
            text=_elapsed_label(job),
            anchor="w",
            font=caption(),
            text_color=colors["text_muted"],
        ).grid(row=0, column=5, padx=Layout.SM, pady=Layout.SM, sticky="w")

        for widget in (row, status_badge, progress_cell):
            widget.bind("<Button-1>", lambda e, jid=job.id: self._select(jid))
        for child in row.winfo_children():
            if isinstance(child, ctk.CTkLabel):
                child.bind("<Button-1>", lambda e, jid=job.id: self._select(jid))

    def _select(self, job_id: str) -> None:
        self.queue.select_job(job_id)
        self._highlight_all()
        job = self.queue.selected_job
        self.details_panel.show_job(job)
        if self.on_selection_change:
            self.on_selection_change(job)

    def _highlight_all(self) -> None:
        colors = self.theme.colors()
        selected = self.queue.selected_job
        for jid, row in self._row_widgets.items():
            if selected and jid == selected.id:
                row.configure(
                    fg_color=colors["card_selected"],
                    border_width=1,
                    border_color=colors["primary"],
                )
            else:
                row.configure(fg_color=colors["card_bg"], border_width=0)

    def update_job(self, job: TranscriptionJob) -> None:
        self.refresh()
        self._update_cache_badge()
        if self.queue.selected_job and self.queue.selected_job.id == job.id:
            self.details_panel.show_job(job)
            if self.on_selection_change:
                self.on_selection_change(job)
