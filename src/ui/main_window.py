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
from src.ui.design.fonts import APP_NAME, APP_TAGLINE, APP_VERSION, badge, brand_subtitle, brand_title
from src.ui.design.spacing import Layout
from src.ui.design.theme_manager import ThemeManager
from src.ui.graph_panel import GraphPanel
from src.ui.knowledge_workspace_panel import KnowledgeWorkspacePanel
from src.ui.library_panel import LibraryPanel
from src.ui.study_panel import StudyPanel
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

        self.settings = SettingsService()
        self.theme = ThemeManager(self.settings.theme)
        self.theme.apply(self.settings.theme)

        self.root = TkinterDnD.Tk()
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("1140x740")
        self.root.minsize(920, 620)
        self._apply_root_background()

        self.queue_manager = QueueManager(
            self.settings,
            on_job_updated=self._on_job_updated_threadsafe,
            on_queue_idle=self._on_queue_idle_threadsafe,
            on_status_message=self._on_status_threadsafe,
            on_progress=self._on_progress_threadsafe,
            on_queue_recovered=self._on_queue_recovered_threadsafe,
        )

        self._build_layout()
        self._setup_dnd()
        self._setup_shortcuts()
        self._try_queue_recovery()

    def _apply_root_background(self) -> None:
        """TkinterDnD.Tk() usa bg nativo — fg_color é exclusivo do CTk."""
        self.root.configure(bg=self.theme.colors()["surface"])

    def _build_layout(self) -> None:
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)

        self.settings_panel = SettingsPanel(
            self.root,
            self.settings,
            self.theme,
            on_theme_change=self._on_theme_change,
            on_settings_change=self._on_settings_change,
            width=Layout.SIDEBAR_WIDTH,
        )
        self.settings_panel.grid(
            row=0, column=0, rowspan=3, sticky="nsew", padx=(Layout.LG, Layout.SM), pady=Layout.LG
        )

        self._build_header()

        center = ctk.CTkFrame(self.root, fg_color="transparent")
        center.grid(row=1, column=1, sticky="nsew", padx=(Layout.SM, Layout.LG), pady=(0, Layout.SM))
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(0, weight=1)
        center.grid_rowconfigure(1, weight=0)

        self.main_tabs = ctk.CTkTabview(center, fg_color="transparent")
        self.main_tabs.grid(row=0, column=0, sticky="nsew")
        self.main_tabs.add("Pipeline")
        self.main_tabs.add("Conhecimento")
        self.main_tabs.add("Biblioteca")
        self.main_tabs.add("Grafo / Conexões")
        self.main_tabs.add("Estudo")

        pipeline_tab = self.main_tabs.tab("Pipeline")
        pipeline_tab.grid_columnconfigure(0, weight=1)
        pipeline_tab.grid_rowconfigure(0, weight=1)

        self.queue_panel = QueuePanel(
            pipeline_tab,
            self.queue_manager,
            self.theme,
            on_selection_change=self._on_job_selected,
        )
        self.queue_panel.grid(row=0, column=0, sticky="nsew")
        self.queue_panel.set_add_files_handler(self.add_files_dialog)
        self.queue_panel.set_status_handler(self._set_status)

        knowledge_tab = self.main_tabs.tab("Conhecimento")
        knowledge_tab.grid_columnconfigure(0, weight=1)
        knowledge_tab.grid_rowconfigure(0, weight=1)

        self.workspace_panel = KnowledgeWorkspacePanel(
            knowledge_tab,
            self.settings,
            self.theme,
            on_status=self._set_status,
            on_show_related=self._on_library_show_related,
        )
        self.workspace_panel.grid(row=0, column=0, sticky="nsew")

        library_tab = self.main_tabs.tab("Biblioteca")
        library_tab.grid_columnconfigure(0, weight=1)
        library_tab.grid_rowconfigure(0, weight=1)

        self.graph_panel = GraphPanel(
            self.main_tabs.tab("Grafo / Conexões"),
            self.theme,
            on_status=self._set_status,
        )
        self.graph_panel.grid(row=0, column=0, sticky="nsew")
        graph_tab = self.main_tabs.tab("Grafo / Conexões")
        graph_tab.grid_columnconfigure(0, weight=1)
        graph_tab.grid_rowconfigure(0, weight=1)

        self.library_panel = LibraryPanel(
            library_tab,
            self.settings,
            self.theme,
            on_status=self._set_status,
            on_show_related=self._on_library_show_related,
            on_open_workspace=self._on_open_in_workspace,
        )
        self.library_panel.grid(row=0, column=0, sticky="nsew")

        self._wrap_tab_persistence()
        self._restore_last_tab()

        study_tab = self.main_tabs.tab("Estudo")
        study_tab.grid_columnconfigure(0, weight=1)
        study_tab.grid_rowconfigure(0, weight=1)

        self.study_panel = StudyPanel(
            study_tab,
            self.theme,
            on_status=self._set_status,
        )
        self.study_panel.grid(row=0, column=0, sticky="nsew")

        self.status_label = ctk.CTkLabel(
            center,
            text="Pronto.",
            font=brand_subtitle(),
            text_color=self.theme.colors()["accent"],
            anchor="w",
        )
        self.status_label.grid(row=1, column=0, sticky="ew", pady=(Layout.SM, 0))

        self.result_panel = ResultPanel(self.root, self.theme, self.settings, on_status=self._set_status)
        self.result_panel.grid(
            row=2, column=1, sticky="nsew", padx=(Layout.SM, Layout.LG), pady=(0, Layout.LG)
        )

    def _build_header(self) -> None:
        colors = self.theme.colors()
        header = ctk.CTkFrame(
            self.root,
            fg_color=colors["header_bg"],
            border_color=colors["border"],
            border_width=1,
            corner_radius=Layout.CORNER_RADIUS,
            height=Layout.HEADER_HEIGHT,
        )
        header.grid(row=0, column=1, sticky="ew", padx=(Layout.SM, Layout.LG), pady=(Layout.LG, Layout.SM))
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(fill="x", padx=Layout.LG, pady=(Layout.MD, 0))

        ctk.CTkLabel(
            title_row,
            text=APP_NAME.upper(),
            font=brand_title(),
            text_color=colors["text_primary"],
        ).pack(side="left")

        ctk.CTkLabel(
            title_row,
            text=f"v{APP_VERSION}",
            font=badge(),
            text_color=colors["text_muted"],
            fg_color=colors["surface"],
            corner_radius=6,
            padx=8,
            pady=2,
        ).pack(side="left", padx=(Layout.SM, 0))

        ctk.CTkLabel(
            header,
            text=APP_TAGLINE,
            font=brand_subtitle(),
            text_color=colors["text_secondary"],
            anchor="w",
        ).pack(fill="x", padx=Layout.LG, pady=(Layout.XS, Layout.MD))

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
            fd.askopenfilenames(title="Escolha arquivos para processar", filetypes=FILE_DIALOG_TYPES)
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
        self.study_panel.show_job(job)

    def _on_settings_change(self) -> None:
        for job in self.queue_manager.jobs:
            if job.status == JobStatus.WAITING:
                from src.core.export_service import ExportService

                output_dir = self.settings.resolve_output_dir(job.file_path)
                fmt = self.settings.default_export_format  # type: ignore[arg-type]
                job.output_path = ExportService.build_output_path(job.file_path, output_dir, fmt)
        self.queue_panel.refresh()

    def _on_theme_change(self, theme: str) -> None:
        self.theme.apply(theme)
        colors = self.theme.colors()
        self._apply_root_background()
        self.status_label.configure(text_color=colors["accent"])
        self.settings_panel.refresh_theme()
        self.queue_panel.refresh_theme()
        self.workspace_panel.refresh_theme()
        self.library_panel.refresh_theme()
        self.graph_panel.refresh_theme()
        self.study_panel.refresh_theme()
        self.result_panel.refresh_theme()
        self._set_status(f"Tema alterado para {theme}")

    def _on_job_updated_threadsafe(self, job: TranscriptionJob) -> None:
        self.root.after(0, lambda j=job: self._on_job_updated(j))

    def _on_queue_idle_threadsafe(self) -> None:
        self.root.after(0, self._on_queue_idle)

    def _on_status_threadsafe(self, message: str) -> None:
        self.root.after(0, lambda m=message: self._set_status(m))

    def _on_progress_threadsafe(self, value: float, stats: QueueStats) -> None:
        self.root.after(0, lambda v=value, s=stats: self.queue_panel.update_progress(v, s))

    def _on_queue_recovered_threadsafe(self, meta: dict) -> None:
        self.root.after(0, lambda m=meta: self._on_queue_recovered(m))

    def _try_queue_recovery(self) -> None:
        if self.queue_manager.try_recover_queue(auto=True):
            self.queue_panel.refresh()
            self.queue_panel.set_queue_restored(True)
            pending = sum(
                1 for j in self.queue_manager.jobs
                if j.status in (JobStatus.WAITING, JobStatus.ERROR)
            )
            reset = meta.get("processing_reset", 0) if (meta := self.queue_manager.recovery_meta) else 0
            msg = f"Fila restaurada ({len(self.queue_manager.jobs)} item(ns))."
            if reset:
                msg += f" {reset} em processamento voltaram a aguardar."
            if pending:
                msg += " Clique em Iniciar Fila para continuar."
            self._set_status(msg)
            if self.queue_manager.jobs:
                self.queue_manager.select_job(self.queue_manager.jobs[0].id)
                self._on_job_selected(self.queue_manager.selected_job)
        self.queue_panel.refresh_cache_stats()

    def _on_queue_recovered(self, meta: dict) -> None:
        self.queue_panel.set_queue_restored(bool(meta.get("restored")))
        self.queue_panel.refresh()
        self.queue_panel.refresh_cache_stats()

    def _on_job_updated(self, job: TranscriptionJob) -> None:
        self.queue_panel.update_job(job)
        selected = self.queue_manager.selected_job
        if selected and selected.id == job.id:
            self.result_panel.show_job(job)
            self.study_panel.show_job(job)
        if job.status == JobStatus.COMPLETED:
            self.settings_panel.refresh_history()
            self.library_panel.refresh()
            self.workspace_panel.refresh()
            self.graph_panel.refresh()

    def _on_queue_idle(self) -> None:
        self.queue_panel.update_progress(
            self.queue_manager.get_overall_progress(),
            self.queue_manager.stats,
        )
        self.settings_panel.refresh_history()
        self.library_panel.refresh()
        self.workspace_panel.refresh()
        self.graph_panel.refresh()

    def _wrap_tab_persistence(self) -> None:
        seg = self.main_tabs._segmented_button
        previous = seg.cget("command")

        def on_tab(value: str) -> None:
            if previous:
                previous(value)
            try:
                self.settings.ui_last_tab = self.main_tabs.get()
            except Exception:
                pass

        seg.configure(command=on_tab)

    def _restore_last_tab(self) -> None:
        tab = self.settings.ui_last_tab
        valid = ("Pipeline", "Conhecimento", "Biblioteca", "Grafo / Conexões", "Estudo")
        if tab in valid:
            try:
                self.main_tabs.set(tab)
            except ValueError:
                pass

    def _on_open_in_workspace(self, catalog_id: str) -> None:
        self.main_tabs.set("Conhecimento")
        self.workspace_panel.focus_catalog(catalog_id)
        self._set_status("Documento aberto no workspace.")

    def _on_library_show_related(self, catalog_id: str, title: str) -> None:
        self.main_tabs.set("Grafo / Conexões")
        self.graph_panel.show_related(catalog_id, title)

    def _set_status(self, message: str) -> None:
        self.status_label.configure(text=message)

    def run(self) -> None:
        self.root.mainloop()


def run_app() -> None:
    MainWindow().run()
