from __future__ import annotations

import tkinter.filedialog as fd
from typing import Callable, Optional

import customtkinter as ctk

from src.core.export_service import ExportService
from src.models.transcription_job import JobStatus, TranscriptionJob

PREVIEW_CHAR_LIMIT = 12_000


class ResultPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_status: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, corner_radius=12, **kwargs)
        self.on_status = on_status
        self._export = ExportService()
        self._current_job: Optional[TranscriptionJob] = None
        self._current_text = ""
        self._preview_truncated = False

        ctk.CTkLabel(
            self,
            text="Resultado",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(12, 8), padx=16, anchor="w")

        self.meta_label = ctk.CTkLabel(
            self,
            text="Selecione um item da fila para visualizar.",
            text_color="gray55",
            font=ctk.CTkFont(size=11),
            anchor="w",
            wraplength=700,
        )
        self.meta_label.pack(fill="x", padx=16, pady=(0, 6))

        preview_bar = ctk.CTkFrame(self, fg_color="transparent")
        preview_bar.pack(fill="x", padx=16, pady=(0, 4))

        self.preview_info = ctk.CTkLabel(
            preview_bar,
            text="",
            text_color="gray55",
            font=ctk.CTkFont(size=10),
            anchor="w",
        )
        self.preview_info.pack(side="left", fill="x", expand=True)

        self.btn_load_full = ctk.CTkButton(
            preview_bar,
            text="Carregar texto completo",
            width=160,
            height=24,
            font=ctk.CTkFont(size=11),
            command=self._load_full_text,
        )
        self.btn_load_full.pack(side="right")
        self.btn_load_full.pack_forget()

        self.text_box = ctk.CTkTextbox(
            self,
            height=160,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
        )
        self.text_box.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self.text_box.insert("1.0", "O texto transcrito ou extraído aparecerá aqui.")
        self.text_box.configure(state="disabled")

        export_row = ctk.CTkFrame(self, fg_color="transparent")
        export_row.pack(fill="x", padx=16, pady=(0, 12))

        self.btn_txt = ctk.CTkButton(
            export_row, text="Exportar TXT", width=110, state="disabled", command=lambda: self.export_manual("txt")
        )
        self.btn_txt.pack(side="left", padx=4)

        self.btn_json = ctk.CTkButton(
            export_row, text="Exportar JSON", width=110, state="disabled", command=lambda: self.export_manual("json")
        )
        self.btn_json.pack(side="left", padx=4)

        self.btn_md = ctk.CTkButton(
            export_row, text="Exportar MD", width=110, state="disabled", command=lambda: self.export_manual("md")
        )
        self.btn_md.pack(side="left", padx=4)

    def show_job(self, job: Optional[TranscriptionJob]) -> None:
        self._current_job = job
        self._preview_truncated = False
        self.btn_load_full.pack_forget()
        self.preview_info.configure(text="")

        if not job:
            self._set_text_content(
                "O texto transcrito ou extraído aparecerá aqui.",
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
            self._set_text_content(job.result_text or "(vazio)", full_text=job.result_text, meta=meta)
            self._set_export_enabled(bool((job.result_text or "").strip()))
            return

        self._set_text_content(
            "Aguardando processamento na fila.",
            full_text="",
            meta=f"{job.file_name} — {job.status.value}",
        )
        self._set_export_enabled(False)

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
            self._export.save(path, self._current_text, fmt)  # type: ignore[arg-type]
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
