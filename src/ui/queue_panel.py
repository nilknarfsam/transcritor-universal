from __future__ import annotations

import os
import subprocess
import sys
from typing import Callable, Optional

import customtkinter as ctk

from src.core.queue_manager import QueueManager, QueueStats
from src.models.transcription_job import JobStatus, TranscriptionJob


class QueuePanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        queue: QueueManager,
        on_selection_change: Optional[Callable[[Optional[TranscriptionJob]], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, corner_radius=12, **kwargs)
        self.queue = queue
        self.on_selection_change = on_selection_change
        self._row_widgets: dict[str, ctk.CTkFrame] = {}

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            header,
            text="Fila de transcrições",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left")

        self.drop_hint = ctk.CTkLabel(
            header,
            text="Arraste arquivos aqui",
            text_color="gray55",
            font=ctk.CTkFont(size=12),
        )
        self.drop_hint.pack(side="right", padx=8)

        self.stats_label = ctk.CTkLabel(
            self,
            text=self._stats_text(QueueStats(0, 0, 0, 0, 0, 0)),
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
        )
        self.stats_label.pack(fill="x", padx=16, pady=(0, 4))

        self.overall_progress = ctk.CTkProgressBar(self)
        self.overall_progress.set(0)
        self.overall_progress.pack(fill="x", padx=16, pady=(0, 8))

        cols = ctk.CTkFrame(self, fg_color=("gray85", "gray25"), corner_radius=8)
        cols.pack(fill="x", padx=16, pady=(0, 4))
        for i, (text, width) in enumerate(
            [("Arquivo", 180), ("Tipo", 70), ("Status", 90), ("Saída", 200)]
        ):
            ctk.CTkLabel(
                cols, text=text, width=width, anchor="w", font=ctk.CTkFont(weight="bold", size=11)
            ).grid(row=0, column=i, padx=6, pady=6, sticky="w")

        self.scroll = ctk.CTkScrollableFrame(self, label_text="")
        self.scroll.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(0, 8))

        self.btn_add = ctk.CTkButton(
            actions, text="Adicionar Arquivos", width=130, command=self._on_add_clicked
        )
        self.btn_add.pack(side="left", padx=(0, 6))

        self.btn_start = ctk.CTkButton(
            actions, text="Iniciar Fila", width=100, command=self._start_queue
        )
        self.btn_start.pack(side="left", padx=4)

        self.btn_cancel = ctk.CTkButton(
            actions,
            text="Cancelar Fila",
            width=110,
            fg_color="#8b4513",
            hover_color="#6b3410",
            command=self._cancel_queue,
            state="disabled",
        )
        self.btn_cancel.pack(side="left", padx=4)

        self.btn_open_folder = ctk.CTkButton(
            actions,
            text="Abrir pasta de saída",
            width=140,
            fg_color="transparent",
            border_width=1,
            command=self._open_output_folder,
        )
        self.btn_open_folder.pack(side="left", padx=4)

        actions2 = ctk.CTkFrame(self, fg_color="transparent")
        actions2.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkButton(
            actions2,
            text="Remover Selecionado",
            width=140,
            fg_color="transparent",
            border_width=1,
            command=self._remove_selected,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            actions2,
            text="Limpar Fila",
            width=110,
            fg_color="#8b2635",
            hover_color="#6b1c28",
            command=self._clear_queue,
        ).pack(side="left", padx=4)

        self._on_add_files: Optional[Callable[[], None]] = None
        self._on_status: Optional[Callable[[str], None]] = None
        self.update_progress(0.0, self.queue.stats)

    def set_add_files_handler(self, handler: Callable[[], None]) -> None:
        self._on_add_files = handler

    def set_status_handler(self, handler: Callable[[str], None]) -> None:
        self._on_status = handler

    @staticmethod
    def _stats_text(stats: QueueStats) -> str:
        return (
            f"Total: {stats.total}  |  Aguardando: {stats.waiting}  |  "
            f"Processando: {stats.processing}  |  Concluídos: {stats.completed}  |  "
            f"Erros: {stats.errors}"
            + (f"  |  Cancelados: {stats.cancelled}" if stats.cancelled else "")
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

    def refresh(self) -> None:
        for widget in self.scroll.winfo_children():
            widget.destroy()
        self._row_widgets.clear()

        for job in self.queue.jobs:
            self._create_row(job)

        self.update_progress(self.queue.get_overall_progress(), self.queue.stats)

    def _create_row(self, job: TranscriptionJob) -> None:
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(fill="x", pady=2)
        self._row_widgets[job.id] = row

        status_color = {
            JobStatus.WAITING: "gray55",
            JobStatus.PROCESSING: "#1a73e8",
            JobStatus.COMPLETED: "#2e7d32",
            JobStatus.ERROR: "#c62828",
            JobStatus.CANCELLED: "#e65100",
        }.get(job.status, "gray55")

        status_text = job.status.value
        if job.status == JobStatus.ERROR and job.error_code:
            status_text = f"{status_text}"

        out_display = job.output_path or "—"
        if len(out_display) > 42:
            out_display = "…" + out_display[-39:]

        values = [
            (job.file_name[:28] + "…" if len(job.file_name) > 29 else job.file_name, 180),
            (job.file_type, 70),
            (status_text, 90),
            (out_display, 200),
        ]

        for col, (text, width) in enumerate(values):
            lbl = ctk.CTkLabel(row, text=text, width=width, anchor="w", font=ctk.CTkFont(size=11))
            if col == 2:
                lbl.configure(text_color=status_color)
            lbl.grid(row=0, column=col, padx=6, pady=4, sticky="w")
            lbl.bind("<Button-1>", lambda e, jid=job.id: self._select(jid))

        row.bind("<Button-1>", lambda e, jid=job.id: self._select(jid))
        self._highlight_row(job.id)

    def _select(self, job_id: str) -> None:
        self.queue.select_job(job_id)
        self._highlight_all()
        if self.on_selection_change:
            self.on_selection_change(self.queue.selected_job)

    def _highlight_all(self) -> None:
        selected = self.queue.selected_job
        for jid, row in self._row_widgets.items():
            if selected and jid == selected.id:
                row.configure(fg_color=("gray78", "gray30"))
            else:
                row.configure(fg_color="transparent")

    def _highlight_row(self, job_id: str) -> None:
        selected = self.queue.selected_job
        if selected and selected.id == job_id:
            self._row_widgets[job_id].configure(fg_color=("gray78", "gray30"))

    def update_job(self, job: TranscriptionJob) -> None:
        self.refresh()
        if self.queue.selected_job and self.queue.selected_job.id == job.id:
            if self.on_selection_change:
                self.on_selection_change(job)
