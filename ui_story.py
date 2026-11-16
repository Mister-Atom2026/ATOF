"""Reusable story/mission UI scaffolding for ATOF.

This module is intentionally engine-light: it provides data containers and draw
helpers that can be called from the existing HUD/map render paths with minimal
integration. All user-facing strings are expected to be supplied through label
dictionaries / translation keys so text stays localizable.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping, MutableSequence, Sequence

import pygame

import engine_ui_polish as _ui_polish


# Suggested translation keys (add to language tables when integrating).
STORY_UI_KEYS = (
    "story_objectives",
    "story_journal",
    "story_no_objectives",
    "story_objective_active",
    "story_objective_completed",
    "story_objective_failed",
    "story_distance",
    "story_continue",
    "story_objective_now",
    "story_objective_updated",
    "map_legend",
    "map_marker_player",
    "map_marker_home",
    "map_marker_gunshop",
    "map_marker_garage",
    "map_marker_objective",
    "map_marker_destination",
)


def tr(labels: Mapping[str, str] | None, key: str, default: str, **fmt) -> str:
    """Resolve a translation key with a safe fallback."""
    text = default
    if labels and key in labels:
        value = labels[key]
        if isinstance(value, str):
            text = value
    try:
        return text.format(**fmt) if fmt else text
    except Exception:
        return text


def _font(size: int = 22, *, weight: str = "regular", bold: bool = False):
    """Best-effort font loader; prefers cached engine fonts when available."""
    try:
        import engine as _engine  # local import avoids hard dependency at import time

        getter = getattr(_engine, "_cached_ui_font", None)
        if callable(getter):
            return getter(None, size, bold=bold, weight=weight)
    except Exception:
        pass
    font = pygame.font.Font(None, size)
    if bold:
        font.set_bold(True)
    return font


def _draw_glass_panel(surface: pygame.Surface, rect: pygame.Rect, *, accent=(212, 91, 18),
                      radius: int = 12, alpha: int = 210) -> None:
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((16, 22, 30, alpha))
    # soft top sheen
    sheen = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.ellipse(
        sheen,
        (255, 255, 255, 22),
        (-rect.width * 0.15, -rect.height * 0.55, rect.width * 0.9, rect.height),
    )
    panel.blit(sheen, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    surface.blit(panel, rect.topleft)
    pygame.draw.rect(surface, (120, 145, 175, 120), rect, 1, border_radius=radius)
    pygame.draw.rect(surface, (255, 255, 255, 35), rect.inflate(-2, -2), 1, border_radius=max(0, radius - 1))
    pygame.draw.rect(surface, accent, (rect.x, rect.y + 8, 3, max(12, rect.height - 16)), border_radius=radius)


# ---------------------------------------------------------------------------
# Objective / quest tracker
# ---------------------------------------------------------------------------

@dataclass
class Objective:
    id: str
    title_key: str
    title_default: str = ""
    description_key: str | None = None
    description_default: str = ""
    completed: bool = False
    failed: bool = False
    optional: bool = False
    progress: float | None = None  # 0..1
    target_position: tuple[float, float] | None = None  # world coords for marker/GPS
    marker_label: str = ""
    hidden: bool = False

    @property
    def active(self) -> bool:
        return not (self.completed or self.failed or self.hidden)


@dataclass
class QuestState:
    quest_id: str = ""
    title_key: str = ""
    title_default: str = ""
    objectives: list[Objective] = field(default_factory=list)

    def active_objectives(self) -> list[Objective]:
        return [o for o in self.objectives if o.active]

    def primary_objective(self) -> Objective | None:
        for obj in self.objectives:
            if obj.active and not obj.optional:
                return obj
        active = self.active_objectives()
        return active[0] if active else None


class ObjectiveTrackerHUD:
    """Compact on-screen tracker for current quest objectives."""

    def __init__(self, *, max_visible: int = 3):
        self.max_visible = max_visible

    def draw(self, screen: pygame.Surface, quest: QuestState | None,
             labels: Mapping[str, str] | None = None,
             *, anchor: str = "top_left", margin: int = 20) -> pygame.Rect | None:
        if quest is None:
            return None
        visible = [o for o in quest.objectives if not o.hidden][: self.max_visible]
        if not visible:
            return None

        title_font = _font(20, weight="semibold", bold=True)
        item_font = _font(18, weight="medium")
        small_font = _font(16)

        header = tr(labels, quest.title_key or "story_objectives", quest.title_default or tr(labels, "story_objectives", "Objectives"))
        lines = []
        for obj in visible:
            prefix = "✓" if obj.completed else "✗" if obj.failed else "•"
            text = tr(labels, obj.title_key, obj.title_default or obj.id)
            if obj.progress is not None and obj.active:
                pct = max(0, min(100, round(obj.progress * 100)))
                text = f"{text} ({pct}%)"
            lines.append((prefix, text, obj))

        padding_x, padding_y = 14, 12
        header_s = title_font.render(header, True, (245, 236, 220))
        width = header_s.get_width()
        rendered = []
        for prefix, text, obj in lines:
            p_s = item_font.render(prefix, True, (212, 91, 18) if obj.active else (150, 150, 150))
            t_s = item_font.render(text, True, (240, 244, 248) if obj.active else (170, 170, 170))
            rendered.append((p_s, t_s, obj))
            width = max(width, p_s.get_width() + 8 + t_s.get_width())
        width = min(max(220, width + padding_x * 2), 420)
        line_h = 24
        height = padding_y * 2 + header_s.get_height() + 6 + len(rendered) * line_h

        sw, sh = screen.get_size()
        if anchor == "top_right":
            x = sw - margin - width
            y = margin + 70
        else:
            x = margin
            y = margin + 120  # below common debug/status stacks; caller can override by blitting differently
        rect = pygame.Rect(x, y, width, height)
        _draw_glass_panel(screen, rect)

        cy = rect.y + padding_y
        screen.blit(header_s, (rect.x + padding_x, cy))
        cy += header_s.get_height() + 6
        for p_s, t_s, obj in rendered:
            screen.blit(p_s, (rect.x + padding_x, cy))
            color = (240, 244, 248)
            if obj.completed:
                color = (140, 220, 150)
            elif obj.failed:
                color = (230, 120, 110)
            elif obj.optional:
                color = (210, 210, 220)
            # re-render with semantic color if needed
            if t_s.get_at((min(1, t_s.get_width()-1), min(1, t_s.get_height()-1)))[:3] != color[:3]:
                t_s = item_font.render(t_s and tr(labels, obj.title_key, obj.title_default or obj.id) + ("" if obj.progress is None or not obj.active else f" ({max(0,min(100,round(obj.progress*100)))}%)"), True, color)
            screen.blit(t_s, (rect.x + padding_x + p_s.get_width() + 8, cy))
            cy += line_h
        return rect


# ---------------------------------------------------------------------------
# Journal / objectives view hook
# ---------------------------------------------------------------------------

def draw_objectives_journal(screen: pygame.Surface, quest: QuestState | None,
                            labels: Mapping[str, str] | None = None,
                            *, selected_index: int = 0) -> pygame.Rect:
    """Draw a simple centered journal/objectives overlay. Returns panel rect.

    Hook this from a phone app, pause/menu page, or dedicated keybinding.
    Caller owns input/navigation state (selected_index, open/close).
    """
    sw, sh = screen.get_size()
    panel = pygame.Rect(0, 0, min(720, sw - 80), min(460, sh - 80))
    panel.center = (sw // 2, sh // 2)

    dim = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 140))
    screen.blit(dim, (0, 0))
    _draw_glass_panel(screen, panel, radius=16, alpha=235)

    title_font = _font(34, weight="bold", bold=True)
    item_font = _font(24, weight="medium")
    desc_font = _font(20)
    hint_font = _font(18)

    title = tr(labels, "story_journal", "Journal")
    screen.blit(title_font.render(title, True, (245, 230, 200)), (panel.x + 24, panel.y + 18))
    pygame.draw.line(screen, (90, 75, 60), (panel.x + 20, panel.y + 62), (panel.right - 20, panel.y + 62), 1)

    objectives = quest.objectives if quest else []
    if not objectives:
        empty = tr(labels, "story_no_objectives", "No active objectives.")
        s = item_font.render(empty, True, (190, 190, 190))
        screen.blit(s, s.get_rect(center=panel.center))
    else:
        list_rect = pygame.Rect(panel.x + 20, panel.y + 76, panel.width * 0.52, panel.height - 120)
        detail_rect = pygame.Rect(list_rect.right + 16, panel.y + 76, panel.right - list_rect.right - 36, panel.height - 120)
        selected_index = max(0, min(selected_index, len(objectives) - 1))
        row_h = 42
        for i, obj in enumerate(objectives):
            row = pygame.Rect(list_rect.x, list_rect.y + i * row_h, list_rect.width, row_h - 4)
            if i == selected_index:
                pygame.draw.rect(screen, (212, 91, 18), row, border_radius=8)
                fg = (20, 15, 10)
            else:
                fg = (235, 235, 235) if obj.active else (150, 150, 150)
            status = "[x]" if obj.completed else "[!]" if obj.failed else "[ ]"
            name = tr(labels, obj.title_key, obj.title_default or obj.id)
            txt = item_font.render(f"{status} {name}", True, fg)
            screen.blit(txt, (row.x + 10, row.y + 6))

        sel = objectives[selected_index]
        name = tr(labels, sel.title_key, sel.title_default or sel.id)
        desc = tr(labels, sel.description_key or "", sel.description_default or "")
        status_key = "story_objective_completed" if sel.completed else "story_objective_failed" if sel.failed else "story_objective_active"
        status_default = "Completed" if sel.completed else "Failed" if sel.failed else "In progress"
        lines = [name, tr(labels, status_key, status_default), "", desc]
        y = detail_rect.y
        for li, line in enumerate(lines):
            if not line and li != 2:
                continue
            font = item_font if li == 0 else desc_font
            color = (245, 220, 180) if li == 0 else (220, 220, 220)
            # simple wrap
            words = line.split(" ") if line else [""]
            cur = ""
            for w in words:
                test = (cur + " " + w).strip()
                if font.size(test)[0] > detail_rect.width and cur:
                    screen.blit(font.render(cur, True, color), (detail_rect.x, y))
                    y += font.get_height() + 4
                    cur = w
                else:
                    cur = test
            if cur or line == "":
                screen.blit(font.render(cur, True, color), (detail_rect.x, y))
                y += font.get_height() + 6
            if li == 2:
                y += 2

    hint = hint_font.render(tr(labels, "story_continue", "Esc/Back: close"), True, (190, 190, 190))
    screen.blit(hint, (panel.centerx - hint.get_width() // 2, panel.bottom - 30))
    return panel


# ---------------------------------------------------------------------------
# Notifications / toasts
# ---------------------------------------------------------------------------

@dataclass
class Toast:
    message_key: str
    message_default: str = ""
    duration: float = 2.5
    created_at: float = field(default_factory=time.perf_counter)
    kind: str = "info"  # info|success|warning|error
    payload: dict = field(default_factory=dict)

    @property
    def age(self) -> float:
        return time.perf_counter() - self.created_at

    @property
    def alive(self) -> bool:
        return self.age < self.duration


class ToastManager:
    def __init__(self, *, max_visible: int = 4):
        self.toasts: list[Toast] = []
        self.max_visible = max_visible

    def push(self, message_key: str, default: str = "", *, duration: float = 2.5,
             kind: str = "info", **payload) -> Toast:
        toast = Toast(message_key=message_key, message_default=default, duration=duration,
                      kind=kind, payload=payload)
        self.toasts.append(toast)
        return toast

    def clear(self) -> None:
        self.toasts.clear()

    def update(self) -> None:
        self.toasts = [t for t in self.toasts if t.alive]

    def draw(self, screen: pygame.Surface, labels: Mapping[str, str] | None = None,
             *, anchor: str = "top_center") -> None:
        self.update()
        if not self.toasts:
            return
        visible = self.toasts[-self.max_visible:]
        font = _font(22, weight="medium")
        sw, _ = screen.get_size()
        y = 24
        for toast in reversed(visible):
            text = tr(labels, toast.message_key, toast.message_default or toast.message_key, **toast.payload)
            ts = font.render(text, True, (245, 248, 252))
            pad_x, pad_y = 16, 10
            rect = pygame.Rect(0, 0, ts.get_width() + pad_x * 2, ts.get_height() + pad_y * 2)
            if anchor == "top_left":
                rect.topleft = (20, y)
            elif anchor == "top_right":
                rect.topright = (sw - 20, y)
            else:
                rect.midtop = (sw // 2, y)
            # fade in/out
            remaining = toast.duration - toast.age
            alpha = 230
            if toast.age < 0.18:
                alpha = int(230 * (toast.age / 0.18))
            elif remaining < 0.25:
                alpha = int(230 * max(0.0, remaining / 0.25))
            accent = {
                "success": (80, 220, 140),
                "warning": (255, 190, 80),
                "error": (255, 100, 90),
            }.get(toast.kind, (212, 91, 18))
            surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            surf.fill((18, 22, 30, alpha))
            pygame.draw.rect(surf, (120, 145, 175, min(140, alpha)), surf.get_rect(), 1, border_radius=10)
            pygame.draw.rect(surf, (*accent, min(255, alpha)), (0, 0, 3, rect.height), border_radius=10)
            surf.blit(ts, (pad_x, pad_y))
            screen.blit(surf, rect.topleft)
            y += rect.height + 8


# ---------------------------------------------------------------------------
# Dialogue / subtitles
# ---------------------------------------------------------------------------

@dataclass
class DialogueLine:
    text_key: str
    text_default: str = ""
    speaker_key: str | None = None
    speaker_default: str = ""
    duration: float = 3.0
    payload: dict = field(default_factory=dict)


class DialogueSubtitlePresenter:
    """Simple queue-based subtitle/dialogue presenter.

    Integration: call `update(dt_seconds)` each frame and `draw(screen, labels)`
    in UI layer. Push lines from mission scripts/cutscene logic.
    """

    def __init__(self):
        self.queue: list[DialogueLine] = []
        self.current: DialogueLine | None = None
        self._remaining: float = 0.0

    def push(self, line: DialogueLine) -> None:
        self.queue.append(line)

    def say(self, text_key: str, default: str = "", *, speaker_key: str | None = None,
            speaker_default: str = "", duration: float = 3.0, **payload) -> None:
        self.push(DialogueLine(text_key=text_key, text_default=default,
                               speaker_key=speaker_key, speaker_default=speaker_default,
                               duration=duration, payload=payload))

    def clear(self) -> None:
        self.queue.clear()
        self.current = None
        self._remaining = 0.0

    def skip(self) -> None:
        self.current = None
        self._remaining = 0.0

    def update(self, dt_seconds: float) -> None:
        if self.current is None and self.queue:
            self.current = self.queue.pop(0)
            self._remaining = max(0.1, self.current.duration)
        if self.current is not None:
            self._remaining -= max(0.0, dt_seconds)
            if self._remaining <= 0:
                self.current = None

    @property
    def active(self) -> bool:
        return self.current is not None or bool(self.queue)

    def draw(self, screen: pygame.Surface, labels: Mapping[str, str] | None = None) -> pygame.Rect | None:
        if self.current is None:
            return None
        sw, sh = screen.get_size()
        speaker_font = _font(20, weight="semibold", bold=True)
        text_font = _font(24, weight="medium")

        speaker = ""
        if self.current.speaker_key or self.current.speaker_default:
            speaker = tr(labels, self.current.speaker_key or "", self.current.speaker_default)
        text = tr(labels, self.current.text_key, self.current.text_default, **self.current.payload)

        # word wrap
        max_w = min(900, sw - 120)
        words = text.split()
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if text_font.size(test)[0] > max_w - 36 and cur:
                lines.append(cur)
                cur = w
            else:
                cur = test
        if cur:
            lines.append(cur)
        if not lines:
            lines = [""]

        line_h = text_font.get_height() + 4
        box_h = 20 + (speaker_font.get_height() + 6 if speaker else 0) + len(lines) * line_h + 8
        box_w = min(max_w, max((text_font.size(ln)[0] for ln in lines), default=0) + 40)
        rect = pygame.Rect(0, 0, box_w, box_h)
        rect.midbottom = (sw // 2, sh - 40)
        _draw_glass_panel(screen, rect, radius=14, alpha=220)

        y = rect.y + 10
        if speaker:
            ss = speaker_font.render(speaker, True, (255, 200, 120))
            screen.blit(ss, (rect.x + 20, y))
            y += ss.get_height() + 4
        for ln in lines:
            ts = text_font.render(ln, True, (245, 248, 252))
            screen.blit(ts, (rect.x + 20, y))
            y += line_h
        # progress bar
        total = max(0.001, self.current.duration)
        progress = max(0.0, min(1.0, self._remaining / total))
        bar = pygame.Rect(rect.x + 16, rect.bottom - 8, rect.width - 32, 3)
        pygame.draw.rect(screen, (70, 80, 95), bar, border_radius=2)
        fill = bar.copy()
        fill.width = max(0, int(bar.width * progress))
        pygame.draw.rect(screen, (212, 91, 18), fill, border_radius=2)
        return rect


# ---------------------------------------------------------------------------
# Mission markers (minimap/full map) consistent with existing GPS marker style
# ---------------------------------------------------------------------------

@dataclass
class MissionMarker:
    id: str
    position: tuple[float, float]  # world coords
    label_key: str = ""
    label_default: str = ""
    color: tuple[int, int, int] = (255, 112, 0)
    kind: str = "objective"  # objective|destination|ally|enemy|pickup|custom
    active: bool = True
    show_on_minimap: bool = True
    show_on_full_map: bool = True
    radius: int = 9


def draw_marker_icon(surface: pygame.Surface, center: tuple[int, int], *,
                     color=None, radius=9, selected=False, kind: str | None = None) -> None:
    """Draw a marker with the shared shape-coded vocabulary.

    ``kind`` selects the silhouette (objective/destination/ally/...); ``color``
    only tints it. Falling back to the legacy circle keeps old callers working.
    """
    try:
        _ui_polish.draw_marker_glyph(
            surface, center, kind or "objective",
            radius=radius, selected=selected, color_override=color,
        )
        return
    except Exception:
        pass
    fill = tuple(color) if color else (255, 112, 0)
    pygame.draw.circle(surface, (15, 15, 15), center, radius + 3)
    pygame.draw.circle(surface, (255, 255, 255), center, radius + 1)
    pygame.draw.circle(surface, fill, center, radius)
    inner = (255, 255, 255) if not selected else (255, 230, 120)
    pygame.draw.circle(surface, inner, center, max(2, radius // 3))


def world_to_minimap_point(world_pos, player_pos, world_w, world_h,
                           map_scale_x, map_scale_y, map_origin_x, map_origin_y,
                           radar_size, radar_center, zoom_offset, *,
                           clamp_to_edge: bool = True):
    """Compute a point inside a radar/minimap using the same projection model
    as engine.draw_gta_minimap.

    zoom_offset = (ox, oy) offsets returned/applied by draw_gta_minimap logic.
    Returns ((x,y), on_edge).
    """
    ratio_x = map_scale_x / world_w
    ratio_y = map_scale_y / world_h
    ox, oy = zoom_offset
    px = world_pos[0] * ratio_x + ox
    py = world_pos[1] * ratio_y + oy
    point = pygame.Vector2(px, py)
    center = pygame.Vector2(radar_center)
    rel = point - center
    radius = radar_size / 2 - 14
    on_edge = rel.length_squared() > radius * radius
    if clamp_to_edge and on_edge:
        if rel.length_squared() == 0:
            rel = pygame.Vector2(1, 0)
        rel.scale_to_length(radius)
        point = center + rel
    return (round(point.x), round(point.y)), on_edge


def draw_mission_markers_minimap(screen: pygame.Surface, markers: Iterable[MissionMarker],
                                 *, player_world_pos, destination_world_pos=None,
                                 world_w: int, world_h: int, bg_img: pygame.Surface,
                                 radar_rect: pygame.Rect, zoom: float = 0.1,
                                 preserve_aspect: bool = False) -> None:
    """Draw mission markers onto the screen over the existing minimap area.

    This recomputes the minimap projection (same math as draw_gta_minimap) so it
    can be called as a non-invasive overlay hook after the radar is drawn.
    """
    size = radar_rect.width
    half = size // 2
    square_map_size = size / zoom
    if preserve_aspect:
        map_scale = min(square_map_size / bg_img.get_width(), square_map_size / bg_img.get_height())
        map_scale_x = bg_img.get_width() * map_scale
        map_scale_y = bg_img.get_height() * map_scale
        map_origin_x = (square_map_size - map_scale_x) / 2
        map_origin_y = (square_map_size - map_scale_y) / 2
    else:
        map_scale_x = map_scale_y = square_map_size
        map_origin_x = map_origin_y = 0
    ratio_x = map_scale_x / world_w
    ratio_y = map_scale_y / world_h

    def radar_axis_offset(position, ratio, origin, extent):
        if extent <= size:
            return half - extent / 2
        camera = max(half, min(origin + position * ratio, origin + extent - half))
        return half - camera + origin

    ox = radar_axis_offset(player_world_pos[0], ratio_x, map_origin_x, map_scale_x)
    oy = radar_axis_offset(player_world_pos[1], ratio_y, map_origin_y, map_scale_y)
    center = radar_rect.center

    # Clip drawing to radar circle
    clip_prev = screen.get_clip()
    # approximate clip with radar rect; icon draw is small so this is fine
    screen.set_clip(radar_rect.inflate(-8, -8))
    try:
        for marker in markers:
            if not marker.active or not marker.show_on_minimap:
                continue
            # skip duplicating primary GPS destination if same point passed separately
            if destination_world_pos is not None:
                dx = marker.position[0] - destination_world_pos[0]
                dy = marker.position[1] - destination_world_pos[1]
                if dx * dx + dy * dy < 4:
                    continue
            pos, _edge = world_to_minimap_point(
                marker.position, player_world_pos, world_w, world_h,
                map_scale_x, map_scale_y, map_origin_x, map_origin_y,
                size, center, (radar_rect.x + ox, radar_rect.y + oy),
                clamp_to_edge=True,
            )
            draw_marker_icon(screen, pos, color=marker.color, radius=marker.radius,
                             kind=getattr(marker, "kind", None), selected=bool(getattr(marker, "selected", False)))
    finally:
        screen.set_clip(clip_prev)


def draw_mission_markers_full_map(screen: pygame.Surface, markers: Iterable[MissionMarker],
                                  world_to_map: Callable[[float, float], tuple[int, int]],
                                  labels: Mapping[str, str] | None = None,
                                  *, map_zoom: float = 1.0) -> None:
    """Draw mission markers on the full-screen map.

    Pass the same `world_to_map(wx, wy) -> (mx, my)` function used by
    engine.full_screen_map for perfect alignment.
    """
    for marker in markers:
        if not marker.active or not marker.show_on_full_map:
            continue
        mx, my = world_to_map(*marker.position)
        radius = max(6, int(marker.radius * max(1.0, map_zoom * 0.8)))
        draw_marker_icon(screen, (mx, my), color=marker.color, radius=radius,
                         kind=getattr(marker, "kind", None), selected=bool(getattr(marker, "selected", False)))
        name = tr(labels, marker.label_key, marker.label_default or marker.id)
        if name:
            font = _font(max(14, int(14 * min(map_zoom, 2.0))))
            txt = font.render(name, True, (255, 255, 255))
            bg = pygame.Surface((txt.get_width() + 8, txt.get_height() + 4), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 150))
            screen.blit(bg, (mx + radius + 4, my - txt.get_height() // 2 - 2))
            screen.blit(txt, (mx + radius + 8, my - txt.get_height() // 2))
