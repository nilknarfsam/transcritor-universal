from __future__ import annotations

import tkinter.filedialog as fd
import tkinter.messagebox as mb

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from src.core.file_utils import FILE_DIALOG_TYPES, parse_dropped_paths
from src.core.log_service import setup_logging
from src.core.queue_manager import QueueManager, QueueStats
from src.core.settings_service import SettingsService
from src.core.transcription_service import TranscriptionService
from src.models.transcription_job import JobStatus, TranscriptionJob
from src.ui.queue_panel import QueuePanel
from src.ui.result_panel import ResultPanel
from src.ui.settings_panel import SettingsPanel


class MainWindow:
    def __init__(self) -> None:
        setup_logging()
        try:
            TranscriptionService().ensure_whisper()
        except RuntimeError as exc:
            mb.showerror("Erro", str(exc))
            raise SystemExit(1) from exc

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.settings = SettingsService()
        ctk.set_appearance_mode(self.settings.theme)

        self.root = TkinterDnD.Tk()
        self.root.title("Transcritor Universal 2.1")
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)

        self.queue_manager = QueueManager(
            self.settings,
            on_job_updated=self._on_job_updated_threadsafe,
            on_queue_idle=self._on_queue_idle_threadsafe,
            on_status_message=self._on_status_threadsafe,
            on_progress=self._on_progress_threadsafe,
        )

        self._build_layout()
        self._setup_dnd()
        self._setup_shortcuts()

    def _build_layout(self) -> None:
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)

        self.settings_panel = SettingsPanel(
            self.root,
            self.settings,
            on_theme_change=self._on_theme_change,
            on_settings_change=self._on_settings_change,
            width=260,
        )
        self.settings_panel.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(12, 6), pady=12)

        center = ctk.CTkFrame(self.root, fg_color="transparent")
        center.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=(12, 6))
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            center,
            text="TRANSCRITOR UNIVERSAL",
            font=ctk.CTkFont(family="Arial", size=22, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.queue_panel = QueuePanel(
            center,
            self.queue_manager,
            on_selection_change=self._on_job_selected,
        )
        self.queue_panel.grid(row=1, column=0, sticky="nsew")
        self.queue_panel.set_add_files_handler(self.add_files_dialog)
        self.queue_panel.set_status_handler(self._set_status)

        self.result_panel = ResultPanel(self.root, on_status=self._set_status)
        self.result_panel.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12))

        self.status_label = ctk.CTkLabel(
            center,
            text="Pronto.",
            font=ctk.CTkFont(size=11),
            text_color="#1a73e8",
            anchor="w",
        )
        self.status_label.grid(row=2, column=0, sticky="ew", pady=(8, 0))

    def _setup_dnd(self) -> None:
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self._drop_event)
        try:
            self.queue_panel.drop_target_register(DND_FILES)
            self.queue_panel.dnd_bind("<<Drop>>", self._drop_event)
        except Exception:
            pass

    def _setup_shortcuts(self) -> None:
        self.root.bind_all("<Control-o>", lambda _e: self.add_files_dialog())
        self.root.bind_all("<Control-t>", lambda _e: self.queue_manager.start_queue())
        self.root.bind_all("<Control-e>", lambda _e: self.result_panel.export_via_shortcut())
        self.root.bind_all("<Control-q>", lambda _e: self.root.destroy())

    def _drop_event(self, event) -> None:
        paths = parse_dropped_paths(event.data)
        if paths:
            self._add_paths(paths)
            self.queue_panel.drop_hint.configure(text=f"{len(paths)} arquivo(s) adicionado(s)")
        else:
            self._set_status("Arquivo não encontrado no drag & drop.")

    def add_files_dialog(self) -> None:
        paths = list(
            fd.askopenfilenames(title="Escolha arquivos para transcrever", filetypes=FILE_DIALOG_TYPES)
        )
        if paths:
            self._add_paths(list(paths))

    def _add_paths(self, paths: list[str]) -> None:
        added = self.queue_manager.add_files(paths)
        self.queue_panel.refresh()
        if added:
            self._set_status(f"{len(added)} arquivo(s) na fila.")
            self.queue_manager.select_job(added[-1].id)
            self._on_job_selected(self.queue_manager.selected_job)

    def _on_job_selected(self, job: TranscriptionJob | None) -> None:
        self.result_panel.show_job(job)

    def _on_settings_change(self) -> None:
        for job in self.queue_manager.jobs:
            if job.status == JobStatus.WAITING:
                from src.core.export_service import ExportService

                output_dir = self.settings.resolve_output_dir(job.file_path)
                fmt = self.settings.default_export_format  # type: ignore[arg-type]
                job.output_path = ExportService.build_output_path(job.file_path, output_dir, fmt)
        self.queue_panel.refresh()

    def _on_theme_change(self, theme: str) -> None:
        ctk.set_appearance_mode(theme)
        self._set_status(f"Tema alterado para {theme}")

    def _on_job_updated_threadsafe(self, job: TranscriptionJob) -> None:
        self.root.after(0, lambda j=job: self._on_job_updated(j))

    def _on_queue_idle_threadsafe(self) -> None:
        self.root.after(0, self._on_queue_idle)

    def _on_status_threadsafe(self, message: str) -> None:
        self.root.after(0, lambda m=message: self._set_status(m))

    def _on_progress_threadsafe(self, value: float, stats: QueueStats) -> None:
        self.root.after(0, lambda v=value, s=stats: self.queue_panel.update_progress(v, s))

    def _on_job_updated(self, job: TranscriptionJob) -> None:
        self.queue_panel.update_job(job)
        selected = self.queue_manager.selected_job
        if selected and selected.id == job.id:
            self.result_panel.show_job(job)
        if job.status == JobStatus.COMPLETED:
            self.settings_panel.refresh_history()

    def _on_queue_idle(self) -> None:
        self.queue_panel.update_progress(
            self.queue_manager.get_overall_progress(),
            self.queue_manager.stats,
        )
        self.settings_panel.refresh_history()

    def _set_status(self, message: str) -> None:
        self.status_label.configure(text=message)

    def run(self) -> None:
        self.root.mainloop()


def run_app() -> None:
    MainWindow().run()
