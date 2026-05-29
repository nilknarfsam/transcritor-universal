"""Tokens de cor do CortexFlow."""

from __future__ import annotations

BRAND = {
    "primary": "#5B4FCF",
    "primary_hover": "#4A3FB8",
    "accent": "#00B4D8",
    "accent_hover": "#0096B8",
}

LIGHT = {
    "surface": "#F4F5FA",
    "surface_elevated": "#FFFFFF",
    "sidebar": "#EBECF4",
    "border": "#D4D7E4",
    "text_primary": "#14182A",
    "text_secondary": "#4E5368",
    "text_muted": "#7A8096",
    "header_bg": "#FFFFFF",
    "card_bg": "#FFFFFF",
    "card_selected": "#E6E4F8",
    "row_hover": "#EFEEF8",
    "table_header": "#E8E9F0",
}

DARK = {
    "surface": "#0F1118",
    "surface_elevated": "#181B26",
    "sidebar": "#141720",
    "border": "#2A2F42",
    "text_primary": "#F2F4FA",
    "text_secondary": "#A4A9BE",
    "text_muted": "#6E7489",
    "header_bg": "#181B26",
    "card_bg": "#1C2030",
    "card_selected": "#2A2750",
    "row_hover": "#222638",
    "table_header": "#1E2333",
}

STATUS = {
    "waiting": ("#7A8096", "#8B90A5"),
    "processing": ("#5B4FCF", "#7B6FFF"),
    "completed": ("#2E9B6A", "#3DB87A"),
    "error": ("#D64545", "#FF6B6B"),
    "cancelled": ("#D4822A", "#FFB347"),
    "cache_hit": ("#2E9B6A", "#3DB87A"),
    "cache_miss": ("#9A5F18", "#FFB347"),
}

SEMANTIC = {
    "danger": "#B83D4A",
    "danger_hover": "#962F3A",
    "warning": "#9A5F18",
    "warning_hover": "#7A4C12",
    "success": "#2E9B6A",
    "info": "#5B4FCF",
}
