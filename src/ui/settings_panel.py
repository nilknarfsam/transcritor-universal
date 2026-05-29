from __future__ import annotations

import tkinter.filedialog as fd
from typing import Callable, Optional

import customtkinter as ctk

from src.core.settings_service import SettingsService
from src.library import get_library
from src.ui.design.fonts import APP_NAME, APP_TAGLINE, APP_VERSION, body_small, mono, panel_title
from src.ui.design.spacing import Layout
from src.ui.design.theme_manager import ThemeManager


class BrandSidebar(ctk.CTkFrame):
    """Barra lateral mínima: marca, versão e slogan."""

    def __init__(self, master, theme: ThemeManager, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.theme = theme
        self._apply_frame_style()
        self._build_brand()

    def _apply_frame_style(self) -> None:
        self.configure(**self.theme.sidebar_kwargs())

    def refresh_theme(self) -> None:
        self._apply_frame_style()
        colors = self.theme.colors()
        self.brand_tagline.configure(text_color=colors["text_secondary"])
        self.version_badge.configure(
            text_color=colors["text_muted"],
            fg_color=colors["surface_elevated"],
        )

    def _build_brand(self) -> None:
        colors = self.theme.colors()
        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.pack(fill="both", expand=True, padx=Layout.LG, pady=Layout.LG)

        ctk.CTkLabel(
            brand,
            text=APP_NAME,
            font=panel_title(),
            text_color=colors["text_primary"],
            anchor="w",
        ).pack(fill="x")

        self.version_badge = ctk.CTkLabel(
            brand,
            text=f"v{APP_VERSION}",
            font=body_small(),
            text_color=colors["text_muted"],
            fg_color=colors["surface_elevated"],
            corner_radius=6,
            padx=6,
            pady=1,
            anchor="w",
        )
        self.version_badge.pack(fill="x", pady=(Layout.SM, 0))

        self.brand_tagline = ctk.CTkLabel(
            brand,
            text=APP_TAGLINE,
            font=body_small(),
            text_color=colors["text_secondary"],
            wraplength=180,
            justify="left",
            anchor="w",
        )
        self.brand_tagline.pack(fill="x", pady=(Layout.MD, 0))


class AppSettingsPanel(ctk.CTkFrame):
    """Preferências da aplicação (aba Configurações)."""

    def __init__(
        self,
        master,
        settings: SettingsService,
        theme: ThemeManager,
        on_theme_change: Optional[Callable[[str], None]] = None,
        on_settings_change: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.settings = settings
        self.theme = theme
        self.on_theme_change = on_theme_change
        self.on_settings_change = on_settings_change

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)
        self.scroll.grid_columnconfigure(0, weight=1)
        self.scroll.grid_columnconfigure(1, weight=1)

        self._build_controls()
        self._build_extra()
        self._build_history()

    def refresh_theme(self) -> None:
        colors = self.theme.colors()
        self.output_label.configure(text_color=colors["text_muted"])

    def _pad(self) -> dict:
        return {"padx": Layout.MD, "pady": (Layout.XS, Layout.SM), "sticky": "w"}

    def _label(self, parent, row: int, col: int, text: str) -> None:
        ctk.CTkLabel(parent, text=text, anchor="w", font=body_small()).grid(
            row=row, column=col, **self._pad()
        )

    def _build_controls(self) -> None:
        s = self.scroll
        row = 0

        title = ctk.CTkLabel(s, text="Configurações", font=panel_title(), anchor="w")
        title.grid(row=row, column=0, columnspan=2, padx=Layout.MD, pady=(0, Layout.MD), sticky="w")
        row += 1

        self._label(s, row, 0, "Tema")
        self.theme_menu = ctk.CTkOptionMenu(
            s,
            values=["System", "Light", "Dark"],
            command=self._change_theme,
            width=280,
            **self.theme.option_menu_kwargs(),
        )
        self.theme_menu.set(self.settings.theme)
        self.theme_menu.grid(row=row + 1, column=0, padx=Layout.MD, pady=(0, Layout.MD), sticky="w")
        row += 2

        self._label(s, row, 0, "Idioma (Whisper / OCR)")
        idiomas = ["auto", "pt", "en", "es", "fr", "de", "it", "ru", "zh"]
        self.language_var = ctk.StringVar(value=self.settings.language)
        self.language_menu = ctk.CTkOptionMenu(
            s,
            values=idiomas,
            variable=self.language_var,
            command=self._change_language,
            width=280,
        )
        self.language_menu.grid(row=row + 1, column=0, padx=Layout.MD, pady=(0, Layout.MD), sticky="w")
        row += 2

        self._label(s, row, 0, "Formato padrão de saída")
        self.format_menu = ctk.CTkOptionMenu(
            s,
            values=["txt", "md", "json"],
            command=self._change_format,
            width=280,
        )
        self.format_menu.set(self.settings.default_export_format)
        self.format_menu.grid(row=row + 1, column=0, padx=Layout.MD, pady=(0, Layout.MD), sticky="w")
        row += 2

        self._label(s, row, 0, "Modo de exportação")
        self.export_mode_menu = ctk.CTkOptionMenu(
            s,
            values=["raw", "clean", "ai_ready", "notebooklm", "study_mode"],
            command=self._change_export_mode,
            width=280,
        )
        self.export_mode_menu.set(self.settings.export_mode)
        self.export_mode_menu.grid(row=row + 1, column=0, padx=Layout.MD, pady=(0, Layout.MD), sticky="w")
        row += 2

        self._label(s, row, 0, "Tipo de conteúdo")
        self.template_menu = ctk.CTkOptionMenu(
            s,
            values=["generic", "sermon", "podcast", "course"],
            command=self._change_template,
            width=280,
        )
        self.template_menu.set(self.settings.content_template)
        self.template_menu.grid(row=row + 1, column=0, padx=Layout.MD, pady=(0, Layout.MD), sticky="w")

        lib = get_library()
        ws_pairs = lib.workspaces.list_names()
        ws_labels = [name for _, name in ws_pairs]
        ws_ids = [wid for wid, _ in ws_pairs]
        current_ws = self.settings.workspace_id
        if current_ws in ws_ids:
            ws_index = ws_ids.index(current_ws)
        else:
            ws_index = 0

        col_row = 0
        self._label(s, col_row, 1, "Workspace")
        self.workspace_menu = ctk.CTkOptionMenu(
            s,
            values=ws_labels or ["Biblioteca Principal"],
            command=self._change_workspace,
            width=280,
        )
        if ws_labels:
            self.workspace_menu.set(ws_labels[ws_index])
        self.workspace_menu.grid(row=col_row + 1, column=1, padx=Layout.MD, pady=(0, Layout.MD), sticky="w")
        self._workspace_ids = ws_ids
        col_row += 2

        col_names = lib.collections.list_names() + ["(nova…)"]
        self._label(s, col_row, 1, "Coleção")
        self.collection_menu = ctk.CTkOptionMenu(
            s,
            values=col_names or ["Estudos"],
            command=self._change_collection,
            width=280,
        )
        if self.settings.collection_name and self.settings.collection_name in col_names:
            self.collection_menu.set(self.settings.collection_name)
        elif col_names:
            self.collection_menu.set(col_names[0])
        self.collection_menu.grid(row=col_row + 1, column=1, padx=Layout.MD, pady=(0, Layout.MD), sticky="w")
        col_row += 2

        self._label(s, col_row, 1, "Autor")
        self.author_entry = ctk.CTkEntry(s, width=280, placeholder_text="opcional")
        self.author_entry.insert(0, self.settings.library_author)
        self.author_entry.grid(row=col_row + 1, column=1, padx=Layout.MD, pady=(0, Layout.MD), sticky="w")
        self.author_entry.bind("<FocusOut>", lambda _e: self._save_author())
        col_row += 2

        self._label(s, col_row, 1, "Speaker")
        self.speaker_entry = ctk.CTkEntry(s, width=280, placeholder_text="opcional")
        self.speaker_entry.insert(0, self.settings.library_speaker)
        self.speaker_entry.grid(row=col_row + 1, column=1, padx=Layout.MD, pady=(0, Layout.MD), sticky="w")
        self.speaker_entry.bind("<FocusOut>", lambda _e: self._save_speaker())

        self._controls_row_end = row

    def _build_extra(self) -> None:
        s = self.scroll
        row = self._controls_row_end + 2

        ctk.CTkLabel(s, text="Biblioteca e saída", font=panel_title(), anchor="w").grid(
            row=row, column=0, columnspan=2, padx=Layout.MD, pady=(Layout.MD, Layout.SM), sticky="w"
        )
        row += 1

        self._label(s, row, 0, "Categoria / Tags")
        self.category_entry = ctk.CTkEntry(s, width=280, placeholder_text="categoria")
        self.category_entry.insert(0, self.settings.library_category)
        self.category_entry.grid(row=row + 1, column=0, padx=Layout.MD, pady=(0, Layout.XS), sticky="w")
        self.category_entry.bind("<FocusOut>", lambda _e: self._save_category())

        self.tags_entry = ctk.CTkEntry(s, width=280, placeholder_text="tags separadas por vírgula")
        self.tags_entry.insert(0, self.settings.library_tags)
        self.tags_entry.grid(row=row + 2, column=0, padx=Layout.MD, pady=(0, Layout.MD), sticky="w")
        self.tags_entry.bind("<FocusOut>", lambda _e: self._save_tags())
        row += 3

        self._label(s, row, 0, "Tipo de conhecimento")
        self.knowledge_menu = ctk.CTkOptionMenu(
            s,
            values=["document", "sermon", "podcast", "course", "meeting", "research"],
            command=self._change_knowledge_type,
            width=280,
        )
        self.knowledge_menu.set(self.settings.knowledge_type)
        self.knowledge_menu.grid(row=row + 1, column=0, padx=Layout.MD, pady=(0, Layout.MD), sticky="w")
        row += 2

        self._label(s, row, 0, "Pasta global de saída")
        self.output_label = ctk.CTkLabel(
            s,
            text=self._output_label_text(),
            wraplength=400,
            justify="left",
            text_color=self.theme.colors()["text_muted"],
            font=body_small(),
        )
        self.output_label.grid(row=row + 1, column=0, columnspan=2, padx=Layout.MD, pady=(0, Layout.SM), sticky="w")
        row += 2

        btn_row = ctk.CTkFrame(s, fg_color="transparent")
        btn_row.grid(row=row, column=0, columnspan=2, padx=Layout.MD, pady=(0, Layout.MD), sticky="w")
        ctk.CTkButton(
            btn_row,
            text="Escolher Pasta",
            command=self._choose_output_folder,
            width=160,
            **self.theme.primary_button_kwargs(),
        ).pack(side="left", padx=(0, Layout.SM))
        ctk.CTkButton(
            btn_row,
            text="Usar pasta do arquivo",
            command=self._clear_output_folder,
            width=180,
            **self.theme.ghost_button_kwargs(),
        ).pack(side="left")

        self._extra_row_end = row + 1

    def _build_history(self) -> None:
        s = self.scroll
        row = self._extra_row_end + 1

        ctk.CTkLabel(s, text="Histórico recente", font=panel_title(), anchor="w").grid(
            row=row, column=0, columnspan=2, padx=Layout.MD, pady=(Layout.SM, Layout.XS), sticky="w"
        )

        self.history_box = ctk.CTkTextbox(s, height=160, font=mono())
        self.history_box.grid(
            row=row + 1, column=0, columnspan=2, padx=Layout.MD, pady=(0, Layout.LG), sticky="ew"
        )
        self.history_box.configure(state="disabled")
        self.refresh_history()

    def _output_label_text(self) -> str:
        folder = self.settings.output_folder.strip()
        if folder:
            return folder
        return "(mesma pasta do arquivo original)"

    def _change_theme(self, value: str) -> None:
        self.settings.theme = value
        if self.on_theme_change:
            self.on_theme_change(value)

    def _change_language(self, value: str) -> None:
        self.settings.language = value
        self._notify_change()

    def _change_format(self, value: str) -> None:
        self.settings.default_export_format = value
        self._notify_change()

    def _change_export_mode(self, value: str) -> None:
        self.settings.export_mode = value
        self._notify_change()

    def _change_template(self, value: str) -> None:
        self.settings.content_template = value
        self._notify_change()

    def _change_workspace(self, value: str) -> None:
        if hasattr(self, "_workspace_ids") and value:
            lib = get_library()
            for ws_id, name in lib.workspaces.list_names():
                if name == value:
                    self.settings.workspace_id = ws_id
                    break
        self._notify_change()

    def _change_collection(self, value: str) -> None:
        if value == "(nova…)":
            return
        lib = get_library()
        col = lib.collections.get_by_name(value)
        if col:
            self.settings.collection_id = str(col["id"])
            self.settings.collection_name = str(col.get("name", ""))
        else:
            created = lib.collections.create(value)
            self.settings.collection_id = str(created["id"])
            self.settings.collection_name = str(created.get("name", ""))
        self._notify_change()

    def _save_author(self) -> None:
        self.settings.library_author = self.author_entry.get().strip()
        self._notify_change()

    def _save_speaker(self) -> None:
        self.settings.library_speaker = self.speaker_entry.get().strip()
        self._notify_change()

    def _save_category(self) -> None:
        self.settings.library_category = self.category_entry.get().strip()
        self._notify_change()

    def _save_tags(self) -> None:
        self.settings.library_tags = self.tags_entry.get().strip()
        self._notify_change()

    def _change_knowledge_type(self, value: str) -> None:
        self.settings.knowledge_type = value
        self._notify_change()

    def _choose_output_folder(self) -> None:
        folder = fd.askdirectory(title="Pasta global de saída")
        if folder:
            self.settings.output_folder = folder
            self.output_label.configure(text=self._output_label_text())
            self._notify_change()

    def _clear_output_folder(self) -> None:
        self.settings.output_folder = ""
        self.output_label.configure(text=self._output_label_text())
        self._notify_change()

    def _notify_change(self) -> None:
        if self.on_settings_change:
            self.on_settings_change()

    def refresh_history(self) -> None:
        self.history_box.configure(state="normal")
        self.history_box.delete("1.0", "end")
        history = self.settings.history
        if not history:
            self.history_box.insert("1.0", "Nenhuma transcrição recente.")
        else:
            for item in reversed(history):
                status = item.get("status", "concluído")
                line = f"- {item['arquivo']} ({item['tipo']}) [{status}]"
                if item.get("export_mode"):
                    line += f" · {item['export_mode']}"
                if item.get("template_usado"):
                    line += f" · {item['template_usado']}"
                if item.get("pipeline_stage"):
                    line += f" · {item['pipeline_stage']}"
                if item.get("topicos"):
                    line += f" · {item['topicos'][:40]}"
                if item.get("referencias"):
                    line += f" · refs:{item['referencias']}"
                if item.get("cache_hit"):
                    line += f" · cache:{item['cache_hit']}"
                if item.get("processing_time"):
                    line += f" · {item['processing_time']}"
                if item.get("reused_pipeline") == "sim":
                    line += " · reutilizado"
                if item.get("recovery_used") == "sim":
                    line += " · recovery"
                if item.get("workspace"):
                    line += f" · {item['workspace'][:20]}"
                if item.get("collection"):
                    line += f" / {item['collection'][:16]}"
                if item.get("catalog_id"):
                    line += f" · id:{item['catalog_id'][:10]}"
                if item.get("flashcards_count"):
                    line += f" · fc:{item['flashcards_count']}"
                if item.get("quizzes_count"):
                    line += f" · quiz:{item['quizzes_count']}"
                if item.get("difficulty"):
                    line += f" · {item['difficulty']}"
                if item.get("mensagem"):
                    line += f" — {item['mensagem'][:60]}"
                self.history_box.insert("end", line + "\n")
        self.history_box.configure(state="disabled")


# Compatibilidade com imports legados
SettingsPanel = AppSettingsPanel
