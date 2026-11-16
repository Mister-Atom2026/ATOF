"""Shared UI-consistency tokens and drawing helpers for ATOF menus.

Audit of ``engine.py`` (settings / phone / pause / weapon / storage menus)
showed the same visual vocabulary re-implemented with slightly different
values in every menu:

* backgrounds: ``(14, 14, 20)`` (selection), ``(0, 0, 0)`` (pause, save
  slots), ``(20, 20, 20)`` (settings pages), ``(18, 12, 10)`` (gun shop);
* two competing oranges: ``(212, 91, 18)`` (selection highlight, storage,
  glass accent) and ``(238, 164, 47)`` (gun shop / controls titles);
* active rows: ``(65, 50, 40)`` in the audio/video pages but ``(212, 91, 18)``
  in the storage and selection menus;
* margins and row heights differ from menu to menu (40/50 px, 50-100 px);
* every label is rendered with a bare ``font.render`` -- there is no shared
  outlined-text helper for readable text over bright phone backgrounds.

This module centralises the canonical values (see :data:`DEFAULT_PALETTE`
and :data:`DEFAULT_SPACING`) and provides small, dependency-free primitives
so future menu work can converge on one look.  It deliberately does **not**
import ``engine`` (or touch gameplay systems) to avoid import cycles and to
keep the change surface disjoint from in-flight engine work.

The canonical accent ``(212, 91, 18)`` is kept because it is already used by
the glass HUD prompt (``engine_ui.draw_glass_panel``) and by the majority of
menus; ``(238, 164, 47)`` is retained as a secondary/gold title accent.
"""

from __future__ import annotations

from functools import lru_cache
from typing import NamedTuple, Sequence

import pygame


class MenuPalette(NamedTuple):
    """Colour tokens shared by all menu-like overlays."""

    accent: tuple[int, int, int] = (212, 91, 18)
    accent_gold: tuple[int, int, int] = (238, 164, 47)
    menu_bg: tuple[int, int, int] = (20, 20, 20)
    panel_bg: tuple[int, int, int, int] = (22, 18, 16, 235)
    row_active: tuple[int, int, int] = (65, 50, 40)
    row_idle: tuple[int, int, int] = (38, 38, 38)
    button: tuple[int, int, int] = (85, 85, 85)
    button_hover: tuple[int, int, int] = (212, 91, 18)
    text: tuple[int, int, int] = (255, 255, 255)
    text_soft: tuple[int, int, int] = (220, 220, 220)
    text_muted: tuple[int, int, int] = (150, 150, 150)
    border: tuple[int, int, int] = (70, 52, 38)
    outline: tuple[int, int, int] = (0, 0, 0)
    shadow: tuple[int, int, int, int] = (0, 0, 0, 140)


class MenuSpacing(NamedTuple):
    """Layout tokens shared by all menu-like overlays."""

    margin: int = 40
    row_height: int = 64
    row_gap: int = 12
    radius: int = 12
    button_width: int = 220
    button_height: int = 50


DEFAULT_PALETTE = MenuPalette()
DEFAULT_SPACING = MenuSpacing()

# Expose the most common tokens as flat constants for callers that prefer a
# simple ``from engine_ui_consistency import ACCENT`` style import.
ACCENT = DEFAULT_PALETTE.accent
ACCENT_GOLD = DEFAULT_PALETTE.accent_gold
MENU_BG = DEFAULT_PALETTE.menu_bg
PANEL_BG = DEFAULT_PALETTE.panel_bg
ROW_ACTIVE = DEFAULT_PALETTE.row_active
ROW_IDLE = DEFAULT_PALETTE.row_idle
BUTTON = DEFAULT_PALETTE.button
BUTTON_HOVER = DEFAULT_PALETTE.button_hover
TEXT_PRIMARY = DEFAULT_PALETTE.text
TEXT_SOFT = DEFAULT_PALETTE.text_soft
TEXT_MUTED = DEFAULT_PALETTE.text_muted
BORDER = DEFAULT_PALETTE.border
OUTLINE = DEFAULT_PALETTE.outline

MARGIN = DEFAULT_SPACING.margin
ROW_HEIGHT = DEFAULT_SPACING.row_height
ROW_GAP = DEFAULT_SPACING.row_gap
PANEL_RADIUS = DEFAULT_SPACING.radius
BUTTON_WIDTH = DEFAULT_SPACING.button_width
BUTTON_HEIGHT = DEFAULT_SPACING.button_height

_ANCHORS = frozenset(
    (
        "topleft", "top", "topright", "left", "center", "right",
        "bottomleft", "bottom", "bottomright", "midtop", "midleft",
        "midright", "midbottom",
    )
)


def clamp_color(color: Sequence[int | float]) -> tuple[int, ...]:
    """Return ``color`` as integer RGB(A) channels clamped to ``0..255``.

    Accepts 3- or 4-component sequences; any other length is a programming
    error and raises :class:`ValueError`.
    """
    values = tuple(color)
    if len(values) not in (3, 4):
        raise ValueError(f"color must have 3 or 4 channels, got {len(values)}")
    return tuple(max(0, min(255, int(channel))) for channel in values)


@lru_cache(maxsize=256)
def _render_text(font: pygame.font.Font, text: str, color: tuple[int, ...]) -> pygame.Surface:
    """Cached plain-text renderer (surfaces are treated as immutable)."""
    return font.render(text, True, color)


def draw_outlined_text(
    surface: pygame.Surface,
    text: str,
    position: tuple[int, int],
    font: pygame.font.Font,
    *,
    color: Sequence[int] | None = None,
    outline_color: Sequence[int] | None = None,
    outline_width: int = 2,
    anchor: str = "topleft",
) -> pygame.Rect:
    """Blit ``text`` with a solid outline and return the *text* rect.

    The outline is produced by blitting the glyphs once per offset in the
    square ring around the text (cheap and font-independent).  ``anchor`` is
    any :class:`pygame.Rect` anchor name and controls how ``position`` is
    interpreted.  The returned rect matches the plain text size (the outline
    extends ``outline_width`` pixels beyond it) so it can be used directly
    for hover/hit testing.
    """
    if anchor not in _ANCHORS:
        raise ValueError(f"unknown anchor: {anchor!r}")

    fill = clamp_color(DEFAULT_PALETTE.text if color is None else color)
    edge = clamp_color(DEFAULT_PALETTE.outline if outline_color is None else outline_color)
    outline_width = max(0, int(outline_width))

    label = str(text)
    text_surface = _render_text(font, label, fill)
    rect = text_surface.get_rect()
    setattr(rect, anchor, position)

    if outline_width and label and text_surface.get_width() and text_surface.get_height():
        outline_surface = _render_text(font, label, edge)
        for dy in range(-outline_width, outline_width + 1):
            for dx in range(-outline_width, outline_width + 1):
                if dx == 0 and dy == 0:
                    continue
                surface.blit(outline_surface, (rect.x + dx, rect.y + dy))

    surface.blit(text_surface, rect.topleft)
    return rect


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect | tuple[int, int, int, int],
    *,
    palette: MenuPalette = DEFAULT_PALETTE,
    alpha: int = PANEL_BG[3],
    radius: int | None = None,
    border: bool = True,
    accent: bool = True,
    accent_width: int = 4,
    shadow: bool = True,
    shadow_offset: int = 4,
) -> pygame.Rect:
    """Draw the canonical menu panel: drop shadow, fill, border, accent tab.

    Returns the panel rect for convenience (e.g. to place child widgets).
    """
    panel_rect = pygame.Rect(rect)
    if panel_rect.width <= 0 or panel_rect.height <= 0:
        return panel_rect

    corner = DEFAULT_SPACING.radius if radius is None else max(0, int(radius))
    alpha = max(0, min(255, int(alpha)))

    if shadow and shadow_offset > 0:
        shadow_surface = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            shadow_surface,
            clamp_color(palette.shadow),
            shadow_surface.get_rect(),
            border_radius=corner,
        )
        surface.blit(shadow_surface, (panel_rect.x + shadow_offset, panel_rect.y + shadow_offset))

    fill = clamp_color(tuple(palette.panel_bg[:3]) + (alpha,))
    panel_surface = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel_surface, fill, panel_surface.get_rect(), border_radius=corner)
    surface.blit(panel_surface, panel_rect.topleft)

    if border:
        pygame.draw.rect(surface, clamp_color(palette.border), panel_rect, 2, border_radius=corner)
    if accent and accent_width > 0:
        stripe = pygame.Rect(panel_rect.x, panel_rect.y, min(accent_width, panel_rect.width), panel_rect.height)
        pygame.draw.rect(surface, clamp_color(palette.accent), stripe, border_radius=corner)

    return panel_rect


def draw_row(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    selected: bool = False,
    palette: MenuPalette = DEFAULT_PALETTE,
    radius: int | None = None,
) -> pygame.Rect:
    """Draw a menu row/list item using the shared active/idle colours."""
    row_rect = pygame.Rect(rect)
    corner = DEFAULT_SPACING.radius if radius is None else max(0, int(radius))
    if row_rect.width <= 0 or row_rect.height <= 0:
        return row_rect
    pygame.draw.rect(
        surface,
        clamp_color(palette.row_active if selected else palette.row_idle),
        row_rect,
        border_radius=corner,
    )
    pygame.draw.rect(
        surface,
        clamp_color(palette.accent if selected else palette.border),
        row_rect,
        2 if selected else 1,
        border_radius=corner,
    )
    return row_rect


def draw_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font: pygame.font.Font,
    *,
    hovered: bool = False,
    selected: bool = False,
    palette: MenuPalette = DEFAULT_PALETTE,
    radius: int | None = None,
) -> pygame.Rect:
    """Draw a labelled button using the shared button palette."""
    button_rect = pygame.Rect(rect)
    corner = DEFAULT_SPACING.radius if radius is None else max(0, int(radius))
    if button_rect.width <= 0 or button_rect.height <= 0:
        return button_rect
    background = palette.button_hover if (hovered or selected) else palette.button
    pygame.draw.rect(surface, clamp_color(background), button_rect, border_radius=corner)
    rendered = _render_text(font, str(label), clamp_color(palette.text))
    surface.blit(rendered, rendered.get_rect(center=button_rect.center))
    return button_rect


def centered_panel_rect(
    surface_size: tuple[int, int],
    size: tuple[int, int],
) -> pygame.Rect:
    """Return ``size`` centred inside ``surface_size``."""
    width, height = surface_size
    panel_width, panel_height = size
    return pygame.Rect((width - panel_width) // 2, (height - panel_height) // 2, panel_width, panel_height)


def stacked_row_rects(
    surface_size: tuple[int, int],
    count: int,
    *,
    spacing: MenuSpacing = DEFAULT_SPACING,
    top: int | None = None,
) -> tuple[pygame.Rect, ...]:
    """Return ``count`` equally sized rows with shared margins and gaps.

    When ``top`` is omitted the stack is vertically centred in the surface.
    """
    count = max(0, int(count))
    if not count:
        return ()
    width = max(1, surface_size[0] - 2 * spacing.margin)
    total_height = count * spacing.row_height + (count - 1) * spacing.row_gap
    first_top = max(0, (surface_size[1] - total_height) // 2) if top is None else max(0, int(top))
    return tuple(
        pygame.Rect(
            spacing.margin,
            first_top + index * (spacing.row_height + spacing.row_gap),
            width,
            spacing.row_height,
        )
        for index in range(count)
    )
