from __future__ import annotations

import tkinter.filedialog as fd
from typing import Callable, Optional

import customtkinter as ctk

from src.core.settings_service import SettingsService


class SettingsPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        settings: SettingsService,
        on_theme_change: Optional[Callable[[str], None]] = None,
        on_settings_change: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, corner_radius=12, **kwargs)
        self.settings = settings
        self.on_theme_change = on_theme_change
        self.on_settings_change = on_settings_change

        ctk.CTkLabel(
            self,
            text="Configurações",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(16, 12), padx=16, anchor="w")

        ctk.CTkLabel(self, text="Tema", anchor="w").pack(fill="x", padx=16, pady=(4, 0))
        self.theme_menu = ctk.CTkOptionMenu(
            self,
            values=["System", "Light", "Dark"],
            command=self._change_theme,
            width=200,
        )
        self.theme_menu.set(self.settings.theme)
        self.theme_menu.pack(padx=16, pady=(4, 12), anchor="w")

        ctk.CTkLabel(self, text="Idioma (Whisper / OCR)", anchor="w").pack(fill="x", padx=16)
        idiomas = ["auto", "pt", "en", "es", "fr", "de", "it", "ru", "zh"]
        self.language_var = ctk.StringVar(value=self.settings.language)
        self.language_menu = ctk.CTkOptionMenu(
            self,
            values=idiomas,
            variable=self.language_var,
            command=self._change_language,
            width=200,
        )
        self.language_menu.pack(padx=16, pady=(4, 12), anchor="w")

        ctk.CTkLabel(self, text="Formato padrão de saída", anchor="w").pack(fill="x", padx=16)
        self.format_menu = ctk.CTkOptionMenu(
            self,
            values=["txt", "md", "json"],
            command=self._change_format,
            width=200,
        )
        self.format_menu.set(self.settings.default_export_format)
        self.format_menu.pack(padx=16, pady=(4, 12), anchor="w")

        ctk.CTkLabel(self, text="Pasta global de saída", anchor="w").pack(fill="x", padx=16)
        self.output_label = ctk.CTkLabel(
            self,
            text=self._output_label_text(),
            wraplength=220,
            justify="left",
            text_color="gray60",
            font=ctk.CTkFont(size=11),
        )
        self.output_label.pack(padx=16, pady=(4, 8), anchor="w")

        ctk.CTkButton(
            self,
            text="Escolher Pasta",
            command=self._choose_output_folder,
            width=200,
        ).pack(padx=16, pady=(0, 8), anchor="w")

        ctk.CTkButton(
            self,
            text="Usar pasta do arquivo",
            command=self._clear_output_folder,
            width=200,
            fg_color="transparent",
            border_width=1,
        ).pack(padx=16, pady=(0, 16), anchor="w")

        ctk.CTkLabel(self, text="Histórico recente", font=ctk.CTkFont(weight="bold")).pack(
            padx=16, pady=(8, 4), anchor="w"
        )
        self.history_box = ctk.CTkTextbox(self, height=140, font=ctk.CTkFont(family="Consolas", size=11))
        self.history_box.pack(padx=16, pady=(0, 16), fill="both", expand=True)
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
                if item.get("mensagem"):
                    line += f" — {item['mensagem'][:60]}"
                self.history_box.insert("end", line + "\n")
        self.history_box.configure(state="disabled")
