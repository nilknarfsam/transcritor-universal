"""Componentes visuais da fila de transcrição — UX 3.0.2."""

from __future__ import annotations

import traceback
from datetime import datetime
from typing import Optional

import customtkinter as ctk

from src.core.log_service import get_logger

from src.models.transcription_job import JobStatus, TranscriptionJob
from src.ui.design.colors import SEMANTIC
from src.ui.design.fonts import badge, body_small, caption, panel_title
from src.ui.design.spacing import Layout
from src.ui.design.theme_manager import ThemeManager

ACCEPTED_FORMATS_HINT = (
    "áudio · vídeo · PDF · DOCX · XLSX · imagens · TXT"
)

EMPTY_QUEUE_MESSAGE = (
    "Arraste arquivos aqui ou clique em Adicionar arquivos para começar."
)


class StatusBadge(ctk.CTkLabel):
    """Badge padronizado para status da fila e cache."""

    _LABELS = {
        "waiting": "aguardando",
        "processing": "processando",
        "completed": "concluído",
        "error": "erro",
        "cancelled": "cancelado",
        "cache_hit": "cache hit",
        "cache_miss": "cache miss",
    }

    def __init__(self, master, status_key: str, theme: ThemeManager, **kwargs) -> None:
        self.theme = theme
        self._status_key = status_key
        text = self._LABELS.get(status_key, status_key)
        super().__init__(
            master,
            text=text,
            font=badge(),
            corner_radius=6,
            padx=8,
            pady=2,
            **kwargs,
        )
        self.apply_status(status_key)

    def apply_status(self, status_key: str) -> None:
        self._status_key = status_key
        self.configure(text=self._LABELS.get(status_key, status_key))
        if status_key == "cache_hit":
            self.configure(text_color="#FFFFFF", fg_color=SEMANTIC["success"])
        elif status_key == "cache_miss":
            self.configure(text_color="#FFFFFF", fg_color=SEMANTIC["warning"])
        else:
            self.configure(
                text_color="#FFFFFF",
                fg_color=self.theme.status_color(status_key),
            )


class QueueEmptyState(ctk.CTkFrame):
    def __init__(self, master, theme: ThemeManager, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        colors = theme.colors()
        ctk.CTkLabel(
            self,
            text=EMPTY_QUEUE_MESSAGE,
            font=body_small(),
            text_color=colors["text_secondary"],
            wraplength=520,
            justify="center",
        ).pack(pady=(Layout.XXL, Layout.SM))
        ctk.CTkLabel(
            self,
            text=ACCEPTED_FORMATS_HINT,
            font=caption(),
            text_color=colors["text_muted"],
            justify="center",
        ).pack(pady=(0, Layout.XXL))


class JobDetailsPanel(ctk.CTkFrame):
    """Detalhes compactos do item selecionado — UX 3.1."""

    def __init__(self, master, theme: ThemeManager, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.theme = theme
        self._apply_style()
        self._fields: dict[str, ctk.CTkLabel] = {}
        self._build()

    def _apply_style(self) -> None:
        self.configure(**self.theme.frame_kwargs(elevated=False))

    def refresh_theme(self) -> None:
        self._apply_style()
        colors = self.theme.colors()
        for lbl in self._fields.values():
            lbl.configure(text_color=colors["text_primary"])

    def _build(self) -> None:
        colors = self.theme.colors()
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=Layout.MD, pady=(Layout.SM, Layout.XS))

        ctk.CTkLabel(
            header,
            text="Detalhes do item",
            font=body_small(),
            text_color=colors["text_secondary"],
            anchor="w",
        ).pack(side="left")

        self._cache_detail_badge = StatusBadge(header, "waiting", self.theme)
        self._cache_detail_badge.pack(side="right")
        self._cache_detail_badge.pack_forget()

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=Layout.MD, pady=(0, Layout.SM))
        for col in (0, 1, 2, 3):
            grid.grid_columnconfigure(col, weight=1)

        labels = (
            ("Nome", "name"),
            ("Status", "status"),
            ("Cache", "cache"),
            ("Saída", "output"),
        )
        for col, (title, key) in enumerate(labels):
            ctk.CTkLabel(
                grid,
                text=title,
                font=caption(),
                text_color=colors["text_muted"],
                anchor="w",
            ).grid(row=0, column=col, sticky="w", padx=(0, Layout.XS), pady=(0, 2))
            value = ctk.CTkLabel(
                grid,
                text="—",
                font=body_small(),
                text_color=colors["text_primary"],
                anchor="w",
                justify="left",
            )
            value.grid(row=1, column=col, sticky="ew", pady=(0, 2))
            self._fields[key] = value

    @staticmethod
    def _short_path(path: str, max_len: int = 28) -> str:
        if not path or path == "—":
            return "—"
        name = path.replace("\\", "/").split("/")[-1]
        if len(name) <= max_len:
            return name
        return name[: max_len - 1] + "…"

    def show_job(self, job: Optional[TranscriptionJob]) -> None:
        try:
            self._show_job_impl(job)
        except Exception:
            get_logger().exception("Falha ao atualizar detalhes compactos do item")
            traceback.print_exc()

    def _show_job_impl(self, job: Optional[TranscriptionJob]) -> None:
        colors = self.theme.colors()
        if not job:
            for lbl in self._fields.values():
                lbl.configure(text="—", text_color=colors["text_muted"])
            self._cache_detail_badge.pack_forget()
            return

        self._fields["name"].configure(
            text=self._short_path(job.file_name, 32),
            text_color=colors["text_primary"],
        )
        self._fields["status"].configure(text=job.status.value, text_color=colors["text_primary"])
        self._fields["cache"].configure(
            text=_cache_label(job.cache_status),
            text_color=colors["text_primary"],
        )
        self._fields["output"].configure(
            text=self._short_path(job.output_path or "—"),
            text_color=colors["text_primary"],
        )

        cache_key = _cache_badge_key(job.cache_status)
        if cache_key:
            self._cache_detail_badge.apply_status(cache_key)
            self._cache_detail_badge.pack(side="right")
        else:
            self._cache_detail_badge.pack_forget()


def _cache_label(status: str) -> str:
    if status == "hit":
        return "HIT"
    if status == "miss":
        return "MISS"
    if status == "partial":
        return "PARTIAL"
    return "—"


def _cache_badge_key(status: str) -> Optional[str]:
    if status == "hit":
        return "cache_hit"
    if status == "miss":
        return "cache_miss"
    return None


def _elapsed_label(job: TranscriptionJob) -> str:
    if job.status == JobStatus.PROCESSING:
        pct = int(max(0.0, min(1.0, job.job_progress)) * 100)
        return f"{pct}%"
    if job.updated_at and job.created_at:
        try:
            start = datetime.fromisoformat(job.created_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(job.updated_at.replace("Z", "+00:00"))
            seconds = (end - start).total_seconds()
            if seconds > 0:
                return f"{seconds:.1f}s"
        except (ValueError, TypeError):
            pass
    if job.status == JobStatus.COMPLETED:
        return "concluído"
    return "—"
