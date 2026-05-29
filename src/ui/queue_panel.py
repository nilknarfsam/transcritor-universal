"""Painel principal da fila de transcrição (UX 3.1)."""

from __future__ import annotations

import os
import subprocess
import sys
import traceback
from dataclasses import dataclass
from typing import Callable, Optional

import customtkinter as ctk

from src.core.log_service import get_logger
from src.core.queue_manager import QueueManager, QueueStats
from src.models.transcription_job import JobStatus, TranscriptionJob
from src.ui.components.queue_widgets import (
    ACCEPTED_FORMATS_HINT,
    JobDetailsPanel,
    QueueEmptyState,
    StatusBadge,
    _elapsed_label,
)
from src.ui.design.fonts import body_small, caption
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


@dataclass
class _QueueRowCells:
    """Referências mutáveis de uma linha da fila — evita refresh completo a cada notify."""

    frame: ctk.CTkFrame
    status_badge: StatusBadge
    progress_cell: ctk.CTkFrame
    output_label: ctk.CTkLabel
    time_label: ctk.CTkLabel


class QueuePanel(ctk.CTkFrame):
    """Lista de transcrição — foco principal da interface UX 3.1."""

    def __init__(
        self,
        master,
        queue: QueueManager,
        theme: ThemeManager,
        on_selection_change: Optional[Callable[[Optional[TranscriptionJob]], None]] = None,
        on_view_result: Optional[Callable[[Optional[TranscriptionJob]], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.queue = queue
        self.theme = theme
        self.on_selection_change = on_selection_change
        self.on_view_result = on_view_result
        self._row_widgets: dict[str, ctk.CTkFrame] = {}
        self._row_cells: dict[str, _QueueRowCells] = {}
        self._logger = get_logger()

        self._on_status: Optional[Callable[[str], None]] = None
        self._queue_restored = False

        self._build_queue_card()
        self._build_details()
        self._safe(self.refresh)

    def _safe(self, fn: Callable[[], None], *, context: str = "ui") -> None:
        try:
            fn()
        except Exception:
            self._logger.exception("Falha na atualização da fila (%s)", context)
            traceback.print_exc()

    def refresh_theme(self) -> None:
        def _do() -> None:
            colors = self.theme.colors()
            self.table_header.configure(fg_color=colors["table_header"])
            self.queue_card.configure(
                fg_color=colors["surface_elevated"],
                border_color=colors["border"],
            )
            self.drop_hint.configure(text_color=colors["text_muted"])
            self.details_panel.refresh_theme()
            self.btn_view_result.configure(**self.theme.ghost_button_kwargs())
            self.refresh()

        self._safe(_do, context="refresh_theme")

    def set_queue_restored(self, restored: bool) -> None:
        self._queue_restored = restored

    def set_status_handler(self, handler: Callable[[str], None]) -> None:
        self._on_status = handler

    def _build_queue_card(self) -> None:
        colors = self.theme.colors()

        self.drop_hint = ctk.CTkLabel(
            self,
            text=ACCEPTED_FORMATS_HINT,
            text_color=colors["text_muted"],
            font=caption(),
        )
        self.drop_hint.pack(fill="x", pady=(0, Layout.XS))

        self.queue_card = ctk.CTkFrame(
            self,
            fg_color=colors["surface_elevated"],
            border_color=colors["border"],
            border_width=1,
            corner_radius=Layout.CORNER_RADIUS,
        )
        self.queue_card.pack(fill="both", expand=True)

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
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", pady=(Layout.SM, 0))

        self.details_panel = JobDetailsPanel(bottom, self.theme)
        self.details_panel.pack(fill="x")

        actions = ctk.CTkFrame(bottom, fg_color="transparent")
        actions.pack(fill="x", pady=(Layout.XS, 0))

        self.btn_view_result = ctk.CTkButton(
            actions,
            text="Visualizar Resultado",
            width=160,
            height=30,
            command=self._view_result,
            state="disabled",
            **self.theme.ghost_button_kwargs(),
        )
        self.btn_view_result.pack(side="left")

    def update_progress(self, value: float, stats: QueueStats) -> None:
        self._safe(self._update_view_button, context="update_progress")

    def _update_view_button(self) -> None:
        if not self.winfo_exists():
            return
        job = self.queue.selected_job
        can_view = bool(
            job
            and job.status in (JobStatus.COMPLETED, JobStatus.ERROR, JobStatus.CANCELLED)
        )
        self.btn_view_result.configure(state="normal" if can_view else "disabled")

    def _view_result(self) -> None:
        job = self.queue.selected_job
        if self.on_view_result:
            self.on_view_result(job)

    def remove_selected(self) -> None:
        if self.queue.remove_selected():
            self.refresh()

    def clear_queue(self) -> None:
        self.queue.clear_queue()
        self.refresh()

    def start_queue(self) -> None:
        if not self.queue.start_queue():
            if self._on_status and self.queue.is_processing:
                self._on_status("A fila já está em processamento.")

    def cancel_queue(self) -> None:
        self.queue.cancel_queue()

    def open_output_folder(self) -> None:
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

    def restore_queue(self) -> None:
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

    def clear_cache(self) -> None:
        if self.queue.is_processing:
            if self._on_status:
                self._on_status("Aguarde o fim do processamento para limpar o cache.")
            return
        items, _ = self.queue.clear_cache()
        if self._on_status:
            self._on_status(f"Cache limpo ({items} entrada(s) removidas).")

    def refresh(self) -> None:
        def _do() -> None:
            if not self.winfo_exists():
                return
            for widget in self.scroll.winfo_children():
                widget.destroy()
            self._row_widgets.clear()
            self._row_cells.clear()

            has_jobs = bool(self.queue.jobs)
            if has_jobs:
                self.empty_state.pack_forget()
                self.scroll.pack(fill="both", expand=True)
                for job in self.queue.jobs:
                    self._create_row(job)
            else:
                self.scroll.pack_forget()
                self.empty_state.pack(fill="both", expand=True)

            self._update_view_button()
            self.details_panel.show_job(self.queue.selected_job)

        self._safe(_do, context="refresh")

    @staticmethod
    def _short_output(path: str) -> str:
        out_display = path or "—"
        if len(out_display) > 32:
            out_display = "…" + out_display[-29:]
        return out_display

    def _fill_progress_cell(self, cell: ctk.CTkFrame, job: TranscriptionJob) -> None:
        for widget in cell.winfo_children():
            widget.destroy()
        colors = self.theme.colors()
        if job.status == JobStatus.PROCESSING:
            bar = ctk.CTkProgressBar(
                cell,
                width=64,
                height=8,
                progress_color=colors["primary"],
            )
            bar.set(max(0.05, min(1.0, job.job_progress)))
            bar.pack()
        else:
            pct = f"{int(job.job_progress * 100)}%" if job.job_progress else "—"
            ctk.CTkLabel(
                cell,
                text=pct,
                font=caption(),
                text_color=colors["text_muted"],
            ).pack()

    def _apply_job_to_row(self, job: TranscriptionJob) -> None:
        cells = self._row_cells.get(job.id)
        if cells is None or not cells.frame.winfo_exists():
            return
        cells.status_badge.apply_status(self._status_key(job.status))
        self._fill_progress_cell(cells.progress_cell, job)
        cells.output_label.configure(text=self._short_output(job.output_path or "—"))
        cells.time_label.configure(text=_elapsed_label(job))
        self._highlight_all()

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
        self._fill_progress_cell(progress_cell, job)

        output_label = ctk.CTkLabel(
            row,
            text=self._short_output(job.output_path or "—"),
            anchor="w",
            font=body_small(),
            text_color=colors["text_muted"],
        )
        output_label.grid(row=0, column=4, padx=Layout.XS, pady=Layout.SM, sticky="ew")

        time_label = ctk.CTkLabel(
            row,
            text=_elapsed_label(job),
            anchor="w",
            font=caption(),
            text_color=colors["text_muted"],
        )
        time_label.grid(row=0, column=5, padx=Layout.SM, pady=Layout.SM, sticky="w")

        self._row_cells[job.id] = _QueueRowCells(
            frame=row,
            status_badge=status_badge,
            progress_cell=progress_cell,
            output_label=output_label,
            time_label=time_label,
        )

        for widget in (row, status_badge, progress_cell):
            widget.bind("<Button-1>", lambda e, jid=job.id: self._select(jid))
        for child in row.winfo_children():
            if isinstance(child, ctk.CTkLabel):
                child.bind("<Button-1>", lambda e, jid=job.id: self._select(jid))

    def _select(self, job_id: str) -> None:
        self._safe(lambda: self._select_impl(job_id), context="select")

    def _select_impl(self, job_id: str) -> None:
        self.queue.select_job(job_id)
        self._highlight_all()
        job = self.queue.selected_job
        self.details_panel.show_job(job)
        self._update_view_button()
        if self.on_selection_change:
            self.on_selection_change(job)

    def _highlight_all(self) -> None:
        colors = self.theme.colors()
        selected = self.queue.selected_job
        for jid, row in self._row_widgets.items():
            if not row.winfo_exists():
                continue
            if selected and jid == selected.id:
                row.configure(
                    fg_color=colors["card_selected"],
                    border_width=1,
                    border_color=colors["primary"],
                )
            else:
                row.configure(fg_color=colors["card_bg"], border_width=0)

    def update_job(self, job: TranscriptionJob) -> None:
        """Atualiza só a linha afetada + detalhes compactos (sem refresh completo)."""

        def _do() -> None:
            if not self.winfo_exists():
                return

            cells = self._row_cells.get(job.id)
            if cells is not None and cells.frame.winfo_exists():
                self._apply_job_to_row(job)
            elif len(self._row_cells) != len(self.queue.jobs):
                self.refresh()
            else:
                self.refresh()

            selected = self.queue.selected_job
            if selected and selected.id == job.id:
                self.details_panel.show_job(job)
            self._update_view_button()

        self._safe(_do, context=f"update_job:{job.file_name}")
