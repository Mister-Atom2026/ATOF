"""Reusable UI-polish primitives for ATOF.

Inspired by the GTA V/VI, RDR1/2 and Mafia: The Old Country research in
``docs/ui_research_*.md`` and by ``docs/ui_best_practices_atof.md``:

* one semantic token table (colors / spacing / motion / typography);
* one shape-coded marker language shared by the full map, the radar overlay
  and the map legend (never color alone);
* a compact *single active objective* HUD chip with a short change pulse;
* a map legend built from the very same glyphs as the map markers;
* a shared glass-panel / menu-header primitive for storage, garage and phone.

Deliberately out of scope (owned by other agents): ``draw_gta_minimap``,
``draw_interaction_prompt``, the wanted system and traffic/car physics.
"""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Iterable, Mapping, Sequence

import pygame


# ---------------------------------------------------------------------------
# Design tokens — single source of truth for the polished UI layer
# ---------------------------------------------------------------------------

UI_TOKENS: dict[str, object] = {
    "accent": (212, 91, 18),
    "accent_soft": (255, 170, 90),
    "panel_bg": (16, 22, 30, 215),
    "panel_rim": (120, 145, 175, 120),
    "panel_rim_inner": (255, 255, 255, 35),
    "text": (240, 244, 248),
    "text_muted": (170, 180, 192),
    "text_dim": (120, 130, 142),
    "success": (80, 220, 140),
    "warning": (255, 190, 80),
    "danger": (255, 100, 90),
    "radius": 12,
    "padding_x": 14,
    "padding_y": 11,
    "row_height": 26,
    "pulse_seconds": 0.35,  # GTA/RDR-style short state-change acknowledgement
    "fade_seconds": 0.18,
}


def color(name: str, fallback=(212, 91, 18)):
    """Return a semantic color token."""
    value = UI_TOKENS.get(name, fallback)
    return tuple(value) if isinstance(value, (tuple, list)) else fallback


def token(name: str, fallback=None):
    return UI_TOKENS.get(name, fallback)


# kind -> silhouette + semantic color + localization fallback.
# Shape is the primary signal; color only reinforces it (accessibility).
MARKER_STYLES: dict[str, dict] = {
    "player": {
        "shape": "triangle",
        "color": (235, 75, 65),
        "label_key": "map_marker_player",
        "label_default": "You",
    },
    "home": {
        "shape": "house",
        "color": (75, 135, 230),
        "label_key": "map_marker_home",
        "label_default": "Home",
    },
    "gunshop": {
        "shape": "cross",
        "color": (70, 180, 255),
        "label_key": "map_marker_gunshop",
        "label_default": "Gun shop",
    },
    "garage": {
        "shape": "garage",
        "color": (220, 150, 55),
        "label_key": "map_marker_garage",
        "label_default": "Garage",
    },
    "objective": {
        "shape": "diamond",
        "color": (255, 112, 0),
        "label_key": "map_marker_objective",
        "label_default": "Objective",
    },
    "destination": {
        "shape": "ring",
        "color": (255, 190, 70),
        "label_key": "map_marker_destination",
        "label_default": "Destination",
    },
    "ally": {
        "shape": "plus",
        "color": (95, 215, 150),
        "label_key": "map_marker_ally",
        "label_default": "Ally",
    },
    "enemy": {
        "shape": "crossed",
        "color": (230, 85, 80),
        "label_key": "map_marker_enemy",
        "label_default": "Threat",
    },
    "pickup": {
        "shape": "dot",
        "color": (200, 190, 255),
        "label_key": "map_marker_pickup",
        "label_default": "Pickup",
    },
}

MAP_LEGEND_KINDS: tuple[str, ...] = (
    "player",
    "home",
    "gunshop",
    "garage",
    "objective",
    "destination",
)


@lru_cache(maxsize=64)
def _ui_font(size: int, weight: str = "regular"):
    """Prefer the engine's cached Inter font, fall back to pygame default."""
    try:
        import engine as _engine

        getter = getattr(_engine, "_cached_ui_font", None)
        if callable(getter):
            return getter(None, size, weight=weight)
    except Exception:
        pass
    return pygame.font.Font(None, size)


def tr(labels: Mapping[str, str] | None, key: str, default: str) -> str:
    value = (labels or {}).get(key)
    return value if isinstance(value, str) and value else default


def _ellipsize(font, text: str, max_width: int) -> str:
    if max_width <= 0 or font.size(text)[0] <= max_width:
        return text
    ellipsis = "…"
    cut = text
    while cut and font.size(cut + ellipsis)[0] > max_width:
        cut = cut[:-1]
    return (cut + ellipsis).strip()


# ---------------------------------------------------------------------------
# Panel / menu primitives
# ---------------------------------------------------------------------------

@lru_cache(maxsize=64)
def _panel_surface(width: int, height: int, accent, alpha: int, radius: int):
    """Cached frosted-look panel; callers only blit it, never mutate it."""
    panel = pygame.Surface((max(1, width), max(1, height)), pygame.SRCALPHA)
    panel.fill((*UI_TOKENS["panel_bg"][:3], alpha))
    sheen = pygame.Surface(panel.get_size(), pygame.SRCALPHA)
    # BLEND_RGBA_ADD adds raw channel values, so keep RGB low: a subtle
    # top-left sheen, never a bright blob that hurts text contrast.
    pygame.draw.ellipse(
        sheen,
        (26, 30, 38, 22),
        (-panel.get_width() * 0.15, -panel.get_height() * 0.55,
         panel.get_width() * 0.9, panel.get_height()),
    )
    panel.blit(sheen, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    accent_bar = pygame.Rect(0, 8, 3, max(12, panel.get_height() - 16))
    pygame.draw.rect(panel, (*accent, 235), accent_bar, border_radius=radius)
    return panel


def draw_glass_panel(surface: pygame.Surface, rect: pygame.Rect, *,
                     accent=None, radius: int | None = None, alpha: int = 215) -> None:
    """One reusable glass-panel renderer for chips, legends and menus."""
    accent = tuple(accent or color("accent"))
    radius = int(token("radius", 12) if radius is None else radius)
    panel = _panel_surface(rect.width, rect.height, accent, alpha, radius)
    surface.blit(panel, rect.topleft)
    pygame.draw.rect(surface, token("panel_rim"), rect, 1, border_radius=radius)
    pygame.draw.rect(surface, token("panel_rim_inner"), rect.inflate(-2, -2), 1,
                     border_radius=max(0, radius - 1))


def draw_accent_rule(surface: pygame.Surface, x: int, y: int, width: int, *,
                     accent=None, height: int = 3) -> pygame.Rect:
    """Shared accent underline for menu titles (storage / garage / phone)."""
    accent = tuple(accent or color("accent"))
    rect = pygame.Rect(int(x), int(y), max(24, int(width)), max(1, int(height)))
    pygame.draw.rect(surface, accent, rect, border_radius=2)
    return rect


def draw_menu_header(surface: pygame.Surface, topleft: tuple[int, int], title: str, *,
                     font=None, kicker: str | None = None, width: int | None = None,
                     accent=None) -> pygame.Rect:
    """Shared title treatment (title + optional kicker + accent rule).

    Returns the bounding rect of the header so callers can lay out rows below.
    """
    accent = tuple(accent or color("accent"))
    title_font = font or _ui_font(28, "semibold")
    tx, ty = int(topleft[0]), int(topleft[1])
    kicker_font = _ui_font(12, "regular")
    kicker_s = kicker_font.render(kicker.upper(), True, color("text_muted")) if kicker else None
    title_y = ty + (kicker_s.get_height() + 3 if kicker_s is not None else 0)
    title_s = title_font.render(title, True, color("text"))
    if kicker_s is not None:
        surface.blit(kicker_s, (tx, ty))
    surface.blit(title_s, (tx, title_y))
    rule_y = title_y + title_s.get_height() + 5
    rule_w = width if width is not None else min(360, max(90, title_s.get_width() + 8))
    rule = draw_accent_rule(surface, tx, rule_y, rule_w, accent=accent)
    bottom = rule.bottom
    return pygame.Rect(tx, ty, rule.width, bottom - ty)


# ---------------------------------------------------------------------------
# Unified marker silhouettes (map, radar overlay and legend share these)
# ---------------------------------------------------------------------------

def draw_marker_glyph(surface: pygame.Surface, center: tuple[int, int], kind: str = "objective", *,
                      radius: int = 9, selected: bool = False, color_override=None) -> None:
    """Draw a shape-coded marker. Color is secondary; shape carries the meaning."""
    style = MARKER_STYLES.get(kind, MARKER_STYLES["objective"])
    cx, cy = int(center[0]), int(center[1])
    r = max(4, int(radius))
    fill = tuple(color_override) if color_override else style["color"]
    edge = (255, 228, 140) if selected else (255, 255, 255)
    lw = 2 if selected else 1
    shape = style["shape"]

    # Contrast halo so markers stay readable over roads/buildings/minimap glass.
    pygame.draw.circle(surface, (12, 16, 22), center, r + 3)

    if shape == "triangle":  # player
        pts = [(cx, cy - r - 1), (cx - r, cy + r), (cx + r, cy + r)]
        pygame.draw.polygon(surface, fill, pts)
        pygame.draw.polygon(surface, edge, pts, lw)
    elif shape == "house":  # home
        box = pygame.Rect(cx - r, cy - r // 2, 2 * r, r + r // 2)
        pygame.draw.rect(surface, fill, box)
        pygame.draw.rect(surface, edge, box, lw)
        roof = [(cx - r - 2, cy - r // 2), (cx, cy - r - 2), (cx + r + 2, cy - r // 2)]
        pygame.draw.polygon(surface, fill, roof)
        pygame.draw.polygon(surface, edge, roof, lw)
    elif shape == "cross":  # gun shop: round badge with a plus
        pygame.draw.circle(surface, fill, center, r)
        pygame.draw.circle(surface, edge, center, r, lw)
        arm = max(2, r // 2)
        pygame.draw.rect(surface, edge, (cx - arm, cy - 1, arm * 2, 2))
        pygame.draw.rect(surface, edge, (cx - 1, cy - arm, 2, arm * 2))
    elif shape == "garage":  # square bay with a shutter strip
        box = pygame.Rect(cx - r, cy - r, 2 * r, 2 * r)
        pygame.draw.rect(surface, fill, box, border_radius=3)
        pygame.draw.rect(surface, edge, box, lw, border_radius=3)
        pygame.draw.rect(surface, edge, (cx - r + 3, cy + r // 3, 2 * r - 6, 2))
    elif shape == "diamond":  # objective / mission
        pts = [(cx, cy - r - 1), (cx + r + 1, cy), (cx, cy + r + 1), (cx - r - 1, cy)]
        pygame.draw.polygon(surface, fill, pts)
        pygame.draw.polygon(surface, edge, pts, lw)
        pygame.draw.circle(surface, edge, center, max(2, r // 3))
    elif shape == "ring":  # custom GPS destination
        pygame.draw.circle(surface, fill, center, r, lw + 1)
        pygame.draw.circle(surface, edge, center, max(2, r // 3))
    elif shape == "plus":  # ally
        pygame.draw.circle(surface, fill, center, r)
        pygame.draw.circle(surface, edge, center, r, lw)
        pygame.draw.rect(surface, edge, (cx - max(1, r // 3), cy - r + 3, max(2, 2 * r // 3), 2 * r - 6))
        pygame.draw.rect(surface, edge, (cx - r + 3, cy - max(1, r // 3), 2 * r - 6, max(2, 2 * r // 3)))
    elif shape == "crossed":  # threat / enemy
        pts = [(cx, cy - r - 1), (cx + r + 1, cy), (cx, cy + r + 1), (cx - r - 1, cy)]
        pygame.draw.polygon(surface, fill, pts)
        pygame.draw.polygon(surface, edge, pts, lw)
        d = max(2, r // 2)
        pygame.draw.line(surface, edge, (cx - d, cy - d), (cx + d, cy + d), lw)
        pygame.draw.line(surface, edge, (cx + d, cy - d), (cx - d, cy + d), lw)
    else:  # dot / pickup / custom
        pygame.draw.circle(surface, fill, center, r)
        pygame.draw.circle(surface, edge, center, r, lw)
        pygame.draw.circle(surface, edge, center, max(2, r // 3))


# ---------------------------------------------------------------------------
# Compact objective HUD chip (one active goal + distance)
# ---------------------------------------------------------------------------

class ObjectiveChip:
    """Glanceable single-objective chip with a short acknowledgement pulse.

    The journal keeps the full objective list; the HUD only promises the next
    thing to do. ``observe`` is dt-free (wall clock), so it works both in the
    main loop and in blocking menu loops.
    """

    def __init__(self, *, margin: int = 20, top: int = 88,
                 pulse_seconds: float | None = None, reduced_motion: bool = False):
        self.margin = margin
        self.top = top
        self.pulse_seconds = float(
            pulse_seconds if pulse_seconds is not None else token("pulse_seconds", 0.35)
        )
        self.reduced_motion = reduced_motion
        self._last_id: str | None = None
        self._changed_at: float | None = None

    def observe(self, objective_id: str | None) -> bool:
        """Record an objective id; return True on a genuine change."""
        changed = bool(objective_id) and objective_id != self._last_id
        if changed:
            self._last_id = objective_id
            self._changed_at = time.perf_counter()
        return changed

    @property
    def pulse(self) -> float:
        if self.reduced_motion or self._changed_at is None or self.pulse_seconds <= 0:
            return 0.0
        elapsed = time.perf_counter() - self._changed_at
        return max(0.0, 1.0 - elapsed / self.pulse_seconds)

    def draw(self, surface: pygame.Surface, text: str, distance: str | None = None, *,
             labels: Mapping[str, str] | None = None, top: int | None = None) -> pygame.Rect | None:
        title = tr(labels, "story_objective_now", "CURRENT OBJECTIVE")
        if not text:
            return None
        kicker_font = _ui_font(12)
        text_font = _ui_font(19, "semibold")
        dist_font = _ui_font(16, "medium")
        kicker_s = kicker_font.render(title.upper(), True, color("text_muted"))
        dist_s = dist_font.render(distance, True, color("warning")) if distance else None

        pad_x, pad_y = token("padding_x", 14), token("padding_y", 11)
        glyph_r = 9
        text_x = pad_x + glyph_r * 2 + 10
        max_text = 300 - (dist_s.get_width() + 12 if dist_s else 0)
        text_s = text_font.render(_ellipsize(text_font, text, max_text), True, color("text"))
        width = max(210, min(420, text_x + text_s.get_width() + pad_x + (dist_s.get_width() + 12 if dist_s else 0)))
        height = pad_y * 2 + kicker_s.get_height() + 3 + text_s.get_height() + 6
        y = self.top if top is None else top
        rect = pygame.Rect(self.margin, y, width, height)

        draw_glass_panel(surface, rect)
        pulse = self.pulse
        if pulse > 0:
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            alpha = int(46 * pulse)
            pygame.draw.rect(glow, (*color("warning"), alpha), glow.get_rect(),
                             border_radius=int(token("radius", 12)))
            surface.blit(glow, rect.topleft)

        surface.blit(kicker_s, (rect.x + pad_x, rect.y + pad_y))
        draw_marker_glyph(surface, (rect.x + pad_x + glyph_r, rect.y + pad_y + kicker_s.get_height() + 3 + text_s.get_height() // 2 + 4),
                          "objective", radius=glyph_r)
        ty = rect.y + pad_y + kicker_s.get_height() + 3
        surface.blit(text_s, (rect.x + text_x, ty))
        if dist_s is not None:
            surface.blit(dist_s, (rect.right - pad_x - dist_s.get_width(), ty + 1))
        return rect


# ---------------------------------------------------------------------------
# Full-map legend — uses exactly the same glyphs as the markers
# ---------------------------------------------------------------------------

def draw_map_legend(surface: pygame.Surface, labels: Mapping[str, str] | None = None, *,
                    kinds: Sequence[str] = MAP_LEGEND_KINDS, anchor: str = "bottom_left",
                    margin: int = 20, visible: bool = True) -> pygame.Rect | None:
    """Legend panel for the full-screen map. Returns its rect (or None)."""
    if not visible or not kinds:
        return None
    header_font = _ui_font(16, "semibold")
    row_font = _ui_font(15)
    header = tr(labels, "map_legend", "MAP LEGEND")
    header_s = header_font.render(header.upper(), True, color("text"))
    rows = []
    widest = header_s.get_width()
    for kind in kinds:
        style = MARKER_STYLES.get(kind)
        if style is None:
            continue
        caption = tr(labels, style["label_key"], style["label_default"])
        rows.append((kind, row_font.render(caption, True, color("text"))))
        widest = max(widest, rows[-1][1].get_width())

    pad_x, pad_y = token("padding_x", 14), token("padding_y", 11)
    row_h = token("row_height", 26)
    width = min(340, max(190, widest + pad_x * 2 + 34))
    height = pad_y * 2 + header_s.get_height() + 6 + len(rows) * row_h
    sw, sh = surface.get_size()
    if anchor == "top_right":
        x = sw - margin - width
        y = margin
    elif anchor == "bottom_right":
        x = sw - margin - width
        y = sh - margin - height
    else:
        x = margin
        y = sh - margin - height
    rect = pygame.Rect(x, max(0, y), width, height)
    draw_glass_panel(surface, rect, radius=10)
    surface.blit(header_s, (rect.x + pad_x, rect.y + pad_y))
    cy = rect.y + pad_y + header_s.get_height() + 8
    for idx, (kind, label_s) in enumerate(rows):
        line_y = cy + idx * row_h
        draw_marker_glyph(surface, (rect.x + pad_x + 9, line_y + row_h // 2 - 1),
                          kind, radius=7)
        surface.blit(label_s, (rect.x + pad_x + 28, line_y + 3))
    return rect
