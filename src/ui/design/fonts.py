"""Tipografia e identidade textual do CortexFlow."""

from __future__ import annotations

import customtkinter as ctk

APP_NAME = "CortexFlow"
APP_VERSION = "2.9"
APP_TAGLINE = "Preparação inteligente de conhecimento para IA"

_FONT_FAMILY = "Segoe UI"


def brand_title() -> ctk.CTkFont:
    return ctk.CTkFont(family=_FONT_FAMILY, size=22, weight="bold")


def brand_subtitle() -> ctk.CTkFont:
    return ctk.CTkFont(family=_FONT_FAMILY, size=11)


def section_title() -> ctk.CTkFont:
    return ctk.CTkFont(family=_FONT_FAMILY, size=17, weight="bold")


def panel_title() -> ctk.CTkFont:
    return ctk.CTkFont(family=_FONT_FAMILY, size=15, weight="bold")


def body() -> ctk.CTkFont:
    return ctk.CTkFont(family=_FONT_FAMILY, size=12)


def body_small() -> ctk.CTkFont:
    return ctk.CTkFont(family=_FONT_FAMILY, size=11)


def caption() -> ctk.CTkFont:
    return ctk.CTkFont(family=_FONT_FAMILY, size=10)


def mono(size: int = 11) -> ctk.CTkFont:
    return ctk.CTkFont(family="Consolas", size=size)


def badge() -> ctk.CTkFont:
    return ctk.CTkFont(family=_FONT_FAMILY, size=10, weight="bold")
