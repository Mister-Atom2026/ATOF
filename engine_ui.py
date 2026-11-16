"""Reusable HUD/prompt/glass UI primitives for engine-side rendering."""

from __future__ import annotations

from functools import lru_cache

import pygame


@lru_cache(maxsize=64)
def get_glass_panel_surface(size: tuple[int, int], *, alpha: int = 205, radius: int = 12) -> pygame.Surface:
    """Return a cached glass panel surface for a given size/style bucket."""
    width, height = max(1, int(size[0])), max(1, int(size[1]))
    alpha = max(0, min(255, int(alpha)))
    radius = max(0, int(radius))

    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    panel.fill((16, 22, 30, alpha))
    sheen = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(
        sheen,
        (255, 255, 255, 22),
        (-width * 0.18, -height * 0.60, width * 0.85, height * 1.10),
    )
    pygame.draw.rect(
        sheen,
        (255, 255, 255, 10),
        (0, 0, width, max(1, height // 2)),
        border_radius=radius,
    )
    panel.blit(sheen, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return panel.copy()


def draw_glass_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    alpha: int = 205,
    radius: int = 12,
    border_color=(120, 145, 175, 120),
    inner_border_color=(255, 255, 255, 40),
    accent=(212, 91, 18),
    accent_width: int = 3,
) -> None:
    """Draw a reusable glass-style panel matching engine HUD prompt aesthetics."""
    panel = get_glass_panel_surface(rect.size, alpha=alpha, radius=radius)
    surface.blit(panel, rect.topleft)
    pygame.draw.rect(surface, border_color, rect, 1, border_radius=radius)
    pygame.draw.rect(
        surface,
        inner_border_color,
        rect.inflate(-2, -2),
        1,
        border_radius=max(0, radius - 1),
    )
    if accent_width > 0 and accent is not None:
        pygame.draw.rect(
            surface,
            accent,
            (rect.x, rect.y, accent_width, rect.height),
            border_radius=radius,
        )