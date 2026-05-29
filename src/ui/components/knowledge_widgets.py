"""Componentes reutilizáveis — workspace premium de conhecimento."""

from __future__ import annotations

from typing import Any, Callable, Optional

import customtkinter as ctk

from src.ui.design.fonts import badge, body_small, caption, section_title
from src.ui.design.spacing import Layout
from src.ui.design.theme_manager import ThemeManager

TYPE_COLORS = {
    "document": "#2563EB",
    "topic": "#7C3AED",
    "chunk": "#0891B2",
    "flashcard": "#059669",
    "quiz": "#D97706",
    "highlight": "#DB2777",
    "bible_reference": "#4F46E5",
    "tag": "#64748B",
    "speaker": "#0D9488",
    "author": "#6366F1",
    "collection": "#9333EA",
    "workspace": "#475569",
}


class SectionHeader(ctk.CTkFrame):
    def __init__(
        self,
        master,
        title: str,
        theme: ThemeManager,
        subtitle: str = "",
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        colors = theme.colors()
        ctk.CTkLabel(
            self,
            text=title,
            font=section_title(),
            text_color=colors["text_primary"],
            anchor="w",
        ).pack(fill="x")
        if subtitle:
            ctk.CTkLabel(
                self,
                text=subtitle,
                font=caption(),
                text_color=colors["text_muted"],
                anchor="w",
            ).pack(fill="x", pady=(Layout.XS, 0))


class TypeBadge(ctk.CTkLabel):
    def __init__(self, master, result_type: str, theme: ThemeManager, **kwargs) -> None:
        color = TYPE_COLORS.get(result_type, "#64748B")
        super().__init__(
            master,
            text=result_type[:12],
            font=badge(),
            text_color="#FFFFFF",
            fg_color=color,
            corner_radius=6,
            padx=6,
            pady=2,
            **kwargs,
        )


class StatCard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        label: str,
        value: str,
        theme: ThemeManager,
        **kwargs,
    ) -> None:
        colors = theme.colors()
        super().__init__(
            master,
            fg_color=colors["card_bg"],
            border_color=colors["border"],
            border_width=1,
            corner_radius=Layout.CORNER_RADIUS_CARD,
            **kwargs,
        )
        ctk.CTkLabel(
            self,
            text=value,
            font=section_title(),
            text_color=colors["text_primary"],
        ).pack(padx=Layout.SM, pady=(Layout.SM, 0))
        ctk.CTkLabel(
            self,
            text=label,
            font=caption(),
            text_color=colors["text_muted"],
        ).pack(padx=Layout.SM, pady=(0, Layout.SM))


class EmptyState(ctk.CTkFrame):
    def __init__(
        self,
        master,
        message: str,
        theme: ThemeManager,
        hint: str = "",
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        colors = theme.colors()
        ctk.CTkLabel(
            self,
            text=message,
            font=body_small(),
            text_color=colors["text_secondary"],
            wraplength=400,
            justify="center",
        ).pack(pady=Layout.MD)
        if hint:
            ctk.CTkLabel(
                self,
                text=hint,
                font=caption(),
                text_color=colors["text_muted"],
                wraplength=400,
                justify="center",
            ).pack()


class ResultCard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        theme: ThemeManager,
        title: str,
        result_type: str,
        score: float,
        match_reason: str,
        workspace: str = "",
        collection: str = "",
        topics: list[str] | None = None,
        selected: bool = False,
        on_select: Optional[Callable[[], None]] = None,
        on_open: Optional[Callable[[], None]] = None,
        on_related: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        colors = theme.colors()
        super().__init__(
            master,
            fg_color=colors["card_selected"] if selected else colors["card_bg"],
            border_color=colors["primary"] if selected else colors["border"],
            border_width=1 if selected else 0,
            corner_radius=Layout.CORNER_RADIUS_CARD,
            **kwargs,
        )
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=Layout.SM, pady=(Layout.SM, Layout.XS))
        TypeBadge(top, result_type, theme).pack(side="left")
        ctk.CTkLabel(
            top,
            text=f"score {score:.1f}",
            font=caption(),
            text_color=colors["text_muted"],
        ).pack(side="right")

        title_lbl = ctk.CTkLabel(
            self,
            text=title[:72],
            font=body_small(),
            text_color=colors["text_primary"],
            anchor="w",
        )
        title_lbl.pack(fill="x", padx=Layout.SM)
        meta = f"{workspace or '—'} · {collection or '—'}"
        ctk.CTkLabel(
            self,
            text=meta,
            font=caption(),
            text_color=colors["text_muted"],
            anchor="w",
        ).pack(fill="x", padx=Layout.SM)
        if topics:
            ctk.CTkLabel(
                self,
                text=" · ".join(topics[:4]),
                font=caption(),
                text_color=colors["text_secondary"],
                anchor="w",
                wraplength=320,
            ).pack(fill="x", padx=Layout.SM, pady=(0, Layout.XS))
        if match_reason:
            ctk.CTkLabel(
                self,
                text=f"↳ {match_reason}",
                font=caption(),
                text_color=colors["accent"],
                anchor="w",
                wraplength=320,
            ).pack(fill="x", padx=Layout.SM, pady=(0, Layout.XS))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=Layout.SM, pady=(0, Layout.SM))
        if on_open and result_type == "document":
            ctk.CTkButton(
                actions,
                text="Abrir MD",
                width=72,
                height=24,
                command=on_open,
                **theme.accent_button_kwargs(),
            ).pack(side="left", padx=(0, Layout.XS))
        if on_related and result_type == "document":
            ctk.CTkButton(
                actions,
                text="Relacionados",
                width=88,
                height=24,
                command=on_related,
                **theme.ghost_button_kwargs(),
            ).pack(side="left")

        if on_select:
            for w in (self, title_lbl):
                w.bind("<Button-1>", lambda _e: on_select())
