import json
import math
import random
from pathlib import Path
import sys

import pygame

import constants as _constants
from constants import WIDTH, HEIGHT, FPS

_menu_sounds: dict[str, pygame.mixer.Sound | None] = {}
_house_icon: pygame.Surface | None = None
_house_icon_load_attempted = False
_AUDIO_DEFAULTS = {
    "music_volume": 20,
    "npc_volume": 100,
    "crash_volume": 100,
    "button_volume": 100,
    "footsteps_volume": 100,
}
_audio_settings: dict[str, float] = {key: value / 100 for key, value in _AUDIO_DEFAULTS.items()}
_MENU_SOUND_LEVELS = {"hover": 0.22, "click": 0.38}


def configure_audio(settings):
    global _audio_settings
    for key, default in _AUDIO_DEFAULTS.items():
        try:
            value = int(settings.get(key, default))
        except (TypeError, ValueError):
            value = default
        _audio_settings[key] = max(0, min(100, value)) / 100

    for kind, sound in _menu_sounds.items():
        if sound is not None:
            sound.set_volume(_MENU_SOUND_LEVELS[kind] * _audio_settings["button_volume"])

    if pygame.mixer.get_init():
        try:
            pygame.mixer.music.set_volume(_audio_settings["music_volume"])
        except pygame.error:
            pass


def _sync_display_state(surface, settings):
    global WIDTH, HEIGHT, FPS
    width, height = surface.get_size()
    fps_limit = int(settings.get("fps_limit", 60))
    settings["video_width"] = width
    settings["video_height"] = height
    _constants.WIDTH, _constants.HEIGHT, _constants.FPS = width, height, fps_limit
    WIDTH, HEIGHT, FPS = width, height, fps_limit
    for module_name in ("main", "chapters.ch1"):
        module = sys.modules.get(module_name)
        if module is not None:
            module.WIDTH = width
            module.HEIGHT = height
            module.FPS = fps_limit
    return surface


def apply_video_settings(settings):
    """Apply saved window settings and refresh modules that imported constants."""
    width = int(settings.get("video_width", 1280))
    height = int(settings.get("video_height", 720))
    try:
        surface = pygame.display.set_mode((width, height), pygame.RESIZABLE)
    except pygame.error:
        settings.update({"video_width": 1280, "video_height": 720})
        surface = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
    return _sync_display_state(surface, settings)


def apply_window_resize(size, settings):
    """Keep the game surface and imported dimensions in sync with the OS window."""
    width = max(800, min(7680, int(size[0])))
    height = max(600, min(4320, int(size[1])))
    surface = pygame.display.get_surface()
    if surface is None or surface.get_size() != (width, height):
        try:
            surface = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        except pygame.error:
            surface = pygame.display.get_surface()
    return _sync_display_state(surface, settings)


def _available_resolutions(settings):
    resolutions = set()
    try:
        modes = pygame.display.list_modes(0, pygame.FULLSCREEN)
    except pygame.error:
        modes = []
    if isinstance(modes, (list, tuple)):
        resolutions.update(tuple(map(int, size)) for size in modes if len(size) == 2)

    desktop_sizes = []
    try:
        desktop_sizes = pygame.display.get_desktop_sizes()
        resolutions.update(tuple(map(int, size)) for size in desktop_sizes if len(size) == 2)
    except (AttributeError, pygame.error):
        pass

    max_width = max((size[0] for size in desktop_sizes), default=1920)
    max_height = max((size[1] for size in desktop_sizes), default=1080)
    standard_modes = (
        (800, 600), (1024, 768), (1280, 720), (1280, 800),
        (1366, 768), (1600, 900), (1920, 1080), (2560, 1440),
        (3840, 2160),
    )
    resolutions.update(
        size for size in standard_modes
        if size[0] <= max_width and size[1] <= max_height
    )

    resolutions.add((int(settings.get("video_width", 1280)), int(settings.get("video_height", 720))))
    resolutions = {
        size for size in resolutions
        if 800 <= size[0] <= 7680 and 600 <= size[1] <= 4320
    }
    return sorted(resolutions, key=lambda size: (size[0] * size[1], size[0])) or [(1280, 720)]


def play_menu_sound(kind):
    sound_paths = {
        "hover": "menu_hover.wav",
        "click": "menu_click.wav",
    }
    if kind not in sound_paths:
        return
    if kind not in _menu_sounds:
        path = Path(__file__).resolve().parent / "sounds" / sound_paths[kind]
        try:
            _menu_sounds[kind] = pygame.mixer.Sound(str(path))
            _menu_sounds[kind].set_volume(_MENU_SOUND_LEVELS[kind] * _audio_settings["button_volume"])
        except pygame.error:
            _menu_sounds[kind] = None
    sound = _menu_sounds[kind]
    if sound is not None:
        sound.play()


def _get_house_icon() -> pygame.Surface | None:
    global _house_icon, _house_icon_load_attempted
    if _house_icon_load_attempted:
        return _house_icon

    _house_icon_load_attempted = True
    icon_path = Path(__file__).resolve().parent / "ch_home" / "haus.png"
    try:
        _house_icon = pygame.image.load(str(icon_path)).convert_alpha()
    except (pygame.error, OSError):
        _house_icon = None
    return _house_icon


class Player:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.speed = 2
        self.angle = 0  # 0 degrees points south (down) by default.
        self.is_moving = False

        self.original_image: pygame.Surface | None = None
        self.image: pygame.Surface | None = None
        try:
            path = Path(__file__).resolve().parent / "characters" / "atom.png"
            raw = pygame.image.load(str(path)).convert_alpha()
            self.original_image = pygame.transform.scale(raw, (48, 48))
            self.image = self.original_image
        except (pygame.error, OSError) as exc:
            print(f"Не вдалося завантажити characters/atom.png: {exc}")

    def update(self, keys, col_mask, car_obj=None, npc_cars=None, frame_scale=1.0):
        move = pygame.Vector2(0, 0)

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y = -1
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y = 1

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x = -1
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x = 1

        if move.length() > 0:
            self.is_moving = True

            # Set the character facing direction.
            if move.y == 1:
                if move.x == 1:
                    self.angle = -45
                elif move.x == -1:
                    self.angle = 45
                else:
                    self.angle = 0
            elif move.y == -1:
                if move.x == 1:
                    self.angle = -135
                elif move.x == -1:
                    self.angle = 135
                else:
                    self.angle = 180
            elif move.x == 1:
                self.angle = -90
            elif move.x == -1:
                self.angle = 90

            move = move.normalize() * self.speed * frame_scale
            new_pos = self.pos + move

            can_move = True

            # 1. Check the collision mask (walls).
            mask_x, mask_y = int(new_pos.x), int(new_pos.y)
            if (
                col_mask is None
                or not col_mask.get_rect().collidepoint(mask_x, mask_y)
            ):
                can_move = False
            else:
                pixel = col_mask.get_at((mask_x, mask_y))
                if pixel.r > 200 and pixel.g < 50 and pixel.b < 50:
                    can_move = False

            # 2. Check for traffic collisions.
            if can_move and npc_cars:
                    for npc in npc_cars:
                        dist = new_pos.distance_to(npc.pos)
                        if dist < 45:  # Traffic collision radius; stop Atom when he gets closer.
                            can_move = False
                            break
            if car_obj and can_move:
                # Get the vector from the car center to Atom’s next position.
                rel_pos = new_pos - car_obj.pos

                # Rotate the vector by the car angle to convert it to local coordinates.
                # Use .rotate(car_obj.angle) to check the point in the car’s local coordinates.
                rotated_rel = rel_pos.rotate(car_obj.angle)

                # Treat the car as axis-aligned and check its 96x48 bounds.
                # Half-width is 48 pixels; half-height is 24 pixels.
                # Leave a small margin so Atom does not get stuck in the corners.
                if abs(rotated_rel.x) < 46 and abs(rotated_rel.y) < 22:
                    can_move = False

            if can_move:
                self.pos = new_pos
        else:
            self.is_moving = False
    def draw(self, screen, offset_x, offset_y):
        if self.image:
            # Negate the angle to match the game’s coordinate convention.
            rotated = pygame.transform.rotate(self.image, self.angle)

            # Center the sprite to prevent jitter.
            rect = rotated.get_rect(center=(self.pos.x + offset_x, self.pos.y + offset_y))
            screen.blit(rotated, rect)
        else:
            pygame.draw.circle(screen, (255, 200, 0), (int(self.pos.x + offset_x), int(self.pos.y + offset_y)), 15)

class Car:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.angle = 0
        self.speed = 0
        self.max_speed = 15
        self.accel = 0.08
        self.friction = 0.04
        self.brake_force = 0.3
        self.motion_velocity = pygame.Vector2()

        self.skid_marks = []
        self.just_hit = False

        # --- Vehicle damage system ---
        self.health = 200.0  # Current health.
        self.max_health = 200.0
        self.smoke_particles = []
        self.is_broken = False  # Whether the car is disabled.
        self.repair_progress = 0  # Repair progress in frames (360 frames equals 6 seconds).
        # -----------------------

        self.ui_x = 950
        self.ui_y = 600
        self.ui_radius = 75

        try:
            self.ui_font = pygame.font.Font(None, 20)
        except pygame.error:
            self.ui_font = pygame.font.SysFont("Arial", 14)

        try:
            image_path = Path(__file__).resolve().parent / "cars" / "tornado" / "tornado_special.png"
            self.image = pygame.image.load(str(image_path)).convert_alpha()
            self.image = pygame.transform.scale(self.image, (96, 48))
        except (pygame.error, OSError):
            self.image = pygame.Surface((96, 48))
            self.image.fill((0, 0, 255))

    def update(self, keys, col_mask, active, npc_cars=None, frame_scale=1.0):
        left_pressed = False
        right_pressed = False
        # A broken car does not respond to acceleration.
        if self.is_broken:
            active = False
            if abs(self.speed) < 0.1: self.speed = 0

        if not active:
            if abs(self.speed) > 0.1:
                self.speed *= 0.95 ** frame_scale
            else:
                self.speed = 0
        else:
            # 1. Speed control.
            current_accel = self.accel * frame_scale
            if abs(self.speed) > 10: current_accel = self.accel / 3
            if abs(self.speed) > 10: current_accel *= frame_scale

            if keys[pygame.K_w] or keys[pygame.K_UP]:
                if self.speed < 0:
                    self.speed += self.brake_force * frame_scale
                else:
                    self.speed = min(self.speed + current_accel, self.max_speed)
            elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
                if self.speed > 0:
                    self.speed -= self.brake_force * frame_scale
                else:
                    self.speed = max(self.speed - current_accel, -self.max_speed / 2)
            else:
                self.speed *= 0.97 ** frame_scale

            # 2. Steering.
            left_pressed = keys[pygame.K_a] or keys[pygame.K_LEFT]
            right_pressed = keys[pygame.K_d] or keys[pygame.K_RIGHT]
            if abs(self.speed) > 0.5:
                steer = 5.0 - (min(abs(self.speed) / 2, 1.0))
                direction = 1 if self.speed > 0 else -1
                if left_pressed: self.angle += steer * direction * frame_scale
                if right_pressed: self.angle -= steer * direction * frame_scale

        # 3. Movement and collision. At higher speed the car's momentum
        # follows steering more slowly, so it slides sideways during turns.
        current_kmh = abs(self.speed) * 8
        is_turning = left_pressed != right_pressed
        is_drifting = active and current_kmh > 40 and is_turning
        desired_velocity = pygame.Vector2(self.speed, 0).rotate(-self.angle + 180)
        if is_drifting:
            drift_intensity = min((current_kmh - 40) / 80, 1.0)
            grip = 0.40 - 0.24 * drift_intensity
        elif current_kmh > 40:
            grip = 0.38
        else:
            grip = 0.65
        blend = 1 - (1 - grip) ** max(frame_scale, 0)
        self.motion_velocity += (desired_velocity - self.motion_velocity) * blend
        velocity = self.motion_velocity
        next_pos = self.pos + velocity * frame_scale
        # 1. Update existing smoke particles, even while the car is stationary.
        self.update_smoke_particles(frame_scale)

        # 2. Create new particles when the car is damaged.
        # Emit smoke only when health is below 50%.
        if self.health < self.max_health * 0.5:
            # Lower health makes smoke appear more often.
            spawn_chance = 10  # Base chance: once every 10 frames.

            # At critical health (<20%), smoke appears almost continuously.
            if self.health < self.max_health * 0.2:
                spawn_chance = 2  # Very frequently.

            # Add randomness so smoke does not look continuous.
            if random.random() < min(1.0, frame_scale / spawn_chance):
                self.create_smoke_particle()  # <-- This method is defined below.

        def check_at_pos(test_pos):
            if npc_cars:
                for npc in npc_cars:
                    # Check nearby traffic around the player’s car.
                    if test_pos.distance_to(npc.pos) < 95:  # Detection distance.
                        # Build rectangles for the sprite collision check.
                        my_rect = self.image.get_rect(center=test_pos)
                        # npc.image.get_rect(center=npc.pos) is the other car’s rectangle.
                        if my_rect.colliderect(npc.image.get_rect(center=npc.pos)):
                            return True  # Treat the other car as an obstacle.
            w, h = 45, 22
            points = [
                test_pos + pygame.Vector2(w, h).rotate(-self.angle + 180),
                test_pos + pygame.Vector2(w, -h).rotate(-self.angle + 180),
                test_pos + pygame.Vector2(-w, h).rotate(-self.angle + 180),
                test_pos + pygame.Vector2(-w, -h).rotate(-self.angle + 180),
                test_pos + pygame.Vector2(w, 0).rotate(-self.angle + 180),
                test_pos + pygame.Vector2(-w, 0).rotate(-self.angle + 180)
            ]
            for point in points:
                mask_x, mask_y = int(point.x), int(point.y)
                if (
                    col_mask is None
                    or not col_mask.get_rect().collidepoint(mask_x, mask_y)
                ):
                    return True
                pixel = col_mask.get_at((mask_x, mask_y))
                is_red_wall = pixel.r > 200 and pixel.g < 50 and pixel.b < 50
                is_black_wall = pixel.r < 50 and pixel.g < 50 and pixel.b < 50
                if is_red_wall or is_black_wall:
                    return True
            return False

        if check_at_pos(next_pos):
            # --- Damage handling ---
            impact_speed = abs(self.speed)
            if impact_speed > 1.5:
                self.just_hit = True
                # Damage increases with impact speed.
                damage = impact_speed * 2
                self.health -= damage
                if self.health <= 0:
                    self.health = 0
                    self.is_broken = True
            # -------------------------

            if velocity.length() > 0:
                self.pos -= velocity.normalize() * 5 * frame_scale
            self.speed = -self.speed * 0.6
            self.motion_velocity *= -0.6
        else:
            old_pos = pygame.Vector2(self.pos.x, self.pos.y)
            self.pos = next_pos

            # Tire tracks.
            is_braking = active and ((keys[pygame.K_s] and self.speed > 2) or (keys[pygame.K_w] and self.speed < -2))
            if is_braking or is_drifting:
                forward_vec = pygame.Vector2(1, 0).rotate(-self.angle + 180)
                off_l = pygame.Vector2(0, 16).rotate(-self.angle + 180)
                off_r = pygame.Vector2(0, -16).rotate(-self.angle + 180)
                back_axle = forward_vec * 35
                p1_l, p1_r = (old_pos - back_axle) + off_l, (old_pos - back_axle) + off_r
                p2_l, p2_r = (self.pos - back_axle) + off_l, (self.pos - back_axle) + off_r
                self.skid_marks.append((p1_l, p2_l, p1_r, p2_r))
                if len(self.skid_marks) > 60: self.skid_marks.pop(0)

    def create_smoke_particle(self):
        """Create one smoke particle at the center of the car."""
        # Spawn smoke near the car’s position.
        spawn_x = self.pos.x + random.randint(-5, 5)
        spawn_y = self.pos.y + random.randint(-5, 5)

        particle = [
            spawn_x,  # 0: x
            spawn_y,  # 1: y
            random.randint(5, 10),  # 2: radius
            random.randint(150, 200),  # 3: alpha
            random.uniform(1.0, 2.5),  # 4: upward velocity
            random.randint(40, 70)  # 5: lifetime
        ]
        self.smoke_particles.append(particle)
    def update_smoke_particles(self, frame_scale=1.0):
        """Update all existing smoke particles."""
        for p in self.smoke_particles[:]:
            p[1] -= p[4] * frame_scale  # Move the particle upward by changing y.
            p[2] += 0.3 * frame_scale  # Increase the radius as the particle expands.
            p[3] -= 3 * frame_scale  # Reduce opacity (alpha).
            p[5] -= frame_scale  # Decrease the remaining lifetime.

            # Remove particles when they fade out or expire.
            if p[3] <= 0 or p[5] <= 0:
                self.smoke_particles.remove(p)
    def draw(self, screen, offset_x, offset_y):
        for p1l, p2l, p1r, p2r in self.skid_marks:
            pygame.draw.line(screen, (45, 45, 45), (p1l.x + offset_x, p1l.y + offset_y),
                             (p2l.x + offset_x, p2l.y + offset_y), 5)
            pygame.draw.line(screen, (45, 45, 45), (p1r.x + offset_x, p1r.y + offset_y),
                             (p2r.x + offset_x, p2r.y + offset_y), 5)

        rotated = pygame.transform.rotate(self.image, self.angle)
        rect = rotated.get_rect(center=(self.pos.x + offset_x, self.pos.y + offset_y))

        # Optional: add vibration or light smoke below 30% health.
        screen.blit(rotated, rect)

    def draw_speedometer(self, screen):
        center = (screen.get_width() - 330, screen.get_height() - 120)
        r = self.ui_radius

        # Draw the health bar above the speedometer.
        bar_width = 100
        bar_height = 10
        bar_x = center[0] - bar_width // 2
        bar_y = center[1] - r - 30

        # The color shifts from green to red.
        hp_ratio = self.health / self.max_health
        hp_color = (int(255 * (1 - hp_ratio)), int(255 * hp_ratio), 0)

        # Gray health-bar background.
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
        # Current health.
        pygame.draw.rect(screen, hp_color, (bar_x, bar_y, int(bar_width * hp_ratio), bar_height))
        # Border.
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, bar_width, bar_height), 1)

        # Additional speedometer markings.
        pygame.draw.circle(screen, (20, 20, 20), center, r + 5)
        pygame.draw.circle(screen, (0, 0, 0), center, r)

        speed_labels = [0, 20, 40, 60, 80, 100, 120]
        for km in speed_labels:
            val_norm = km / 120
            angle_deg = -225 + val_norm * 270
            rad = math.radians(angle_deg)
            p1 = (center[0] + math.cos(rad) * (r * 0.85), center[1] + math.sin(rad) * (r * 0.85))
            p2 = (center[0] + math.cos(rad) * r, center[1] + math.sin(rad) * r)
            pygame.draw.line(screen, (255, 255, 255), p1, p2, 2)
            text_pos = (center[0] + math.cos(rad) * (r * 0.65), center[1] + math.sin(rad) * (r * 0.65))
            txt = self.ui_font.render(str(km), True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=text_pos))

        current_kmh = abs(self.speed) * 8
        val = min(current_kmh / 120, 1.0)
        angle_rad = math.radians(-225 + val * 270)
        target = (center[0] + math.cos(angle_rad) * (r * 0.8), center[1] + math.sin(angle_rad) * (r * 0.8))
        pygame.draw.line(screen, (255, 0, 0), center, target, 4)
        pygame.draw.circle(screen, (150, 0, 0), center, 8)

def draw_atom_character(ctx, x, y, atom_tex, angle):
    """Draw Atom with the correct texture rotation."""
    rotated_atom = pygame.transform.rotate(atom_tex, -angle)
    rect = rotated_atom.get_rect(center=(int(x), int(y)))
    ctx.blit(rotated_atom, rect)


def draw_gta_minimap(screen, bg_img, target, world_w, world_h, house_pos=(7738, 2325)):
    """Draw a minimap that stays within the world bounds."""

    size, margin = 200, 30
    screen_width, screen_height = screen.get_size()
    x, y = screen_width - size - margin, screen_height - size - margin

    # Create a transparent surface for the minimap.
    mini_surf = pygame.Surface((size, size), pygame.SRCALPHA)

    zoom = 0.1
    # Calculate the map scale once.
    map_scale_x = bg_img.get_width() * (size / (bg_img.get_width() * zoom))
    map_scale_y = bg_img.get_height() * (size / (bg_img.get_height() * zoom))

    # Coordinate conversion ratios.
    ratio_x = map_scale_x / world_w
    ratio_y = map_scale_y / world_h

    # --- Main camera-boundary logic ---
    # Distance from the minimap center to its edge, in map pixels.
    half_size = size // 2

    # Clamp the minimap camera center to avoid showing empty areas.
    # Keep the camera at least half_size pixels from the map edge.
    cam_x = max(half_size, min(target.pos.x * ratio_x, map_scale_x - half_size))
    cam_y = max(half_size, min(target.pos.y * ratio_y, map_scale_y - half_size))

    # Offset the background relative to the fixed camera.
    ox = -cam_x + half_size
    oy = -cam_y + half_size

    # Draw the map background.
    temp = pygame.transform.scale(bg_img, (int(map_scale_x), int(map_scale_y)))
    mini_surf.blit(temp, (ox, oy))

    # House marker.
    hx = (house_pos[0] * ratio_x) + ox
    hy = (house_pos[1] * ratio_y) + oy

    house_icon = _get_house_icon()
    if house_icon is not None:
        icon_mini = pygame.transform.scale(house_icon, (20, 20))
        mini_surf.blit(icon_mini, (int(hx) - 10, int(hy) - 10))
    else:
        pygame.draw.circle(mini_surf, (0, 0, 255), (int(hx), int(hy)), 5)

    # Player marker; it moves away from the center near map boundaries.
    px = (target.pos.x * ratio_x) + ox
    py = (target.pos.y * ratio_y) + oy

    # Draw the player marker on the minimap surface.
    pygame.draw.circle(mini_surf, (255, 0, 0), (int(px), int(py)), 6)
    pygame.draw.circle(mini_surf, (255, 255, 255), (int(px), int(py)), 6, 2)

    # Apply a circular mask to crop the map edges.
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (half_size, half_size), half_size)
    mini_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    # Draw the minimap on the main screen.
    # Border.
    pygame.draw.circle(screen, (255, 255, 255), (x + half_size, y + half_size), half_size + 3, 3)
    # Map.
    screen.blit(mini_surf, (x, y))

def stats_dialog(screen, font, small_font, t, stats=None, controls=None):
    stats = stats or {}
    clock = pygame.time.Clock()
    last_hovered = False
    width, height = screen.get_size()
    back_rect = pygame.Rect(width // 2 - 120, height - 150, 240, 56)

    while True:
        screen.fill((14, 14, 20))
        title = font.render(t.get("stats_title", "Stats"), True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(width // 2, 125)))

        lines = [
            t.get("stats_money", "Money: {money}").format(money=stats.get("money", 0)),
            t.get("stats_time", "Time: {time}").format(time=stats.get("time", "00:00")),
            t.get("stats_treasures", "Treasures: {treasures}").format(
                treasures=stats.get("treasures", 0)
            ),
            t.get("stats_earned", "Total earned: {amount} UAH").format(
                amount=stats.get("earned", 0)
            ),
            t.get("stats_spent", "Total spent: {amount} UAH").format(
                amount=stats.get("spent", 0)
            ),
        ]
        for index, line in enumerate(lines):
            rendered = small_font.render(line, True, (220, 220, 220))
            screen.blit(rendered, rendered.get_rect(center=(width // 2, 230 + index * 54)))

        mouse_pos = pygame.mouse.get_pos()
        hovered = back_rect.collidepoint(mouse_pos)
        if hovered and not last_hovered:
            play_menu_sound("hover")
        last_hovered = hovered
        color = (212, 91, 18) if hovered else (70, 70, 70)
        pygame.draw.rect(screen, color, back_rect, border_radius=8)
        back_text = small_font.render(t.get("back", "Back"), True, (255, 255, 255))
        screen.blit(back_text, back_text.get_rect(center=back_rect.center))
        hint = small_font.render(t.get("stats_hint", "Press Esc or Enter to return"), True, (150, 150, 150))
        screen.blit(hint, hint.get_rect(center=(width // 2, height - 55)))
        pygame.display.flip()

        for event in pygame.event.get():
            if controls is not None:
                controls.process_event(event)
            if event.type == pygame.QUIT:
                return "EXIT"
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                play_menu_sound("click")
                return "BACK"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and back_rect.collidepoint(event.pos):
                play_menu_sound("click")
                return "BACK"
        clock.tick(FPS)


def pause_menu(screen, font, small_font, settings, trans_dict, languages, controls=None, stats=None, on_change=None):
    pygame.mouse.set_visible(True)
    sel = 0
    clock = pygame.time.Clock()
    last_hovered = None

    def activate_option(index, translations):
        if index == 0:
            return "CONTINUE"
        if index == 1:
            result = stats_dialog(screen, font, small_font, translations, stats, controls)
            return "EXIT" if result == "EXIT" else None
        if index == 2:
            result = settings_sub_menu(screen, font, settings, trans_dict, languages, controls, on_change)
            return result if result in ("EXIT", "VIDEO_CHANGED") else None
        elif index == 3 and confirm_dialog(screen, font, small_font, translations, controls):
            return "MENU"
        return None

    while True:
        t = trans_dict[languages[settings['lang_idx']]]
        options = [t["resume"], t["stats"], t["settings"], t["menu"]]

        screen.fill((0, 0, 0))
        m_pos = pygame.mouse.get_pos()
        rects = [pygame.Rect(50, 200 + i * 100, 500, 60) for i in range(len(options))]

        for event in pygame.event.get():
            if controls is not None:
                controls.process_event(event)
            if event.type == pygame.QUIT: return "EXIT"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    play_menu_sound("click")
                    return "CONTINUE"
                if event.key == pygame.K_UP:
                    sel = (sel - 1) % len(options)
                    play_menu_sound("hover")
                if event.key == pygame.K_DOWN:
                    sel = (sel + 1) % len(options)
                    play_menu_sound("hover")
                if event.key == pygame.K_RETURN:
                    play_menu_sound("click")
                    result = activate_option(sel, t)
                    if result is not None:
                        return result

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, r in enumerate(rects):
                    if r.collidepoint(event.pos):
                        play_menu_sound("click")
                        result = activate_option(i, t)
                        if result is not None:
                            return result

        for i, opt in enumerate(options):
            if rects[i].collidepoint(m_pos):
                if last_hovered != i:
                    play_menu_sound("hover")
                last_hovered = i
                sel = i
            color = (212, 91, 18) if i == sel else (255, 255, 255)
            txt = font.render(opt, True, color)
            screen.blit(txt, (50, 200 + i * 100))
        if not any(rect.collidepoint(m_pos) for rect in rects):
            last_hovered = None

        pygame.display.flip()
        clock.tick(FPS)


def _audio_settings_menu(screen, font, settings, trans_dict, languages, controls=None, on_change=None):
    volume_keys = ("music_volume", "npc_volume", "crash_volume", "button_volume", "footsteps_volume")
    title_keys = ("music_vol", "npc_vol", "crash_vol", "button_vol", "footsteps_vol")
    selected_index = 0
    last_hovered = None
    mouse_control_active = False
    clock = pygame.time.Clock()
    hint_font = pygame.font.Font(None, 22)

    def adjust_volume(index, direction):
        key = volume_keys[index]
        settings[key] = max(0, min(100, settings[key] + direction * 5))
        configure_audio(settings)
        if on_change is not None:
            on_change(settings)
        play_menu_sound("click")

    while True:
        language = languages[settings["lang_idx"]]
        text = trans_dict.get(language, {})
        screen_width, screen_height = screen.get_size()
        row_step = min(82, max(54, (screen_height - 210) // len(volume_keys)))
        row_height = min(64, row_step - 6)
        first_y = (screen_height - (row_step * (len(volume_keys) - 1) + row_height)) // 2
        row_rects = [
            pygame.Rect(40, first_y + index * row_step, screen_width - 80, row_height)
            for index in range(len(volume_keys))
        ]
        decrease_rects = [
            pygame.Rect(screen_width - 300, rect.y + (row_height - 54) // 2, 60, 54)
            for rect in row_rects
        ]
        increase_rects = [
            pygame.Rect(screen_width - 110, rect.y + (row_height - 54) // 2, 60, 54)
            for rect in row_rects
        ]
        back_rect = pygame.Rect(screen_width // 2 - 110, screen_height - 105, 220, 50)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if controls is not None:
                controls.process_event(event)
            if event.type == pygame.MOUSEMOTION:
                mouse_control_active = True
            elif event.type == pygame.KEYDOWN:
                mouse_control_active = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_control_active = True
            if event.type == pygame.QUIT:
                return "EXIT"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    play_menu_sound("click")
                    return "BACK"
                if event.key == pygame.K_UP:
                    selected_index = (selected_index - 1) % len(volume_keys)
                    play_menu_sound("hover")
                elif event.key == pygame.K_DOWN:
                    selected_index = (selected_index + 1) % len(volume_keys)
                    play_menu_sound("hover")
                elif event.key == pygame.K_LEFT:
                    adjust_volume(selected_index, -1)
                elif event.key in (pygame.K_RIGHT, pygame.K_RETURN):
                    adjust_volume(selected_index, 1)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if back_rect.collidepoint(event.pos):
                    play_menu_sound("click")
                    return "BACK"
                for index, rect in enumerate(row_rects):
                    if decrease_rects[index].collidepoint(event.pos):
                        selected_index = index
                        adjust_volume(index, -1)
                        break
                    if increase_rects[index].collidepoint(event.pos):
                        selected_index = index
                        adjust_volume(index, 1)
                        break
                    if rect.collidepoint(event.pos):
                        selected_index = index
                        break

        screen.fill((20, 20, 20))
        page_title = font.render(text.get("volume", "Volume"), True, (220, 220, 220))
        screen.blit(page_title, page_title.get_rect(center=(screen_width // 2, 38)))

        for index, rect in enumerate(row_rects):
            hovered = mouse_control_active and rect.collidepoint(mouse_pos)
            if hovered and last_hovered != index:
                play_menu_sound("hover")
            if hovered:
                selected_index = index
                last_hovered = index
            row_color = (65, 50, 40) if index == selected_index else (38, 38, 38)
            pygame.draw.rect(screen, row_color, rect, border_radius=8)

            label = text.get(title_keys[index], "Volume")
            rendered_label = font.render(label, True, (255, 255, 255))
            screen.blit(
                rendered_label,
                (rect.x + 20, rect.y + (row_height - rendered_label.get_height()) // 2),
            )

            value = font.render(f"{settings[volume_keys[index]]}%", True, (255, 255, 255))
            screen.blit(value, value.get_rect(center=(screen_width - 190, rect.centery)))

            for button_rect, symbol in (
                (decrease_rects[index], "−"),
                (increase_rects[index], "+"),
            ):
                button_hovered = button_rect.collidepoint(mouse_pos)
                button_color = (212, 91, 18) if button_hovered else (85, 85, 85)
                pygame.draw.rect(screen, button_color, button_rect, border_radius=7)
                rendered_symbol = font.render(symbol, True, (255, 255, 255))
                screen.blit(rendered_symbol, rendered_symbol.get_rect(center=button_rect.center))

        if not any(rect.collidepoint(mouse_pos) for rect in row_rects):
            last_hovered = None
        pygame.draw.rect(screen, (70, 70, 70), back_rect, border_radius=8)
        rendered_back = font.render(text.get("back", "Back"), True, (255, 255, 255))
        screen.blit(rendered_back, rendered_back.get_rect(center=back_rect.center))
        hint = text.get(
            "audio_hint",
            "Up/Down selects a sound; Left/Right adjusts it; Esc returns",
        )
        rendered_hint = hint_font.render(hint, True, (170, 170, 170))
        screen.blit(
            rendered_hint,
            rendered_hint.get_rect(center=(screen_width // 2, screen_height - 28)),
        )

        pygame.display.flip()
        clock.tick(FPS)


def _video_settings_menu(screen, font, settings, trans_dict, languages, controls=None, on_change=None):
    fps_values = (0, 30, 60, 75, 90, 120, 144, 165, 240)
    resolutions = _available_resolutions(settings)
    selected_index = 1
    changed = False
    mouse_control_active = False
    last_hovered = None
    clock = pygame.time.Clock()
    hint_font = pygame.font.Font(None, 20)

    def adjust(direction):
        nonlocal changed
        if selected_index == 1:
            current = (settings["video_width"], settings["video_height"])
            try:
                current_index = resolutions.index(current)
            except ValueError:
                current_index = 0
            settings["video_width"], settings["video_height"] = resolutions[
                (current_index + direction) % len(resolutions)
            ]
        elif selected_index == 2:
            current_index = fps_values.index(settings.get("fps_limit", 60))
            settings["fps_limit"] = fps_values[(current_index + direction) % len(fps_values)]
        else:
            return
        changed = True
        if on_change is not None:
            on_change(settings)
        play_menu_sound("click")

    while True:
        language = languages[settings["lang_idx"]]
        text = trans_dict.get(language, {})
        screen_width, screen_height = screen.get_size()
        row_step = min(112, max(78, (screen_height - 180) // 4))
        row_height = min(64, row_step - 8)
        first_y = max(62, (screen_height - (row_step * 3 + row_height)) // 2)
        row_rects = [
            pygame.Rect(40, first_y + index * row_step, screen_width - 80, row_height)
            for index in range(4)
        ]
        back_rect = pygame.Rect(screen_width // 2 - 110, screen_height - 90, 220, 48)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if controls is not None:
                controls.process_event(event)
            if event.type == pygame.MOUSEMOTION:
                mouse_control_active = True
            elif event.type == pygame.KEYDOWN:
                mouse_control_active = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_control_active = True
            if event.type == pygame.QUIT:
                return "EXIT"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    play_menu_sound("click")
                    return "VIDEO_CHANGED" if changed else "BACK"
                if event.key == pygame.K_UP:
                    selected_index = (selected_index - 1) % 4
                    play_menu_sound("hover")
                elif event.key == pygame.K_DOWN:
                    selected_index = (selected_index + 1) % 4
                    play_menu_sound("hover")
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT) and 0 < selected_index < 3:
                    adjust(-1 if event.key == pygame.K_LEFT else 1)
                elif event.key == pygame.K_RETURN:
                    if selected_index == 3:
                        return "VIDEO_CHANGED" if changed else "BACK"
                    adjust(1)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if back_rect.collidepoint(event.pos):
                    play_menu_sound("click")
                    return "VIDEO_CHANGED" if changed else "BACK"
                for index, rect in enumerate(row_rects):
                    if rect.collidepoint(event.pos):
                        selected_index = index
                        if index == 3:
                            return "VIDEO_CHANGED" if changed else "BACK"
                        adjust(1)
                        break

        screen.fill((20, 20, 20))
        page_title = font.render(text.get("video", "Video"), True, (220, 220, 220))
        screen.blit(page_title, page_title.get_rect(center=(screen_width // 2, 38)))
        values = (
            text.get("window_mode_value", "Resizable"),
            f'{settings["video_width"]} × {settings["video_height"]}',
            text.get("fps_unlimited", "Unlimited")
            if settings.get("fps_limit", 60) == 0
            else f'{settings.get("fps_limit", 60)} FPS',
        )
        labels = (
            text.get("window_mode", "Window mode"),
            text.get("resolution", "Resolution"),
            text.get("fps_limit", "Frame rate limit"),
            text.get("back", "Back"),
        )
        for index, rect in enumerate(row_rects):
            hovered = mouse_control_active and rect.collidepoint(mouse_pos)
            if hovered and last_hovered != index:
                play_menu_sound("hover")
            if hovered:
                selected_index = index
                last_hovered = index
            color = (65, 50, 40) if index == selected_index else (38, 38, 38)
            pygame.draw.rect(screen, color, rect, border_radius=8)
            label = font.render(labels[index], True, (255, 255, 255))
            screen.blit(label, (rect.x + 18, rect.centery - label.get_height() // 2))
            if index < 3:
                value = font.render(values[index], True, (255, 255, 255))
                screen.blit(value, value.get_rect(midright=(rect.right - 18, rect.centery)))
        if not any(rect.collidepoint(mouse_pos) for rect in row_rects):
            last_hovered = None

        pygame.draw.rect(screen, (70, 70, 70), back_rect, border_radius=8)
        rendered_back = font.render(text.get("back", "Back"), True, (255, 255, 255))
        screen.blit(rendered_back, rendered_back.get_rect(center=back_rect.center))
        hint = hint_font.render(text.get("video_hint", "FPS is a frame limit, not monitor Hz."), True, (170, 170, 170))
        screen.blit(hint, hint.get_rect(center=(screen_width // 2, screen_height - 20)))
        pygame.display.flip()
        clock.tick(FPS)


def settings_sub_menu(screen, font, settings, trans_dict, languages, controls=None, on_change=None):
    selected_index = 0
    clock = pygame.time.Clock()
    last_hovered = None
    mouse_control_active = False

    def apply_change():
        configure_audio(settings)
        if on_change is not None:
            on_change(settings)
        play_menu_sound("click")

    while True:
        language = languages[settings["lang_idx"]]
        text = trans_dict.get(language, {})
        options = [
            text.get("volume", "Volume"),
            f'{text.get("lang", "Language")}: < {language} >',
            text.get("video", "Video"),
            text.get("back", "Back"),
        ]
        screen.fill((20, 20, 20))
        screen_width, screen_height = screen.get_size()
        row_width = min(900, screen_width - 80)
        row_x = (screen_width - row_width) // 2
        rects = [
            pygame.Rect(row_x, screen_height // 2 - 130 + index * 100, row_width, 70)
            for index in range(len(options))
        ]
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.MOUSEMOTION:
                mouse_control_active = True
            elif event.type == pygame.KEYDOWN:
                mouse_control_active = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_control_active = True
            if controls is not None:
                controls.process_event(event)
            if event.type == pygame.QUIT:
                return "EXIT"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    play_menu_sound("click")
                    return "BACK"
                if event.key == pygame.K_UP:
                    selected_index = (selected_index - 1) % len(options)
                    play_menu_sound("hover")
                elif event.key == pygame.K_DOWN:
                    selected_index = (selected_index + 1) % len(options)
                    play_menu_sound("hover")
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT) and selected_index == 1:
                    direction = -1 if event.key == pygame.K_LEFT else 1
                    settings["lang_idx"] = (settings["lang_idx"] + direction) % len(languages)
                    apply_change()
                elif event.key == pygame.K_RETURN:
                    if selected_index == 0:
                        result = _audio_settings_menu(
                            screen, font, settings, trans_dict, languages, controls, on_change
                        )
                        if result == "EXIT":
                            return "EXIT"
                    elif selected_index == 1:
                        settings["lang_idx"] = (settings["lang_idx"] + 1) % len(languages)
                        apply_change()
                    elif selected_index == 2:
                        result = _video_settings_menu(
                            screen, font, settings, trans_dict, languages, controls, on_change
                        )
                        if result in ("EXIT", "VIDEO_CHANGED"):
                            return result
                    else:
                        play_menu_sound("click")
                        return "BACK"

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for index, rect in enumerate(rects):
                    if not rect.collidepoint(event.pos):
                        continue
                    selected_index = index
                    if index == 0:
                        result = _audio_settings_menu(
                            screen, font, settings, trans_dict, languages, controls, on_change
                        )
                        if result == "EXIT":
                            return "EXIT"
                    elif index == 1:
                        settings["lang_idx"] = (settings["lang_idx"] + 1) % len(languages)
                        apply_change()
                    elif index == 2:
                        result = _video_settings_menu(
                            screen, font, settings, trans_dict, languages, controls, on_change
                        )
                        if result in ("EXIT", "VIDEO_CHANGED"):
                            return result
                    else:
                        play_menu_sound("click")
                        return "BACK"
                    break

        for index, option in enumerate(options):
            hovered = mouse_control_active and rects[index].collidepoint(mouse_pos)
            if hovered and last_hovered != index:
                play_menu_sound("hover")
            if hovered:
                selected_index = index
                last_hovered = index
            color = (212, 91, 18) if index == selected_index else (255, 255, 255)
            rendered = font.render(option, True, color)
            screen.blit(rendered, rendered.get_rect(center=rects[index].center))
        if not any(rect.collidepoint(mouse_pos) for rect in rects):
            last_hovered = None

        studio_credit = pygame.font.SysFont("Arial", 16, bold=True).render(
            "Nayra Studio", True, (150, 150, 150)
        )
        screen.blit(studio_credit, studio_credit.get_rect(center=(screen_width // 2, screen_height - 24)))

        pygame.display.flip()
        clock.tick(FPS)


def confirm_dialog(screen, font, small_font, t, controls=None):
    # Add a brief delay before opening the dialog.
    pygame.time.delay(150)

    q_txt = t.get("confirm_q", "Вийти?")
    w_txt = t.get("confirm_w", "Дані буде втрачено")

    selected = 1  # 0 means Yes; 1 means No.
    clock = pygame.time.Clock()
    pygame.mouse.set_visible(True)
    last_hovered = None

    while True:
        screen_width, screen_height = screen.get_size()
        m_pos = pygame.mouse.get_pos()
        m_click = pygame.mouse.get_pressed()[0]  # Left mouse button.

        # 1. Draw the dialog window.
        dr = pygame.Rect(screen_width // 2 - 300, screen_height // 2 - 110, 600, 220)
        pygame.draw.rect(screen, (30, 30, 30), dr)
        pygame.draw.rect(screen, (255, 255, 255), dr, 2)

        # 2. Draw the text.
        q_surf = font.render(q_txt, True, (255, 255, 255))
        w_surf = small_font.render(w_txt, True, (200, 200, 200))
        screen.blit(q_surf, (screen_width // 2 - q_surf.get_width() // 2, screen_height // 2 - 80))
        screen.blit(w_surf, (screen_width // 2 - w_surf.get_width() // 2, screen_height // 2 - 30))

        # 3. Draw the buttons.
        by = pygame.Rect(screen_width // 2 - 130, screen_height // 2 + 40, 100, 50)  # Yes button.
        bn = pygame.Rect(screen_width // 2 + 30, screen_height // 2 + 40, 100, 50)  # No button.

        # --- Mouse handling ---
        hovered = 0 if by.collidepoint(m_pos) else 1 if bn.collidepoint(m_pos) else None
        if hovered != last_hovered:
            if hovered is not None:
                play_menu_sound("hover")
            last_hovered = hovered
        if hovered is not None:
            selected = hovered
            if m_click:
                play_menu_sound("click")
                return selected == 0

        # 4. Draw the selected option.
        y_col = (0, 200, 0) if selected == 0 else (0, 80, 0)
        n_col = (200, 0, 0) if selected == 1 else (80, 0, 0)

        pygame.draw.rect(screen, y_col, by)
        pygame.draw.rect(screen, n_col, bn)

        # Outline the selected option.
        active_rect = by if selected == 0 else bn
        pygame.draw.rect(screen, (255, 255, 255), active_rect, 3)

        yes_label = small_font.render(t.get("yes", "YES"), True, (255, 255, 255))
        no_label = small_font.render(t.get("no", "NO"), True, (255, 255, 255))
        screen.blit(yes_label, yes_label.get_rect(center=by.center))
        screen.blit(no_label, no_label.get_rect(center=bn.center))

        pygame.display.flip()

        # 5. Handle keyboard events.
        for event in pygame.event.get():
            if controls is not None:
                controls.process_event(event)
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_LEFT, pygame.K_RIGHT] or (
                    controls is not None and (
                        controls.matches(event, pygame.K_a) or controls.matches(event, pygame.K_d)
                    )
                ):
                    selected = 1 - selected
                    play_menu_sound("hover")
                if event.key == pygame.K_RETURN:
                    play_menu_sound("click")
                    return selected == 0
                if event.key == pygame.K_ESCAPE:
                    play_menu_sound("click")
                    return False

        clock.tick(FPS)
def draw_debug_coords(screen, target, mode_label):
    """Draw the target's world coordinates for debugging."""
    if target is None:
        return
    position = getattr(target, "pos", None)
    if position is None:
        return
    try:
        debug_f = pygame.font.SysFont("Consolas", 20, bold=True)
    except pygame.error:
        debug_f = pygame.font.SysFont("Arial", 20)

    curr_x = int(position.x)
    curr_y = int(position.y)

    debug_text = f"X: {curr_x} Y: {curr_y} | MODE: {mode_label}"
    txt_surf = debug_f.render(debug_text, True, (255, 255, 0))

    # Text background.
    bg_rect = pygame.Rect(10, 10, txt_surf.get_width() + 10, 30)
    bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
    bg_surf.fill((0, 0, 0, 180))

    screen.blit(bg_surf, (10, 10))
    screen.blit(txt_surf, (15, 15))


def full_screen_map(screen, map_img, target, world_w, world_h, house_pos=(7738, 2325), controls=None):
    """Draw the zoomable full-screen map and its icons."""
    house_icon = _get_house_icon()

    screen_width, screen_height = screen.get_size()
    map_zoom = 1.0
    map_off_x, map_off_y = 0, 0
    clock = pygame.time.Clock()
    running = True

    while running:
        screen.fill((20, 20, 20))
        for event in pygame.event.get():
            if controls is not None:
                controls.process_event(event)
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.MOUSEWHEEL:
                map_zoom += event.y * 0.1
                map_zoom = max(1.0, min(5.0, map_zoom))
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_TAB, pygame.K_ESCAPE]:
                    running = False

        scaled_w, scaled_h = int(screen_width * map_zoom), int(screen_height * map_zoom)
        keys = controls if controls is not None else pygame.key.get_pressed()
        move_speed = 15 / map_zoom

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:  map_off_x += move_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: map_off_x -= move_speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:    map_off_y += move_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:  map_off_y -= move_speed

        limit_x, limit_y = (scaled_w - screen_width) // 2, (scaled_h - screen_height) // 2
        if limit_x > 0:
            map_off_x = max(-limit_x, min(limit_x, map_off_x))
        else:
            map_off_x = 0
        if limit_y > 0:
            map_off_y = max(-limit_y, min(limit_y, map_off_y))
        else:
            map_off_y = 0

        map_rect = pygame.Rect(0, 0, scaled_w, scaled_h)
        map_rect.center = (screen_width // 2 + map_off_x, screen_height // 2 + map_off_y)

        temp_map = pygame.transform.scale(map_img, (scaled_w, scaled_h))
        screen.blit(temp_map, map_rect.topleft)

        def world_to_map(wx, wy):
            mx = (wx / world_w) * scaled_w + map_rect.left
            my = (wy / world_h) * scaled_h + map_rect.top
            return int(mx), int(my)

        # House icon.
        hx, hy = world_to_map(house_pos[0], house_pos[1])
        if house_icon is not None:
            i_size = int(24 * map_zoom)
            s_haus = pygame.transform.scale(house_icon, (i_size, i_size))
            screen.blit(s_haus, (hx - i_size // 2, hy - i_size // 2))
        else:
            pygame.draw.circle(screen, (0, 0, 255), (hx, hy), int(10 * map_zoom))

        # Player marker.
        px, py = world_to_map(target.pos.x, target.pos.y)
        pygame.draw.circle(screen, (255, 0, 0), (px, py), int(8 * map_zoom))
        pygame.draw.circle(screen, (255, 255, 255), (px, py), int(8 * map_zoom), 2)

        pygame.display.flip()
        clock.tick(FPS)

def draw_city_hints(screen, small_font, atom, car, t):
    """Draw interaction hints near the car and house in the city."""
    dist_car = atom.pos.distance_to(car.pos)
    dist_house = atom.pos.distance_to(pygame.Vector2(7738, 2330))

    if dist_car < 100:
        msg = t["hint"].replace("[E]", "[F]")
        txt = small_font.render(msg, True, (255, 255, 255))
        screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT - 120))

    if dist_house < 80:
        txt = small_font.render(t["enter"], True, (255, 255, 0))
        screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT - 160))

def draw_house_scene(screen, house_visual, house_info, atom_h, small_font, t):
    """Draw the interior scene and check the exit area."""
    screen.fill((10, 10, 10))
    h_rect = house_visual.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(house_visual, h_rect)

    # Draw the character relative to the house center.
    atom_h.draw(screen, h_rect.x, h_rect.y)

    px, py = int(atom_h.pos.x), int(atom_h.pos.y)
    if house_info.get_rect().collidepoint(px, py):
        color_at_feet = house_info.get_at((px, py))[:3]
        if color_at_feet == (153, 229, 80):
            txt = small_font.render(t["exit"], True, (255, 255, 0))
            screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT - 100))

def handle_car_logic(atom, car, in_car):
    """Handle entering and leaving the car with the F key."""
    if not in_car and atom.pos.distance_to(car.pos) < 100:
        return True # The player enters the car.
    elif in_car:
        atom.pos = car.pos + pygame.Vector2(60, 0)
        return False # The player leaves the car.
    return in_car
def check_house_exit(atom_h, house_info):
    px, py = int(atom_h.pos.x), int(atom_h.pos.y)
    if not house_info.get_rect().collidepoint(px, py):
        return False
    return house_info.get_at((px, py))[:3] == (153, 229, 80)


def handle_surface_footsteps(keys, in_car, game_state, pos, col_mask, sounds, channel):
    # Play footsteps only while moving on foot.
    is_moving = any(keys[k] for k in [
        pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,
        pygame.K_UP, pygame.K_LEFT, pygame.K_DOWN, pygame.K_RIGHT,
    ])

    if not is_moving or in_car:
        channel.stop()
        return

    target_sound = None

    if game_state == "HOUSE":
        target_sound = sounds['house']  # Use the wood footsteps sound.

    elif game_state == "CITY":
        if col_mask is not None:
            mask_x, mask_y = int(pos.x), int(pos.y)
            if col_mask.get_rect().collidepoint(mask_x, mask_y):
                color = col_mask.get_at((mask_x, mask_y))[:3]
            else:
                color = None
        else:
            color = None

        if color is not None:
            if color == (255, 242, 0):  # Yellow represents asphalt.
                target_sound = sounds['asphalt']
            elif color == (185, 122, 87):  # Brown represents dirt.
                target_sound = sounds['dirt']
            elif color == (27, 56, 0):  # Green represents grass.
                target_sound = sounds['grass']
            else:
                target_sound = sounds['asphalt']  # Use the default asphalt sound.
        else:
            target_sound = sounds['asphalt']

    # Play the selected sound if the channel is idle.
    if target_sound and not channel.get_busy():
        channel.play(target_sound)
def handle_car_audio(car, in_car, sounds, e_chan, c_chan, controls=None):
    if not in_car:
        e_chan.stop()
        return

    # 1. Engine audio.
    if not e_chan.get_busy():
        e_chan.play(sounds['engine'], loops=-1)

    # Adjust volume based on speed.
    vol = min(0.6, 0.2 + (abs(car.speed) / 20.0))
    e_chan.set_volume(vol)

    # 2. Horn audio.
    keys = controls if controls is not None else pygame.key.get_pressed()
    if keys[pygame.K_h]:
        # Use a separate channel so the horn does not interrupt the engine.
        # The horn may overlap other sounds on its channel.
        if not pygame.mixer.Channel(4).get_busy():
            pygame.mixer.Channel(4).play(sounds['beep'])

    # 3. Crash audio.
    if getattr(car, 'just_hit', False):
        if not c_chan.get_busy():
            c_chan.play(sounds['crash'])
        car.just_hit = False

def get_ambient_color(game_time_minutes):
    """
    game_time_minutes: Time in minutes, from 0 to 1440.
    Return the (red, green, blue, alpha) overlay color.
    """
    h = game_time_minutes / 60.0

    # Daytime (08:00–18:00) is fully lit.
    if 8 <= h < 18:
        return (0, 0, 0, 0)
    # Night (21:00–05:00) uses a dark blue overlay.
    elif h >= 21 or h < 5:
        return (15, 15, 40, 160)
    # Dawn and dusk use a gradual transition.
    else:
        if 5 <= h < 8:  # Morning.
            factor = (h - 5) / 3.0
        else:  # Evening (18:00–21:00).
            factor = 1.0 - (h - 18) / 3.0

        # A lower factor produces a darker overlay.
        alpha = int(160 * (1.0 - factor))
        return (15, 15, 40, alpha)
def draw_car_smoke(screen, car, off_x, off_y):
    """Draw the car smoke particles using the camera offset."""
    # Use a temporary surface for alpha blending.
    smoke_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    for p in car.smoke_particles:
        x, y, r, alpha, _vy, _life = p

        # Convert world coordinates to screen coordinates.
        screen_x = int(x + off_x)
        screen_y = int(y + off_y)

        # Skip particles that are outside the screen.
        if -r < screen_x < WIDTH + r and -r < screen_y < HEIGHT + r:
            # Choose gray or black smoke based on the car condition.
            # Particle values: x, y, radius, alpha, vertical speed, lifetime.
            # The particle does not store its color.
            # Select the color here based on the car health.

            # Use gray by default for a simple smoke effect.
            color_val = 150
            if car.health < car.max_health * 0.2:
                color_val = 50 # Use black smoke when the car is badly damaged.

            # Draw the particle on the temporary surface.
            pygame.draw.circle(smoke_surf, (color_val, color_val, color_val, int(alpha)), (screen_x, screen_y), int(r))

    # Blit the smoke surface onto the screen.
    screen.blit(smoke_surf, (0, 0))


# 1. Phone settings storage.
def get_phone_settings():
    path = Path(__file__).resolve().parent / "phone_settings.json"
    default_settings = {
        "bg_idx": 0,
        "case_idx": 0,
        "owner": "Atom"
    }
    if not path.exists():
        path.write_text(json.dumps(default_settings), encoding="utf-8")
        return default_settings
    return json.loads(path.read_text(encoding="utf-8"))


def save_phone_settings(settings):
    path = Path(__file__).resolve().parent / "phone_settings.json"
    path.write_text(json.dumps(settings), encoding="utf-8")


# 2. Color palettes.
BG_PALETTE = [(10, 10, 30), (60, 20, 20), (20, 60, 20), (40, 40, 40), (100, 50, 10)]
CASE_PALETTE = [(30, 30, 30), (200, 200, 200), (0, 120, 255), (255, 215, 0), (255, 0, 100)]


# 3. Phone rendering.
PHONE_TRANSLATIONS = {
    "English": {
        "bank": "Triple1 Bank", "history": "Recent transactions:",
        "start": "Starting balance", "guard": "By the guard", "bridge": "By the bridge",
        "repair": "Repair", "nightstand": "Nightstand", "sofa": "On the sofa",
        "settings_app": "Settings", "phone_settings": "Phone settings", "phone_color": "Phone color",
        "choose_color": "Press 1–5 to choose", "colors": ["Black", "Silver", "Blue", "Gold", "Pink"],
    },
    "Українська": {
        "bank": "Банк Triple1", "history": "Останні транзакції:",
        "start": "Стартовий баланс", "guard": "Біля охоронця", "bridge": "Коло мосту",
        "repair": "Ремонт", "nightstand": "Тумбочка", "sofa": "На дивані",
        "settings_app": "Налаштування", "phone_settings": "Налаштування телефона", "phone_color": "Колір телефона",
        "choose_color": "Натисни 1–5, щоб вибрати", "colors": ["Чорний", "Сріблястий", "Синій", "Золотий", "Рожевий"],
    },
    "Русский": {
        "bank": "Банк Triple1", "history": "Последние транзакции:",
        "start": "Стартовый баланс", "guard": "У охранника", "bridge": "У моста",
        "repair": "Ремонт", "nightstand": "Тумбочка", "sofa": "На диване",
        "settings_app": "Настройки", "phone_settings": "Настройки телефона", "phone_color": "Цвет телефона",
        "choose_color": "Нажми 1–5 для выбора", "colors": ["Чёрный", "Серебристый", "Синий", "Золотой", "Розовый"],
    },
    "Español": {
        "bank": "Banco Triple1", "history": "Transacciones recientes:",
        "start": "Saldo inicial", "guard": "Junto al guardia", "bridge": "Junto al puente",
        "repair": "Reparación", "nightstand": "Mesita de noche", "sofa": "En el sofá",
        "settings_app": "Ajustes", "phone_settings": "Ajustes del teléfono", "phone_color": "Color del teléfono",
        "choose_color": "Pulsa 1–5 para elegir", "colors": ["Negro", "Plateado", "Azul", "Dorado", "Rosa"],
    },
    "Deutsch": {
        "bank": "Triple1 Bank", "history": "Letzte Transaktionen:",
        "start": "Anfangsguthaben", "guard": "Beim Wachmann", "bridge": "Bei der Brücke",
        "repair": "Reparatur", "nightstand": "Nachttisch", "sofa": "Auf dem Sofa",
        "settings_app": "Einstellungen", "phone_settings": "Telefoneinstellungen", "phone_color": "Telefonfarbe",
        "choose_color": "1–5 zum Auswählen", "colors": ["Schwarz", "Silber", "Blau", "Gold", "Pink"],
    },
    "Français": {
        "bank": "Banque Triple1", "history": "Transactions récentes :",
        "start": "Solde initial", "guard": "Près du garde", "bridge": "Près du pont",
        "repair": "Réparation", "nightstand": "Table de chevet", "sofa": "Sur le canapé",
        "settings_app": "Réglages", "phone_settings": "Réglages du téléphone", "phone_color": "Couleur du téléphone",
        "choose_color": "Appuie sur 1–5", "colors": ["Noir", "Argent", "Bleu", "Or", "Rose"],
    },
}


def draw_mobile_phone(screen, money, game_time, font_small, current_app, phone_settings,
                      phone_y_offset, money_history, language="English"):
    width, height = screen.get_size()
    labels = PHONE_TRANSLATIONS.get(language, PHONE_TRANSLATIONS["English"])
    p_w, p_h = 220, 400

    # Calculate the phone position; p_y changes during the slide animation.
    p_x = width - p_w - 20
    p_y = height - p_h - 20 + phone_y_offset

    # 1. Phone body and display.
    case_col = CASE_PALETTE[phone_settings["case_idx"]]
    pygame.draw.rect(screen, case_col, (p_x, p_y, p_w, p_h), border_radius=25)

    # Keep the display aligned with p_y.
    display_rect = pygame.Rect(p_x + 10, p_y + 10, p_w - 20, p_h - 20)
    pygame.draw.rect(screen, BG_PALETTE[phone_settings["bg_idx"]], display_rect, border_radius=15)

    # 2. Status bar (battery and signal).
    signal_bars = 4 if 480 < game_time < 1200 else 2
    for i in range(4):
        bar_h = 5 + (i * 3)
        color = (255, 255, 255) if i < signal_bars else (80, 80, 80)
        # Position these elements relative to display_rect.y, including the offset.
        pygame.draw.rect(screen, color, (display_rect.x + 10 + (i * 5), display_rect.y + 12, 3, bar_h))

    # Battery indicator.
    pygame.draw.rect(screen, (255, 255, 255), (display_rect.right - 35, display_rect.y + 7, 25, 12), 1)
    bat_color = (0, 255, 0) if signal_bars > 2 else (255, 50, 50)
    pygame.draw.rect(screen, bat_color, (display_rect.right - 33, display_rect.y + 9, 18, 8))

    # 3. Apps.
    if current_app == 0:
        icon_x, icon_y = display_rect.x + 20, display_rect.y + 50
        pygame.draw.rect(screen, (80, 80, 120), (icon_x, icon_y, 45, 45), border_radius=10)
        screen.blit(font_small.render("1", True, (255, 255, 255)), (icon_x + 15, icon_y + 10))
        name_surf = pygame.font.SysFont("Arial", 12, bold=True).render("Triple1", True, (220, 220, 220))
        screen.blit(name_surf, (icon_x, icon_y + 50))

        settings_x = display_rect.x + 95
        pygame.draw.rect(screen, (55, 105, 100), (settings_x, icon_y, 45, 45), border_radius=10)
        screen.blit(font_small.render("2", True, (255, 255, 255)), (settings_x + 15, icon_y + 10))
        settings_name = pygame.font.SysFont("Arial", 11, bold=True).render(
            labels["settings_app"], True, (220, 220, 220)
        )
        screen.blit(settings_name, (settings_x, icon_y + 50))

    elif current_app == 1:
        # Position all text relative to display_rect.y.
        bank_label = font_small.render(labels["bank"], True, (255, 215, 0))
        screen.blit(bank_label, (display_rect.x + 15, display_rect.y + 40))

        balance_surf = font_small.render(f"{money} UAH", True, (0, 255, 0))
        screen.blit(balance_surf, (display_rect.x + 15, display_rect.y + 75))

        # Transaction history.
        # Important: calculate y_hist relative to display_rect.y.
        y_hist = display_rect.y + 130
        history_title = pygame.font.SysFont("Arial", 12, bold=True).render(labels["history"], True, (150, 150, 150))
        screen.blit(history_title, (display_rect.x + 15, y_hist))

        for item in money_history[-3:]:
            y_hist += 25
            label = labels.get(item[1], item[1])
            txt = pygame.font.SysFont("Arial", 12).render(f"{item[0]} - {label}", True, (200, 200, 200))
            screen.blit(txt, (display_rect.x + 15, y_hist))

    elif current_app == 2:
        title = pygame.font.SysFont("Arial", 16, bold=True).render(
            labels["phone_settings"], True, (255, 255, 255)
        )
        screen.blit(title, (display_rect.x + 15, display_rect.y + 45))

        category = pygame.font.SysFont("Arial", 13, bold=True).render(
            labels["phone_color"], True, (190, 190, 190)
        )
        screen.blit(category, (display_rect.x + 15, display_rect.y + 90))

        selected_idx = phone_settings["case_idx"]
        swatch_y = display_rect.y + 125
        for idx, color in enumerate(CASE_PALETTE):
            swatch = pygame.Rect(display_rect.x + 16 + idx * 35, swatch_y, 27, 27)
            pygame.draw.rect(screen, color, swatch, border_radius=6)
            border_color = (255, 215, 0) if idx == selected_idx else (180, 180, 180)
            border_width = 3 if idx == selected_idx else 1
            pygame.draw.rect(screen, border_color, swatch, border_width, border_radius=6)
            number = pygame.font.SysFont("Arial", 11, bold=True).render(str(idx + 1), True, (235, 235, 235))
            screen.blit(number, (swatch.x + 10, swatch.bottom + 5))

        selected_name = pygame.font.SysFont("Arial", 14, bold=True).render(
            labels["colors"][selected_idx], True, (255, 255, 255)
        )
        screen.blit(selected_name, (display_rect.x + 15, display_rect.y + 175))

        hint = pygame.font.SysFont("Arial", 11).render(
            labels["choose_color"], True, (165, 165, 165)
        )
        screen.blit(hint, (display_rect.x + 15, display_rect.y + 220))
