"""Mission 01 — «Пробудження».

Self-contained story mission runner: house exploration, two scripted dialogues,
a real-coordinate walk near the house, a final dialogue and a completion card.
Portraits come from the supplied 128x128 emotion sets; no new NPCs or objects.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import engine

HOUSE_MAP = "ch_home/hm_non_cuper.png"
HOUSE_COLLISION = "ch_home/hkm.png"
HOUSE_SCALE = 3

ATOM_SPAWN = (139, 157)
COPPER_HOUSE = (723, 248)
KITCHEN_HINT = (680, 248)
INTERACTION_RADIUS = 100

# Real walkable area near the house, verified against world/vyshneve_collision.png.
CITY_SPAWN = (7738, 2325)
CITY_WAYPOINT = (7988, 2325)
WORLD_W, WORLD_H = 20480, 11520

EMOTION_INDEX = {
    "neutral": 1, "serious": 2, "smiling": 3, "cheerful": 4,
    "laughing": 5, "angry": 6, "surprised": 7, "shocked": 8,
    "suspicious": 9, "ironic": 10, "sad": 11, "scared": 12,
    "confused": 13, "thoughtful": 14, "sleepy": 15,
}

# (speaker, emotion, text) — exact lines from the mission script.
DIALOGUES = {
    2: (
        ("copper", "smiling", "Доброго ранку!"),
        ("atom", "sleepy", "Доброго..."),
        ("copper", "ironic", "Судячи з голосу, ти ще десь у ліжку."),
        ("atom", "ironic", "Я фізично тут. Цього недостатньо?"),
        ("copper", "laughing", "Ха-ха! Майже."),
        ("atom", "neutral", "Що готуєш?"),
        ("copper", "cheerful", "Поки що нічого особливого. Думала зробити нам сніданок."),
        ("atom", "smiling", "Звучить добре."),
        ("copper", "thoughtful", "До речі, ти сьогодні знову збираєшся весь день сидіти за своїми справами?"),
        ("atom", "confused", "А що?"),
        ("copper", "ironic", "Нічого. Просто хотіла нагадати, що в тебе є дружина."),
        ("atom", "surprised", "Я начебто не забував."),
        ("copper", "smiling", "Тоді доведи це. Проведімо сьогодні трохи часу разом."),
        ("atom", "thoughtful", "Хм... Можна."),
        ("copper", "cheerful", "От і чудово!"),
    ),
    3: (
        ("atom", "neutral", "Куди хочеш піти?"),
        ("copper", "thoughtful", "Та хоча б просто пройтися неподалік."),
        ("atom", "smiling", "Без конкретного маршруту?"),
        ("copper", "smiling", "Саме так. Не все ж потрібно планувати."),
        ("atom", "ironic", "Смілива заява."),
        ("copper", "laughing", "Іноді можна!"),
        ("atom", "cheerful", "Добре. Тоді я з тобою."),
    ),
    4: (
        ("copper", "smiling", "Нарешті трохи свіжого повітря."),
        ("atom", "neutral", "Ти ж можеш виходити надвір коли завгодно."),
        ("copper", "ironic", "Самій не так цікаво."),
        ("atom", "smiling", "Зрозумів."),
        ("copper", "thoughtful", "А ти взагалі помічаєш, як швидко минають дні?"),
        ("atom", "thoughtful", "Іноді. Особливо коли постійно чимось зайнятий."),
        ("copper", "sad", "От саме."),
        ("atom", "serious", "Гаразд. Постараюся частіше знаходити час."),
        ("copper", "smiling", "Мені цього достатньо."),
    ),
    5: (
        ("copper", "cheerful", "Ну що, день уже став кращим?"),
        ("atom", "smiling", "Трохи."),
        ("copper", "ironic", "Тільки трохи?!"),
        ("atom", "laughing", "Добре, значно."),
        ("copper", "smiling", "От тепер інша справа."),
        ("atom", "neutral", "То що далі?"),
        ("copper", "cheerful", "Спочатку сніданок. А там побачимо."),
        ("atom", "smiling", "Домовилися."),
    ),
}

NAMES = {"atom": "Атом", "copper": "Мідь"}
ACCENT = (212, 91, 18)
PORTRAIT_SIZE = 128


def portrait_path(character: str, emotion: str) -> str:
    """Resolve an existing 128x128 emotion portrait (fallback: neutral)."""
    folder = os.path.join("characters", f"{character}_portraits_128x128")
    index = EMOTION_INDEX.get(emotion, 1)
    name = f"{character}_{index:02d}_{emotion}.png"
    path = os.path.join(folder, name)
    if os.path.exists(path):
        return path
    return os.path.join(folder, f"{character}_01_neutral.png")


def _wrap(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if font.size(test)[0] <= max_width or not current:
            current = test
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class StoryMission:
    """Runs mission 01 from a main-menu launch to the completion card."""

    def __init__(self, screen, settings):
        self.screen = screen
        self.settings = settings
        self.clock = pygame.time.Clock()
        self.font = engine._cached_ui_font(None, 24)
        self.small = engine._cached_ui_font(None, 18)
        self.title_font = engine._cached_ui_font(None, 46, bold=True)
        self.complete_font = engine._cached_ui_font(None, 52, bold=True)

        house_raw = engine.load_image(HOUSE_MAP)
        self.house_img = pygame.transform.smoothscale(
            house_raw,
            (house_raw.get_width() * HOUSE_SCALE, house_raw.get_height() * HOUSE_SCALE),
        )
        col_raw = engine.load_image(HOUSE_COLLISION)
        self.house_col = pygame.transform.scale(
            col_raw,
            (col_raw.get_width() * HOUSE_SCALE, col_raw.get_height() * HOUSE_SCALE),
        )
        self.map_src = engine.load_image("world/vyshneve_map_normal.png")
        self.world_col = engine.load_image("world/vyshneve_collision.png")
        self.atom_sprite = pygame.transform.scale(
            engine.load_image("characters/atom.png", alpha=True), (48, 48)
        )
        self.copper_sprite = pygame.transform.scale(
            engine.load_image("characters/copper.png", alpha=True), (48, 48)
        )
        self._portrait_cache: dict[tuple[str, str], pygame.Surface] = {}

        self.pos = pygame.Vector2(ATOM_SPAWN)
        self.copper_pos = pygame.Vector2(COPPER_HOUSE)
        self.scene = 1
        self.house_step = 0  # 0: before morning talk, 1: before small plan
        self.dialogue: list[tuple[str, str, str]] = []
        self.dialogue_index = 0
        self.dialogue_stage = 0
        self.dialogue_active = False
        self.subtitle_index = 0
        self.subtitle_timer = 0.0
        self.running = True
        self.complete_timer = 0.0
        self.finished = False

    # ---------- helpers ----------

    def _portrait(self, character: str, emotion: str) -> pygame.Surface:
        key = (character, emotion)
        surface = self._portrait_cache.get(key)
        if surface is None:
            surface = engine.load_image(portrait_path(character, emotion), alpha=True)
            self._portrait_cache[key] = surface
        return surface

    def _house_walkable(self, x: float, y: float) -> bool:
        ix, iy = int(x), int(y)
        if not (0 <= ix < self.house_col.get_width() and 0 <= iy < self.house_col.get_height()):
            return False
        return self.house_col.get_at((ix, iy))[:3] != (0, 0, 0)

    def _world_walkable(self, x: float, y: float) -> bool:
        sx = int(x / WORLD_W * self.world_col.get_width())
        sy = int(y / WORLD_H * self.world_col.get_height())
        if not (0 <= sx < self.world_col.get_width() and 0 <= sy < self.world_col.get_height()):
            return False
        red, green, blue = self.world_col.get_at((sx, sy))[:3]
        return not (red > 200 and green < 50 and blue < 50)

    def _near_copper(self) -> bool:
        return self.pos.distance_to(pygame.Vector2(COPPER_HOUSE)) <= INTERACTION_RADIUS

    def _fade(self) -> None:
        engine.fade_screen(self.screen, True, duration=0.35)

    def _fade_in(self) -> None:
        engine.fade_screen(self.screen, False, duration=0.35)

    def _start_dialogue(self, stage: int) -> None:
        self.dialogue = list(DIALOGUES[stage])
        self.dialogue_index = 0
        self.dialogue_stage = stage
        self.dialogue_active = True

    def _advance_dialogue(self) -> None:
        self.dialogue_index += 1
        if self.dialogue_index < len(self.dialogue):
            return
        self.dialogue_active = False
        stage = self.dialogue_stage
        if stage == 2:
            self.house_step = 1
        elif stage == 3:
            self._fade()
            self.scene = 4
            self.pos.update(CITY_SPAWN)
            self.copper_pos.update(CITY_SPAWN[0] - 55, CITY_SPAWN[1] + 20)
            self.subtitle_index = 0
            self.subtitle_timer = 0.0
            self._fade_in()
        elif stage == 5:
            self.finished = True
            self.complete_timer = 0.0
            self._fade()

    # ---------- update ----------

    def _move(self, keys, dt: float, *, world: bool) -> None:
        speed = 150 if world else 110
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            speed *= 1.7
        move = pygame.Vector2(0, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x += 1
        if move.length_squared() == 0:
            return
        move = move.normalize() * speed * dt
        new_x, new_y = self.pos.x + move.x, self.pos.y + move.y
        walkable = self._world_walkable if world else self._house_walkable
        if walkable(new_x, new_y):
            self.pos.update(new_x, new_y)

    def _update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        if self.finished:
            self.complete_timer += dt
            if self.complete_timer > 3.0:
                self.running = False
            return
        if self.dialogue_active:
            return  # movement is blocked while talking
        if self.scene in (1, 2, 3):
            self._move(keys, dt, world=False)
        elif self.scene == 4:
            old = pygame.Vector2(self.pos)
            self._move(keys, dt, world=True)
            if self.pos.distance_to(pygame.Vector2(CITY_SPAWN)) > 0:
                follow = self.pos + pygame.Vector2(-55, 20)
                if self._world_walkable(follow.x, follow.y):
                    self.copper_pos.lerp(follow, min(1.0, dt * 6.0))
            self.subtitle_timer += dt
            if self.subtitle_index < len(DIALOGUES[4]) and self.subtitle_timer > 3.4:
                self.subtitle_timer = 0.0
                self.subtitle_index += 1
            if self.pos.distance_to(pygame.Vector2(CITY_WAYPOINT)) < 60:
                self._fade()
                self.scene = 5
                self.pos.update(ATOM_SPAWN)
                self.copper_pos.update(COPPER_HOUSE)
                self.house_step = 2
                self._fade_in()
                self._start_dialogue(5)

    # ---------- drawing ----------

    def _draw_panel(self, rect: pygame.Rect, alpha: int = 235) -> None:
        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        surface.fill((14, 18, 26, alpha))
        pygame.draw.rect(surface, (120, 145, 175, 140), surface.get_rect(), 1, border_radius=10)
        pygame.draw.rect(surface, (*ACCENT, 255), (0, 0, 4, rect.height), border_radius=10)
        self.screen.blit(surface, rect.topleft)

    def _draw_house(self) -> None:
        x = (self.screen.get_width() - self.house_img.get_width()) // 2
        y = (self.screen.get_height() - self.house_img.get_height()) // 2
        self.screen.blit(self.house_img, (x, y))
        copper = pygame.transform.scale(self.copper_sprite, (48, 48))
        self.screen.blit(copper, copper.get_rect(center=(x + COPPER_HOUSE[0], y + COPPER_HOUSE[1])))
        atom = pygame.transform.rotate(self.atom_sprite, 0)
        self.screen.blit(atom, atom.get_rect(center=(x + self.pos.x, y + self.pos.y)))
        self._house_origin = (x, y)

    def _draw_world(self) -> None:
        sw, sh = self.screen.get_size()
        scale_x = self.map_src.get_width() / WORLD_W
        scale_y = self.map_src.get_height() / WORLD_H
        view_w = max(1, int(sw * scale_x))
        view_h = max(1, int(sh * scale_y))
        sx = int(self.pos.x * scale_x - view_w / 2)
        sy = int(self.pos.y * scale_y - view_h / 2)
        sx = max(0, min(sx, self.map_src.get_width() - view_w))
        sy = max(0, min(sy, self.map_src.get_height() - view_h))
        region = self.map_src.subsurface(pygame.Rect(sx, sy, view_w, view_h))
        view = pygame.transform.smoothscale(region, (sw, sh))
        self.screen.blit(view, (0, 0))
        px = sw / 2 + (self.pos.x - (sx / scale_x + sw / 2))
        py = sh / 2 + (self.pos.y - (sy / scale_y + sh / 2))
        cx = px - 55
        cy = py + 20
        self.screen.blit(self.copper_sprite, self.copper_sprite.get_rect(center=(cx, cy)))
        self.screen.blit(self.atom_sprite, self.atom_sprite.get_rect(center=(px, py)))

    def _draw_objective(self, text: str) -> None:
        rect = pygame.Rect(20, 20, min(520, self.font.size(text)[0] + 40), 46)
        self._draw_panel(rect, alpha=220)
        self.screen.blit(self.font.render(text, True, (245, 236, 220)), (rect.x + 16, rect.y + 10))

    def _draw_line(self, speaker: str, emotion: str, text: str, *, compact: bool = False) -> None:
        sw, sh = self.screen.get_size()
        panel_h = 150 if compact else 190
        rect = pygame.Rect(30, sh - panel_h - 30, sw - 60, panel_h)
        self._draw_panel(rect)
        portrait = self._portrait(speaker, emotion)
        portrait = pygame.transform.smoothscale(portrait, (PORTRAIT_SIZE, PORTRAIT_SIZE))
        self.screen.blit(portrait, (rect.x + 14, rect.y + (rect.height - PORTRAIT_SIZE) // 2))
        text_x = rect.x + PORTRAIT_SIZE + 34
        self.screen.blit(
            self.font.render(f"{NAMES[speaker]} · {emotion}", True, ACCENT),
            (text_x, rect.y + 14),
        )
        lines = _wrap(text, self.font, rect.width - PORTRAIT_SIZE - 60)
        for i, line in enumerate(lines[:3]):
            self.screen.blit(
                self.font.render(line, True, (245, 248, 252)),
                (text_x, rect.y + 48 + i * 30),
            )
        if not compact:
            hint = self.small.render("F / Enter — далі", True, (170, 180, 195))
            self.screen.blit(hint, (rect.right - hint.get_width() - 18, rect.bottom - 26))

    def _draw_completed(self) -> None:
        sw, sh = self.screen.get_size()
        self.screen.fill((8, 10, 14))
        first = self.complete_font.render("МІСІЮ ВИКОНАНО", True, ACCENT)
        second = self.title_font.render("ПРОБУДЖЕННЯ", True, (245, 236, 220))
        self.screen.blit(first, first.get_rect(center=(sw // 2, sh // 2 - 40)))
        self.screen.blit(second, second.get_rect(center=(sw // 2, sh // 2 + 30)))

    def _draw(self) -> None:
        if self.finished:
            self._draw_completed()
            pygame.display.flip()
            return
        self.screen.fill((12, 14, 18))
        if self.scene in (1, 2, 3):
            self._draw_house()
            if self.scene == 1:
                self._draw_objective("Дістанься кухні · підійди до Міді (F)")
            elif self.house_step == 0:
                self._draw_objective("Натисни F, щоб поговорити з Міддю")
            else:
                self._draw_objective("Натисни F ще раз · невеликий план")
        elif self.scene == 4:
            self._draw_world()
            self._draw_objective("Прогулянка · пройдися неподалік від дому")
        if self.dialogue_active:
            self._draw_line(*self.dialogue[self.dialogue_index])
        elif self.scene == 4 and self.subtitle_index < len(DIALOGUES[4]):
            self._draw_line(*DIALOGUES[4][self.subtitle_index], compact=True)
        pygame.display.flip()

    # ---------- public ----------

    def run(self) -> str:
        self._fade()
        self._draw_house()
        pygame.display.flip()
        self._fade_in()
        while self.running:
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "EXIT"
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.dialogue_active:
                            self._advance_dialogue()
                        else:
                            return "BACK"
                    if event.key in (pygame.K_f, pygame.K_RETURN, pygame.K_SPACE):
                        if self.dialogue_active:
                            self._advance_dialogue()
                        elif self.scene in (1, 2, 3) and self._near_copper():
                            if self.scene == 1 or self.house_step == 0:
                                self._start_dialogue(2)
                            elif self.house_step == 1:
                                self._start_dialogue(3)
            self._update(self.clock.get_time() / 1000.0)
            self._draw()
        if self.finished:
            self._fade_in()
        return "DONE"


def run_story_mission(screen, settings) -> str:
    """Launch the mission; returns 'DONE', 'BACK' or 'EXIT'."""
    return StoryMission(screen, settings).run()
