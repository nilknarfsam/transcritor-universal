"""Janela principal CortexFlow — toolbar, fila e callbacks thread-safe."""

from __future__ import annotations

import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import traceback
from pathlib import Path
from typing import Callable

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from src.core.file_utils import FILE_DIALOG_TYPES, collect_supported_files, parse_dropped_paths
from src.core.log_service import get_logger, setup_logging
from src.core.queue_manager import QueueManager, QueueStats
from src.core.settings_service import SettingsService
from src.core.transcription_service import TranscriptionService
from src.models.transcription_job import JobStatus, TranscriptionJob
from src.ui.design.fonts import APP_NAME, APP_VERSION, caption
from src.ui.design.spacing import Layout
from src.ui.design.theme_manager import ThemeManager
from src.ui.queue_panel import QueuePanel
from src.ui.result_window import ResultViewerWindow
from src.ui.settings_modal import SettingsModal


class MainWindow:
    """Shell da aplicação: fila em foco, configurações em modal, worker em thread separada."""

    def __init__(self) -> None:
        setup_logging()
        self._logger = get_logger()
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
        self.root.geometry("1280x740")
        self.root.minsize(1000, 620)
        self._window_icon: tk.PhotoImage | None = None
        self._apply_root_background()
        self._apply_window_icon()

        self.queue_manager = QueueManager(
            self.settings,
            on_job_updated=self._on_job_updated_threadsafe,
            on_queue_idle=self._on_queue_idle_threadsafe,
            on_status_message=self._on_status_threadsafe,
            on_progress=self._on_progress_threadsafe,
            on_queue_recovered=self._on_queue_recovered_threadsafe,
        )

        self._last_status_message = "Pronto."
        self.status_label = None
        self.btn_start = None
        self.btn_cancel = None

        self.result_viewer = ResultViewerWindow.get(
            self.root,
            self.theme,
            self.settings,
            on_status=self._set_status,
        )

        self._build_layout()
        self._setup_dnd()
        self._setup_shortcuts()

        self.settings_modal = SettingsModal(
            self.root,
            self.settings,
            self.theme,
            on_theme_change=self._on_theme_change,
            on_settings_change=self._on_settings_change,
            on_restore_queue=lambda: self._queue_maintenance(self.queue_panel.restore_queue),
            on_clear_cache=lambda: self._queue_maintenance(self.queue_panel.clear_cache),
        )

        self._try_queue_recovery()

    def _apply_root_background(self) -> None:
        """TkinterDnD.Tk() usa bg nativo — fg_color é exclusivo do CTk."""
        self.root.configure(bg=self.theme.colors()["surface"])

    def _resolve_asset_path(self, name: str) -> Path | None:
        import sys

        candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
            candidates.extend(
                [
                    base / "assets" / name,
                    Path(sys.executable).resolve().parent / "assets" / name,
                    Path(sys.executable).resolve().parent / "_internal" / "assets" / name,
                ]
            )
        else:
            candidates.append(Path(__file__).resolve().parents[2] / "assets" / name)
        for path in candidates:
            if path.is_file():
                return path
        return None

    def _apply_window_icon(self) -> None:
        icon_path = self._resolve_asset_path("icon.png")
        if not icon_path:
            return
        try:
            self._window_icon = tk.PhotoImage(file=str(icon_path))
            self.root.iconphoto(True, self._window_icon)
        except tk.TclError as exc:
            self._logger.warning("Não foi possível carregar ícone da janela: %s", exc)

    def _build_layout(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        self._build_toolbar()
        self._build_main_area()
        self._build_status_bar()
        self._set_status(self._last_status_message)

    def _build_toolbar(self) -> None:
        colors = self.theme.colors()
        toolbar = ctk.CTkFrame(
            self.root,
            fg_color=colors["header_bg"],
            border_color=colors["border"],
            border_width=1,
            corner_radius=Layout.CORNER_RADIUS,
        )
        toolbar.grid(row=0, column=0, sticky="ew", padx=Layout.LG, pady=(Layout.LG, Layout.SM))
        toolbar.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(toolbar, fg_color="transparent")
        inner.pack(fill="x", padx=Layout.MD, pady=Layout.SM)

        ghost = self.theme.ghost_button_kwargs()
        primary = self.theme.primary_button_kwargs()
        danger = self.theme.danger_button_kwargs()
        warning = self.theme.warning_button_kwargs()

        ctk.CTkButton(
            inner, text="Adicionar Arquivos", width=130, command=self.add_files_dialog, **ghost
        ).pack(side="left", padx=(0, Layout.XS))

        ctk.CTkButton(
            inner, text="Adicionar Pasta", width=120, command=self.add_folder_dialog, **ghost
        ).pack(side="left", padx=Layout.XS)

        ctk.CTkButton(
            inner,
            text="Remover",
            width=90,
            command=lambda: self.queue_panel.remove_selected(),
            **ghost,
        ).pack(side="left", padx=Layout.XS)

        ctk.CTkButton(
            inner,
            text="Limpar Fila",
            width=100,
            command=lambda: self.queue_panel.clear_queue(),
            **danger,
        ).pack(side="left", padx=Layout.XS)

        self.btn_start = ctk.CTkButton(
            inner,
            text="▶ INICIAR TRANSCRIÇÃO",
            width=200,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.queue_panel.start_queue(),
            **primary,
        )
        self.btn_start.pack(side="left", padx=(Layout.MD, Layout.XS))

        self.btn_cancel = ctk.CTkButton(
            inner,
            text="⏹ Cancelar",
            width=110,
            height=36,
            command=lambda: self.queue_panel.cancel_queue(),
            state="disabled",
            **warning,
        )
        self.btn_cancel.pack(side="left", padx=Layout.XS)

        ctk.CTkButton(
            inner,
            text="📂 Abrir Pasta",
            width=120,
            height=36,
            command=lambda: self.queue_panel.open_output_folder(),
            **ghost,
        ).pack(side="left", padx=Layout.XS)

        ctk.CTkButton(
            inner,
            text="⚙ Configurações",
            width=130,
            height=36,
            command=self._open_settings,
            **ghost,
        ).pack(side="left", padx=(Layout.XS, 0))

    def _build_main_area(self) -> None:
        main = ctk.CTkFrame(self.root, fg_color="transparent")
        main.grid(row=1, column=0, sticky="nsew", padx=Layout.LG, pady=(0, Layout.SM))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(0, weight=1)

        self.queue_panel = QueuePanel(
            main,
            self.queue_manager,
            self.theme,
            on_selection_change=self._on_job_selected,
            on_view_result=self._view_result,
        )
        self.queue_panel.grid(row=0, column=0, sticky="nsew")
        self.queue_panel.set_status_handler(self._set_status)

    def _build_status_bar(self) -> None:
        colors = self.theme.colors()
        bar = ctk.CTkFrame(
            self.root,
            fg_color=colors["header_bg"],
            border_color=colors["border"],
            border_width=1,
            corner_radius=Layout.CORNER_RADIUS_SM,
            height=32,
        )
        bar.grid(row=2, column=0, sticky="ew", padx=Layout.LG, pady=(0, Layout.LG))
        bar.grid_propagate(False)

        self.status_label = ctk.CTkLabel(
            bar,
            text=self._stats_text(self.queue_manager.stats),
            font=caption(),
            text_color=colors["text_secondary"],
            anchor="w",
        )
        self.status_label.pack(fill="both", expand=True, padx=Layout.MD, pady=Layout.XS)

    @staticmethod
    def _stats_text(stats: QueueStats) -> str:
        return (
            f"Total: {stats.total} | Aguardando: {stats.waiting} | "
            f"Processando: {stats.processing} | Concluídos: {stats.completed} | "
            f"Erros: {stats.errors}"
        )

    def _open_settings(self) -> None:
        self.settings_modal.show()

    def _queue_maintenance(self, action: Callable[[], None]) -> None:
        action()
        self.queue_panel.refresh()

    def _view_result(self, job: TranscriptionJob | None) -> None:
        if job:
            self.result_viewer.show_job(job)

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
        self.root.bind_all("<Control-t>", lambda _e: self.queue_panel.start_queue())
        self.root.bind_all("<Control-e>", lambda _e: self.result_viewer.export_via_shortcut())
        self.root.bind_all("<Control-comma>", lambda _e: self._open_settings())
        self.root.bind_all("<Control-q>", lambda _e: self.root.destroy())

    def _drop_event(self, event) -> None:
        paths = parse_dropped_paths(event.data)
        if paths:
            self._add_paths(paths)
            self._set_status(f"{len(paths)} arquivo(s) adicionado(s) à fila.")
        else:
            self._set_status("Arquivo não encontrado no drag & drop.")

    def add_files_dialog(self) -> None:
        """Abre o seletor após o handler do botão retornar (evita UI congelada)."""
        self.root.after(1, self._open_files_dialog)

    def _open_files_dialog(self) -> None:
        try:
            self.root.update_idletasks()
            paths = list(
                fd.askopenfilenames(
                    parent=self.root,
                    title="Escolha arquivos para processar",
                    filetypes=FILE_DIALOG_TYPES,
                )
            )
            if paths:
                self._add_paths(list(paths))
        except Exception:
            self._logger.exception("Erro ao abrir seletor de arquivos")
            traceback.print_exc()
            self._set_status("Erro ao abrir seletor de arquivos.")

    def add_folder_dialog(self) -> None:
        self.root.after(1, self._open_folder_dialog)

    def _open_folder_dialog(self) -> None:
        try:
            self.root.update_idletasks()
            folder = fd.askdirectory(
                parent=self.root,
                title="Escolha uma pasta com arquivos para processar",
            )
            if not folder:
                return
            paths = collect_supported_files(folder)
            if not paths:
                self._set_status("Nenhum arquivo suportado encontrado na pasta.")
                return
            self._add_paths(paths)
        except Exception:
            self._logger.exception("Erro ao abrir seletor de pasta")
            traceback.print_exc()
            self._set_status("Erro ao abrir seletor de pasta.")

    def _add_paths(self, paths: list[str]) -> None:
        try:
            added = self.queue_manager.add_files(paths)
            self.queue_panel.refresh()
            if added:
                self._set_status(f"{len(added)} arquivo(s) na fila.")
                self.queue_manager.select_job(added[-1].id)
                self._on_job_selected(self.queue_manager.selected_job)
            self._update_progress(
                self.queue_manager.get_overall_progress(),
                self.queue_manager.stats,
            )
        except Exception:
            self._logger.exception("Erro ao adicionar arquivos à fila")
            traceback.print_exc()
            self._set_status("Erro ao adicionar arquivos à fila.")

    def _on_job_selected(self, job: TranscriptionJob | None) -> None:
        pass

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
        if self.status_label is not None:
            self.status_label.configure(text_color=colors["text_secondary"])
        self.settings_modal.refresh_theme()
        self.queue_panel.refresh_theme()
        self.result_viewer.refresh_theme()
        self._set_status(f"Tema alterado para {theme}")

    def _on_job_updated_threadsafe(self, job: TranscriptionJob) -> None:
        self.root.after(0, lambda j=job: self._on_job_updated(j))

    def _on_queue_idle_threadsafe(self) -> None:
        self.root.after(0, self._on_queue_idle)

    def _on_status_threadsafe(self, message: str) -> None:
        self.root.after(0, lambda m=message: self._set_status(m))

    def _on_progress_threadsafe(self, value: float, stats: QueueStats) -> None:
        self.root.after(0, lambda v=value, s=stats: self._update_progress(v, s))

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
                msg += " Clique em Iniciar transcrição para continuar."
            self._set_status(msg)
            if self.queue_manager.jobs:
                self.queue_manager.select_job(self.queue_manager.jobs[0].id)
                self._on_job_selected(self.queue_manager.selected_job)
        self._update_progress(
            self.queue_manager.get_overall_progress(),
            self.queue_manager.stats,
        )

    def _on_queue_recovered(self, meta: dict) -> None:
        self.queue_panel.set_queue_restored(bool(meta.get("restored")))
        self.queue_panel.refresh()

    def _on_job_updated(self, job: TranscriptionJob) -> None:
        """Atualiza apenas fila + detalhes compactos — sem result_panel legado."""
        try:
            self.queue_panel.update_job(job)
            if job.status == JobStatus.COMPLETED:
                self.settings_modal.refresh_history()
            self._update_progress(
                self.queue_manager.get_overall_progress(),
                self.queue_manager.stats,
            )
        except Exception:
            self._logger.exception(
                "Falha ao atualizar UI do job %s (status=%s, progress=%.0f%%)",
                job.file_name,
                job.status.value,
                job.job_progress * 100,
            )
            traceback.print_exc()

    def _on_queue_idle(self) -> None:
        try:
            self._update_progress(
                self.queue_manager.get_overall_progress(),
                self.queue_manager.stats,
            )
            self.settings_modal.refresh_history()
        except Exception:
            self._logger.exception("Falha ao finalizar atualização da fila na UI")
            traceback.print_exc()

    def _update_progress(self, value: float, stats: QueueStats) -> None:
        try:
            self.queue_panel.update_progress(value, stats)
            if self.status_label is not None and self.status_label.winfo_exists():
                self.status_label.configure(text=self._stats_text(stats))
            processing = self.queue_manager.is_processing
            if self.btn_start is not None and self.btn_start.winfo_exists():
                self.btn_start.configure(state="disabled" if processing else "normal")
            if self.btn_cancel is not None and self.btn_cancel.winfo_exists():
                self.btn_cancel.configure(state="normal" if processing else "disabled")
        except Exception:
            self._logger.exception("Falha ao atualizar barra de status/toolbar")
            traceback.print_exc()

    def _set_status(self, message: str) -> None:
        self._last_status_message = message

    def run(self) -> None:
        self.root.mainloop()


def run_app() -> None:
    MainWindow().run()
