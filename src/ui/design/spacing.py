"""Espaçamento e dimensões de layout do CortexFlow."""

from __future__ import annotations


class Layout:
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 20
    XXL = 24

    CORNER_RADIUS = 12
    CORNER_RADIUS_SM = 8
    CORNER_RADIUS_CARD = 10

    SIDEBAR_WIDTH = 200  # legado — não usado na UX 3.1
    TOOLBAR_HEIGHT = 52
    STATUS_BAR_HEIGHT = 32

    PAD_WINDOW = (MD, LG)
    PAD_PANEL = (LG, LG)
    PAD_CARD = (MD, SM)
