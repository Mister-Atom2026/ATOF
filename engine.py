import json
import math
import random
import time
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
import sys
from typing import Callable, Mapping, Optional

import pygame

import constants as _constants
from settings_manager import (
    load_game_save,
    load_statistics,
    save_game_save,
    save_settings,
    save_statistics,
)
import traffic

WIDTH = _constants.WIDTH
HEIGHT = _constants.HEIGHT
FPS = _constants.FPS
WORLD_WIDTH = _constants.WORLD_WIDTH
WORLD_HEIGHT = _constants.WORLD_HEIGHT
HOUSE_SLEEP_SPOT = _constants.HOUSE_SLEEP_SPOT
SUPPORTED_LANGUAGES = (
    "English",
    "Українська",
    "Русский",
    "Español",
    "Deutsch",
    "Français",
)

_menu_sounds: dict[str, Optional[pygame.mixer.Sound]] = {}
_house_icon: Optional[pygame.Surface] = None
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
_ASSET_ROOT = Path(__file__).resolve().parent
_image_cache: dict[tuple[Path, bool], pygame.Surface] = {}


def load_image(relative_path: str, *, alpha: bool = False) -> pygame.Surface:
    path = (_ASSET_ROOT / relative_path).resolve()
    key = (path, alpha)
    if key not in _image_cache:
        image = pygame.image.load(str(path))
        _image_cache[key] = image.convert_alpha() if alpha else image.convert()
    return _image_cache[key]


class FrameClock:
    """Provide a bounded, frame-rate-independent simulation step."""

    def __init__(self):
        self._last_frame_time = time.perf_counter()

    def tick(self, clock: pygame.time.Clock, fps: int) -> float:
        clock.tick(fps)
        now = time.perf_counter()
        frame_scale = (now - self._last_frame_time) * 60
        self._last_frame_time = now
        return max(0.05, min(frame_scale, 3.0))

    def reset(self) -> None:
        self._last_frame_time = time.perf_counter()


class Camera2D:
    """Clamp a world-follow camera and convert between world and screen points."""

    def __init__(self, viewport_size: tuple[int, int], world_size: tuple[int, int]):
        self.viewport_size = pygame.Vector2(viewport_size)
        self.world_size = pygame.Vector2(world_size)
        self.offset = pygame.Vector2()

    def resize(self, viewport_size: tuple[int, int]) -> None:
        self.viewport_size.update(viewport_size)

    def follow(self, world_position) -> tuple[float, float]:
        position = pygame.Vector2(world_position)
        self.offset.update(
            max(-(self.world_size.x - self.viewport_size.x),
                min(0, self.viewport_size.x / 2 - position.x)),
            max(-(self.world_size.y - self.viewport_size.y),
                min(0, self.viewport_size.y / 2 - position.y)),
        )
        return self.offset.x, self.offset.y

    def world_to_screen(self, world_position) -> pygame.Vector2:
        return pygame.Vector2(world_position) + self.offset

    def screen_to_world(self, screen_position) -> pygame.Vector2:
        return pygame.Vector2(screen_position) - self.offset


class SceneManager:
    """Own the active scene identifier and its registered lifecycle hooks."""

    def __init__(self, initial_scene: str):
        self.current = initial_scene
        self.previous: Optional[str] = None
        self._hooks: dict[str, tuple[Optional[Callable], Optional[Callable]]] = {}

    def register(self, scene: str, *, on_enter=None, on_exit=None) -> None:
        self._hooks[scene] = (on_enter, on_exit)

    def transition(self, scene: str, context=None) -> bool:
        if scene == self.current:
            return False
        if scene not in self._hooks:
            raise KeyError(f"Unregistered scene: {scene}")
        previous = self.current
        _enter, on_exit = self._hooks.get(previous, (None, None))
        on_enter, _exit = self._hooks[scene]
        if on_exit is not None:
            on_exit(scene, context)
        self.previous, self.current = previous, scene
        if on_enter is not None:
            on_enter(previous, context)
        return True


class RenderLayer(IntEnum):
    BACKGROUND = 0
    WORLD = 10
    LIGHTING = 20
    UI = 30


class LayeredRenderer:
    """Execute frame draw callbacks in a stable, explicit layer order."""

    def __init__(self):
        self._commands: list[tuple[RenderLayer, int, Callable[[], None]]] = []
        self._sequence = 0

    def begin_frame(self) -> None:
        self._commands.clear()
        self._sequence = 0

    def submit(self, layer: RenderLayer, draw: Callable[[], None]) -> None:
        self._commands.append((layer, self._sequence, draw))
        self._sequence += 1

    def render(self) -> None:
        for _layer, _sequence, draw in sorted(self._commands):
            draw()


PHYSICAL_SCANCODES = {
    getattr(pygame, f"K_{letter}"): getattr(pygame, f"KSCAN_{letter.upper()}")
    for letter in "abcdefghijklmnopqrstuvwxyz"
    if hasattr(pygame, f"K_{letter}") and hasattr(pygame, f"KSCAN_{letter.upper()}")
}
PHYSICAL_SCANCODES.update({
    getattr(pygame, f"K_{number}"): getattr(pygame, f"KSCAN_{number}")
    for number in "0123456789"
    if hasattr(pygame, f"K_{number}") and hasattr(pygame, f"KSCAN_{number}")
})
PHYSICAL_SCANCODES.update({
    getattr(pygame, key_name): getattr(pygame, scancode_name)
    for key_name, scancode_name in (
        ("K_COMMA", "KSCAN_COMMA"),
        ("K_PERIOD", "KSCAN_PERIOD"),
    )
    if hasattr(pygame, key_name) and hasattr(pygame, scancode_name)
})


class KeyboardState:
    """Drop-in key-state reader with layout-independent WASD movement."""

    def __init__(self):
        self._pressed_scancodes = set()

    def process_event(self, event):
        if event.type == pygame.KEYDOWN:
            scancode = getattr(event, "scancode", None)
            if scancode is not None:
                self._pressed_scancodes.add(scancode)
        elif event.type == pygame.KEYUP:
            scancode = getattr(event, "scancode", None)
            if scancode is not None:
                self._pressed_scancodes.discard(scancode)
        elif event.type == getattr(pygame, "WINDOWFOCUSLOST", -1):
            self._pressed_scancodes.clear()

    def __getitem__(self, key):
        scancode = PHYSICAL_SCANCODES.get(key)
        if scancode is not None and scancode in self._pressed_scancodes:
            return True
        try:
            return bool(pygame.key.get_pressed()[key])
        except (IndexError, TypeError):
            return False

    @staticmethod
    def matches(event, key):
        """Match a KEYDOWN to its US-layout key position or its reported key."""
        if getattr(event, "key", None) == key:
            return True
        scancode = PHYSICAL_SCANCODES.get(key)
        return scancode is not None and getattr(event, "scancode", None) == scancode


class GPS:
    def __init__(self) -> None:
        self.destination: tuple[float, float] | None = None

    @staticmethod
    def get_dist(
        first: tuple[float, float],
        second: tuple[float, float],
    ) -> float:
        return math.hypot(first[0] - second[0], first[1] - second[1])

    def set_destination(self, target_pos: tuple[float, float]) -> None:
        self.destination = (float(target_pos[0]), float(target_pos[1]))

    def clear_destination(self) -> None:
        self.destination = None

    def distance_to(self, position: tuple[float, float]) -> float | None:
        if self.destination is None:
            return None
        return self.get_dist(position, self.destination)


class HousePlayer:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.speed = 4
        self.angle = 0
        self.image = None
        try:
            raw = load_image("characters/atom.png", alpha=True)
            self.image = pygame.transform.scale(raw, (48, 48))
        except (pygame.error, OSError) as exc:
            print(f"Помилка завантаження characters/atom.png для хати: {exc}")

    def update(self, keys, col_mask, frame_scale=1.0):
        move = pygame.Vector2(0, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y = -1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y = 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x = -1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x = 1
        if move.length() == 0:
            return

        move = move.normalize() * self.speed * frame_scale
        new_pos = self.pos + move
        x, y = int(new_pos.x), int(new_pos.y)
        if 0 <= x < col_mask.get_width() and 0 <= y < col_mask.get_height():
            if col_mask.get_at((x, y))[:3] != (0, 0, 0):
                self.pos = new_pos

        if move.x > 0 and move.y == 0:
            self.angle = -90
        elif move.x < 0 and move.y == 0:
            self.angle = 90
        elif move.y > 0 and move.x == 0:
            self.angle = 0
        elif move.y < 0 and move.x == 0:
            self.angle = 180
        elif move.x > 0 and move.y > 0:
            self.angle = -45
        elif move.x < 0 < move.y:
            self.angle = 45
        elif move.x > 0 > move.y:
            self.angle = -135
        elif move.x < 0 and move.y < 0:
            self.angle = 135

    def draw(self, screen, offset_x, offset_y):
        if not self.image:
            return
        rotated = pygame.transform.rotate(self.image, -self.angle)
        rect = rotated.get_rect(
            center=(int(self.pos.x + offset_x), int(self.pos.y + offset_y))
        )
        screen.blit(rotated, rect)


@dataclass(frozen=True)
class GameAssets:
    atom: pygame.Surface
    original_nav_map: pygame.Surface
    world_background: pygame.Surface
    full_map: pygame.Surface
    collision_mask: pygame.Surface
    house_visual: pygame.Surface
    house_collision: pygame.Surface
    house_info: pygame.Surface


@dataclass(frozen=True)
class GameResources:
    assets: GameAssets
    audio: "GameAudio"
    game_font: pygame.font.Font
    small_font: pygame.font.Font


@dataclass(frozen=True)
class GameAudio:
    phone_click: pygame.mixer.Sound
    car_sounds: dict[str, pygame.mixer.Sound]
    footsteps: dict[str, pygame.mixer.Sound]
    weapon_sounds: dict[str, pygame.mixer.Sound]
    engine_channel: pygame.mixer.Channel
    crash_channel: pygame.mixer.Channel
    footstep_channel: pygame.mixer.Channel
    horn_channel: pygame.mixer.Channel


def load_game_assets(
    screen_size: tuple[int, int],
    world_size: tuple[int, int],
    house_scale: int = 3,
) -> GameAssets:
    """Load and prepare the shared city, house, and character assets."""
    atom = load_image("characters/atom.png", alpha=True)
    original_nav_map = load_image("world/Карта Вишневого.png")
    original_background = load_image("world/НОРМ Карта Вишневого.png")
    world_background = pygame.transform.scale(original_background, world_size)
    full_map = pygame.transform.scale(original_nav_map, screen_size)
    collision_mask = pygame.transform.scale(
        load_image("world/Нізя їздити.png"),
        world_size,
    )

    house_visual = load_image("ch_home/hm.png")
    house_size = (
        house_visual.get_width() * house_scale,
        house_visual.get_height() * house_scale,
    )
    house_visual = pygame.transform.scale(house_visual, house_size)
    house_collision = pygame.transform.scale(load_image("ch_home/hkm.png"), house_size)
    house_info = pygame.transform.scale(load_image("ch_home/him.png"), house_size)

    return GameAssets(
        atom=atom,
        original_nav_map=original_nav_map,
        world_background=world_background,
        full_map=full_map,
        collision_mask=collision_mask,
        house_visual=house_visual,
        house_collision=house_collision,
        house_info=house_info,
    )


def load_game_resources(
    screen_size: tuple[int, int],
    world_size: tuple[int, int],
) -> GameResources:
    """Load the prepared world visuals, audio, and fonts."""
    audio = load_game_audio()
    assets = load_game_assets(screen_size, world_size)
    game_font, small_font = load_game_fonts()
    return GameResources(
        assets=assets,
        audio=audio,
        game_font=game_font,
        small_font=small_font,
    )


def load_game_audio() -> GameAudio:
    """Create game sound effects and dedicated mixer channels."""
    sound_root = _ASSET_ROOT / "sounds"

    def load_sound(filename: str) -> pygame.mixer.Sound:
        return pygame.mixer.Sound(str(sound_root / filename))

    phone_click = load_sound("click.wav")
    car_sounds = {
        "engine": load_sound("car_engine.wav"),
        "crash": load_sound("car_crash.wav"),
        "beep": load_sound("beep.wav"),
        "door_open": load_sound("cd_open.wav"),
        "door_close": load_sound("cd_close.wav"),
    }
    footsteps = {
        "asphalt": load_sound("footstep_on_stone.wav"),
        "dirt": load_sound("footstep_on_dirt.wav"),
        "grass": load_sound("footstep_on_grass.wav"),
        "house": load_sound("footstep_on_wood.wav"),
    }
    weapon_sounds = {}
    try:
        weapon_sounds["pistol_reload"] = load_sound("pistol_reload.wav")
    except (pygame.error, OSError):
        pass
    try:
        weapon_sounds["shotgun_reload"] = load_sound("shotgun_reload.wav")
    except (pygame.error, OSError):
        pass
    try:
        weapon_sounds["rifle_reload"] = load_sound("rifle_reload.wav")
    except (pygame.error, OSError):
        pass
    try:
        weapon_sounds["smg_reload"] = load_sound("smg_reload.wav")
    except (pygame.error, OSError):
        pass

    phone_click.set_volume(0.4)
    car_sounds["engine"].set_volume(0.3)
    car_sounds["crash"].set_volume(0.5)
    car_sounds["beep"].set_volume(0.4)
    car_sounds["door_open"].set_volume(0.5)
    car_sounds["door_close"].set_volume(0.5)
    for sound in footsteps.values():
        sound.set_volume(0.2)

    return GameAudio(
        phone_click=phone_click,
        car_sounds=car_sounds,
        footsteps=footsteps,
        weapon_sounds=weapon_sounds,
        engine_channel=pygame.mixer.Channel(6),
        crash_channel=pygame.mixer.Channel(7),
        footstep_channel=pygame.mixer.Channel(5),
        horn_channel=pygame.mixer.Channel(4),
    )


def load_game_fonts() -> tuple[pygame.font.Font, pygame.font.Font]:
    """Load the game fonts, falling back to system fonts if needed."""
    font_path = str(_ASSET_ROOT / "static.ttf")
    try:
        return pygame.font.Font(font_path, 40), pygame.font.Font(font_path, 25)
    except (pygame.error, OSError):
        return (
            pygame.font.SysFont("Arial", 40, bold=True),
            pygame.font.SysFont("Arial", 25),
        )


def is_at_sleep_spot(game_state, position) -> bool:
    return (
        game_state == "HOUSE"
        and pygame.Vector2(position).distance_to(_constants.HOUSE_SLEEP_SPOT) < _constants.HOUSE_SLEEP_RADIUS
    )


def configure_game_audio(settings, audio: GameAudio) -> None:
    """Apply saved audio levels to the game's sound effects."""
    configure_audio(settings)

    button_gain = settings.get("button_volume", 100) / 100
    crash_gain = settings.get("crash_volume", 100) / 100
    footsteps_gain = settings.get("footsteps_volume", 100) / 100
    audio.phone_click.set_volume(0.4 * button_gain)
    audio.car_sounds["beep"].set_volume(0.4 * button_gain)
    audio.car_sounds["door_open"].set_volume(0.5 * button_gain)
    audio.car_sounds["door_close"].set_volume(0.5 * button_gain)
    audio.car_sounds["crash"].set_volume(0.5 * crash_gain)
    for sound in audio.footsteps.values():
        sound.set_volume(0.2 * footsteps_gain)


@dataclass(frozen=True)
class RadioTrack:
    title: str
    path: str
    duration: float


@dataclass(frozen=True)
class RadioStation:
    name: str
    genre_key: str
    tracks: tuple[RadioTrack, ...]


_RADIO_STATIONS = (
    RadioStation(
        "Asphalt FM",
        "radio_genre_rock",
        (
            RadioTrack("Sidewalk Talk", "radio/asphalt_fm/sidewalk_talk.ogg", 262.68),
            RadioTrack("rooms for music.", "radio/asphalt_fm/rooms_for_music.mp3", 200.280816),
        ),
    ),
    RadioStation(
        "Night Shift 88",
        "radio_genre_synthwave",
        (
            RadioTrack("All The Fight Left!", "radio/night_shift/all_the_fight_left.mp3", 171.984),
            RadioTrack("Soft and Furious - 02 - Queen", "radio/night_shift/soft_and_furious_queen.ogg", 205.427982),
        ),
    ),
    RadioStation(
        "НРК — Народне Радіо",
        "radio_genre_folk",
        (
            RadioTrack("Medieval Theme", "radio/nrk/medieval_theme.mp3", 146.416327),
            RadioTrack("Kings Feast", "radio/nrk/kings_feast.mp3", 130.0563),
        ),
    ),
)


class GameRadio:
    """Play stations as live playlists whose clocks keep running while tuned away."""

    def __init__(self, settings, *, monotonic_clock=None):
        self.settings = settings
        self.monotonic_clock = monotonic_clock or time.monotonic
        self.started_at = self.monotonic_clock()
        self.station_index = 0
        self.is_on = False
        self.is_playing = False
        self._paused_for_game = False
        self._loaded_track: tuple[int, int] | None = None

    @property
    def station_name(self) -> str:
        return _RADIO_STATIONS[self.station_index].name

    @property
    def station_genre_key(self) -> str:
        return _RADIO_STATIONS[self.station_index].genre_key

    @property
    def track_name(self) -> str:
        station = _RADIO_STATIONS[self.station_index]
        track_index, _offset = self._live_track_position(self.station_index)
        return station.tracks[track_index].title

    def _live_track_position(self, station_index: int, now: float | None = None) -> tuple[int, float]:
        station = _RADIO_STATIONS[station_index]
        now = self.monotonic_clock() if now is None else now
        playlist_duration = sum(track.duration for track in station.tracks)
        playlist_position = max(0.0, now - self.started_at) % playlist_duration
        for track_index, track in enumerate(station.tracks):
            if playlist_position < track.duration:
                return track_index, playlist_position
            playlist_position -= track.duration
        return 0, 0.0

    def _play_live_track(self, *, force: bool = False) -> None:
        track_index, offset = self._live_track_position(self.station_index)
        track_key = (self.station_index, track_index)
        if not force and self._loaded_track == track_key and pygame.mixer.music.get_busy():
            self.is_playing = True
            return

        track = _RADIO_STATIONS[self.station_index].tracks[track_index]
        track_path = _ASSET_ROOT / track.path
        pygame.mixer.music.load(str(track_path))
        pygame.mixer.music.play(start=offset)
        self._loaded_track = track_key
        self.is_playing = True
        configure_audio(self.settings)

    def toggle(self) -> None:
        self.is_on = not self.is_on
        self._paused_for_game = False
        if not self.is_on:
            pygame.mixer.music.stop()
            self._loaded_track = None
            self.is_playing = False
            return
        self._play_live_track(force=True)

    def pause(self) -> None:
        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self._paused_for_game = True

    def resume(self) -> None:
        if not self._paused_for_game:
            return
        self._paused_for_game = False
        if self.is_on:
            self._play_live_track(force=True)

    def cycle_station(self, direction: int) -> None:
        self.station_index = (self.station_index + direction) % len(_RADIO_STATIONS)
        self._loaded_track = None
        if self.is_on and not self._paused_for_game:
            self._play_live_track(force=True)

    def update(self) -> None:
        if self.is_on and not self._paused_for_game:
            self._play_live_track()

    def stop(self) -> None:
        pygame.mixer.music.stop()
        self.is_on = False
        self.is_playing = False
        self._paused_for_game = False
        self._loaded_track = None


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
    for module_name in ("main",):
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
            sound = pygame.mixer.Sound(str(path))
            sound.set_volume(_MENU_SOUND_LEVELS[kind] * _audio_settings["button_volume"])
            _menu_sounds[kind] = sound
        except pygame.error:
            _menu_sounds[kind] = None
    sound = _menu_sounds[kind]
    if sound is not None:
        sound.play()


def _get_house_icon() -> Optional[pygame.Surface]:
    global _house_icon, _house_icon_load_attempted
    if _house_icon_load_attempted:
        return _house_icon

    _house_icon_load_attempted = True
    try:
        _house_icon = load_image("ch_home/haus.png", alpha=True)
    except (pygame.error, OSError):
        _house_icon = None
    return _house_icon


class WantedLevel:
    def __init__(self, level: int = 0, escape_timer: float = 0):
        self.level = max(0, min(5, int(level)))
        self.escape_timer = max(0.0, float(escape_timer))

    def raise_level(self, amount: int = 1) -> None:
        self.level = min(5, self.level + max(1, int(amount)))
        self.escape_timer = max(self.escape_timer, 1800.0 + self.level * 600.0)

    def update(self, frame_scale: float, nearby_police: bool = False) -> None:
        if self.level == 0 or nearby_police:
            return
        self.escape_timer = max(0.0, self.escape_timer - frame_scale)
        if self.escape_timer == 0:
            self.level -= 1
            if self.level:
                self.escape_timer = 1800.0 + self.level * 600.0

    def clear(self) -> None:
        self.level = 0
        self.escape_timer = 0.0


class HonorAndRespect:
    def __init__(self, honor: float = 0, respect: float = 0):
        self.honor = max(-100.0, min(100.0, float(honor)))
        self.respect = max(-100.0, min(100.0, float(respect)))

    def change(self, *, honor: float = 0, respect: float = 0) -> None:
        self.honor = max(-100.0, min(100.0, self.honor + honor))
        self.respect = max(-100.0, min(100.0, self.respect + respect))


@dataclass
class Projectile:
    position: pygame.Vector2
    velocity: pygame.Vector2
    owner: str
    damage: float = 18.0
    remaining_range: float = 900.0
    radius: int = 4

    def update(self, frame_scale: float) -> bool:
        displacement = self.velocity * frame_scale
        distance = displacement.length()
        if distance >= self.remaining_range:
            if distance:
                displacement.scale_to_length(self.remaining_range)
            self.remaining_range = 0
        else:
            self.remaining_range -= distance
        self.position += displacement
        return self.remaining_range > 0

    def draw(self, screen, offset_x: float, offset_y: float) -> None:
        color = (255, 221, 125) if self.owner == "player" else (255, 80, 65)
        pygame.draw.circle(
            screen,
            color,
            (round(self.position.x + offset_x), round(self.position.y + offset_y)),
            self.radius,
        )


def create_projectile(start, target, owner: str, *, speed: float, damage: float) -> Projectile | None:
    direction = pygame.Vector2(target) - pygame.Vector2(start)
    if direction.length_squared() == 0:
        return None
    return Projectile(
        pygame.Vector2(start),
        direction.normalize() * speed,
        owner,
        damage=damage,
    )


def projectile_hits_wall(start, end, collision_mask) -> bool:
    start = pygame.Vector2(start)
    end = pygame.Vector2(end)
    segment = end - start
    steps = max(1, math.ceil(segment.length() / 6))
    width, height = collision_mask.get_size()
    for index in range(1, steps + 1):
        point = start + segment * (index / steps)
        x, y = round(point.x), round(point.y)
        if not (0 <= x < width and 0 <= y < height):
            return True
        pixel = collision_mask.get_at((x, y))
        if pixel.r < 50 and pixel.g < 50 and pixel.b < 50:
            return True
    return False


class WeaponWheel:
    WEAPONS = ("none", "pistol", "shotgun", "rifle", "smg")

    # Weapon stats: (damage, fire_delay, reload_time, mag_size, reserve_max, spread_count, spread_angles, projectile_speed, range)
    WEAPON_STATS = {
        "pistol": {
            "damage": 34.0,
            "fire_delay": 1.0,
            "reload_time": 3.0,
            "mag_size": 7,
            "reserve_max": 49,
            "spread_count": 1,
            "spread_angles": (0,),
            "projectile_speed": 26.0,
            "range": 900.0,
        },
        "shotgun": {
            "damage": 120.0,
            "fire_delay": 2.0,
            "reload_time": 6.0,
            "mag_size": 5,
            "reserve_max": 25,
            "spread_count": 8,
            "spread_angles": (-15, -10, -5, 0, 5, 10, 15, 20),
            "projectile_speed": 21.0,
            "range": 500.0,
        },
        "rifle": {
            "damage": 20.0,
            "fire_delay": 0.3,
            "reload_time": 5.0,
            "mag_size": 50,
            "reserve_max": 150,
            "spread_count": 1,
            "spread_angles": (0,),
            "projectile_speed": 35.0,
            "range": 1200.0,
        },
        "smg": {
            "damage": 25.0,
            "fire_delay": 0.15,
            "reload_time": 3.5,
            "mag_size": 20,
            "reserve_max": 80,
            "spread_count": 1,
            "spread_angles": (0,),
            "projectile_speed": 28.0,
            "range": 800.0,
        },
    }

    def __init__(self, ammo: int = 7, reserve_ammo: int = 49, selected: str = "pistol"):
        if selected not in self.WEAPONS:
            raise ValueError(f"Unknown weapon: {selected}")
        self.selected = selected
        stats = self.WEAPON_STATS.get(selected, self.WEAPON_STATS["pistol"])
        self.ammo = max(0, min(stats["mag_size"], int(ammo)))
        self.reserve_ammo = max(0, min(stats["reserve_max"], int(reserve_ammo)))
        self.wheel_open = False
        self.last_fire_time = 0.0
        self.is_reloading = False
        self.reload_start_time = 0.0
        self.reload_end_time = 0.0

        # Texture slots for weapon sprites (to be filled later)
        self.weapon_textures = {
            "pistol": None,  # Mathew 37 texture
            "shotgun": None,  # Svityaz 111 texture
            "rifle": None,    # Goida G-2 texture
            "smg": None,      # WR Mini .45 texture
        }

    def process_event(self, event, screen_size) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
            self.wheel_open = True
            self._select_from_pointer(event.pos, screen_size)
        elif event.type == pygame.MOUSEMOTION and self.wheel_open:
            self._select_from_pointer(event.pos, screen_size)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            if self.wheel_open:
                self._select_from_pointer(event.pos, screen_size)
            self.wheel_open = False

    def _select_from_pointer(self, pointer, screen_size) -> None:
        center = pygame.Vector2(screen_size) / 2
        direction = pygame.Vector2(pointer) - center
        if direction.length_squared() < 30**2:
            return
        angle = math.degrees(math.atan2(direction.y, direction.x))
        index = round((angle + 90) / 90) % len(self.WEAPONS)
        new_weapon = self.WEAPONS[index]
        if new_weapon != self.selected:
            self.selected = new_weapon
            self.is_reloading = False  # Cancel reload on weapon switch

    def reload(self, audio=None) -> int:
        if self.is_reloading:
            return 0
        if self.selected == "none":
            return 0
        stats = self.WEAPON_STATS[self.selected]
        if self.ammo >= stats["mag_size"] or self.reserve_ammo <= 0:
            return 0

        self.is_reloading = True
        self.reload_start_time = time.perf_counter()
        self.reload_end_time = self.reload_start_time + stats["reload_time"]

        # Play reload sound if available
        if audio and hasattr(audio, "weapon_sounds"):
            sound_key = f"{self.selected}_reload"
            if sound_key in audio.weapon_sounds:
                try:
                    audio.weapon_sounds[sound_key].play()
                except (pygame.error, AttributeError):
                    pass

        # Schedule ammo transfer (will happen when reload completes)
        transfer = min(stats["mag_size"] - self.ammo, self.reserve_ammo)
        self._pending_ammo_transfer = transfer
        return transfer

    def update_reload(self) -> bool:
        """Update reload state. Returns True if reload just completed."""
        if not self.is_reloading:
            return False

        current_time = time.perf_counter()
        if current_time >= self.reload_end_time:
            # Reload complete
            self.ammo += self._pending_ammo_transfer
            self.reserve_ammo -= self._pending_ammo_transfer
            self.is_reloading = False
            return True
        return False

    def get_reload_progress(self) -> float:
        """Get reload progress as 0.0-1.0."""
        if not self.is_reloading:
            return 0.0
        current_time = time.perf_counter()
        elapsed = current_time - self.reload_start_time
        stats = self.WEAPON_STATS[self.selected]
        return min(1.0, elapsed / stats["reload_time"])

    def fire(self, origin, target) -> list[Projectile]:
        if self.selected == "none" or self.is_reloading:
            return []
        if self.ammo <= 0:
            return []

        stats = self.WEAPON_STATS[self.selected]
        current_time = time.perf_counter()

        # Check fire delay
        if current_time - self.last_fire_time < stats["fire_delay"]:
            return []

        self.ammo -= 1
        self.last_fire_time = current_time

        projectiles = []
        for angle in stats["spread_angles"]:
            projectile = create_projectile(
                origin,
                target,
                "player",
                speed=stats["projectile_speed"],
                damage=stats["damage"],
            )
            if projectile is not None:
                projectile.velocity.rotate_ip(angle)
                projectile.remaining_range = stats["range"]
                projectiles.append(projectile)
        return projectiles

    def melee_target(self, origin, target, candidates, max_distance=70.0):
        # Melee removed for now - all weapons are firearms
        return None

    def draw(self, screen, labels) -> None:
        if not self.wheel_open:
            return
        center = pygame.Vector2(screen.get_size()) / 2
        pygame.draw.circle(screen, (12, 12, 18), center, 148)
        pygame.draw.circle(screen, (180, 180, 190), center, 148, 2)
        positions = (
            center + pygame.Vector2(0, -88),
            center + pygame.Vector2(88, 0),
            center + pygame.Vector2(0, 88),
            center + pygame.Vector2(-88, 0),
        )
        font = pygame.font.Font(None, 27)
        for weapon, position in zip(self.WEAPONS, positions):
            selected = weapon == self.selected
            pygame.draw.circle(
                screen,
                (212, 91, 18) if selected else (58, 58, 68),
                position,
                48,
            )
            label = font.render(labels.get(weapon, weapon.title()), True, (255, 255, 255))
            screen.blit(label, label.get_rect(center=position))


class FleeingDriver:
    def __init__(self, position, fleeing_from):
        self.pos = pygame.Vector2(position)
        direction = self.pos - pygame.Vector2(fleeing_from)
        if direction.length_squared() == 0:
            direction.update(1, 0)
        self.direction = direction.normalize()
        self.is_alive = True
        self.lifetime = 1800.0

    def update(self, col_mask, frame_scale: float) -> None:
        self.lifetime -= frame_scale
        if self.lifetime <= 0:
            self.is_alive = False
            return
        candidate = self.pos + self.direction * 2.8 * frame_scale
        x, y = round(candidate.x), round(candidate.y)
        if (
            0 <= x < col_mask.get_width()
            and 0 <= y < col_mask.get_height()
            and col_mask.get_at((x, y))[:3] != (0, 0, 0)
        ):
            self.pos = candidate
        elif random.random() < 0.04:
            self.direction.rotate_ip(random.choice((-90, 90)))

    def draw(self, screen, offset_x: float, offset_y: float) -> None:
        center = round(self.pos.x + offset_x), round(self.pos.y + offset_y)
        pygame.draw.circle(screen, (40, 90, 220), center, 8)
        pygame.draw.circle(screen, (238, 190, 150), center, 4)


class HostileOfficer:
    def __init__(self, position):
        self.pos = pygame.Vector2(position)
        self.fire_cooldown = 0.0
        self.is_alive = True
        self.health = 100.0
        self.max_health = 100.0

    def update(self, frame_scale: float) -> None:
        self.fire_cooldown = max(0.0, self.fire_cooldown - frame_scale)

    def take_damage(self, amount: float) -> None:
        self.health = max(0.0, self.health - max(0.0, amount))
        if self.health <= 0:
            self.is_alive = False

    def draw(self, screen, offset_x: float, offset_y: float) -> None:
        center = round(self.pos.x + offset_x), round(self.pos.y + offset_y)
        pygame.draw.circle(screen, (35, 45, 80), center, 9)
        pygame.draw.circle(screen, (220, 175, 135), center, 4)


class Player:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.speed = 2
        self.angle = 0  # 0 degrees points south (down) by default.
        self.is_moving = False
        self.health = 100.0
        self.max_health = 100.0

        self.original_image: Optional[pygame.Surface] = None
        self.image: Optional[pygame.Surface] = None
        try:
            raw = load_image("characters/atom.png", alpha=True)
            self.original_image = pygame.transform.scale(raw, (48, 48))
            self.image = self.original_image
        except (pygame.error, OSError) as exc:
            print(f"Не вдалося завантажити characters/atom.png: {exc}")

    def take_damage(self, amount: float) -> None:
        self.health = max(0.0, self.health - max(0.0, amount))

    def update(
        self,
        keys,
        col_mask,
        car_obj=None,
        npc_cars=None,
        frame_scale=1.0,
        *,
        cursor_world=None,
        armed=False,
        can_sprint=True,
    ):
        move = pygame.Vector2(0, 0)

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y = -1
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y = 1

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x = -1
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x = 1

        aim_direction = None
        if armed and cursor_world is not None:
            aim_direction = pygame.Vector2(cursor_world) - self.pos
            if aim_direction.length_squared():
                self.angle = -math.degrees(math.atan2(aim_direction.x, aim_direction.y))

        if move.length() > 0:
            self.is_moving = True

            # Set the character facing direction.
            if aim_direction is None and move.y == 1:
                if move.x > 0:
                    self.angle = -45
                elif move.x < 0:
                    self.angle = 45
                else:
                    self.angle = 0
            elif aim_direction is None and move.y == -1:
                if move.x > 0:
                    self.angle = -135
                elif move.x < 0:
                    self.angle = 135
                else:
                    self.angle = 180
            elif aim_direction is None and move.x > 0:
                self.angle = -90
            elif aim_direction is None and move.x < 0:
                self.angle = 90

            sprinting = can_sprint and keys[pygame.K_LSHIFT]
            movement_speed = self.speed * (1.65 if sprinting else 1.0)
            move = move.normalize() * movement_speed * frame_scale
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
                        if not getattr(npc, "is_alive", True):
                            continue
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


class SurvivalNeeds:
    """Track hunger and hourly health effects using in-game minutes."""

    HUNGER_DRAIN_PER_HOUR = 5.0
    STARVATION_DAMAGE_PER_HOUR = 10.0
    REGEN_PER_HOUR = 5.0

    def __init__(self, hunger=100.0, minutes_into_hour=0.0):
        self.hunger = max(0.0, min(100.0, float(hunger)))
        self.minutes_into_hour = max(0.0, min(59.999, float(minutes_into_hour)))

    @property
    def can_sprint(self) -> bool:
        return self.hunger > 20

    def advance(self, game_minutes: float, player: Player) -> int:
        """Apply hunger/health changes for each crossed in-game hour."""
        if game_minutes <= 0:
            return 0

        self.minutes_into_hour += game_minutes
        crossed_hours = int(self.minutes_into_hour // 60)
        self.minutes_into_hour -= crossed_hours * 60
        for _ in range(crossed_hours):
            if self.hunger <= 0:
                player.take_damage(self.STARVATION_DAMAGE_PER_HOUR)
                continue

            well_fed = self.hunger > 70
            self.hunger = max(0.0, self.hunger - self.HUNGER_DRAIN_PER_HOUR)
            if well_fed:
                player.health = min(
                    player.max_health,
                    player.health + self.REGEN_PER_HOUR,
                )
        return crossed_hours


def _get_surface_grip(col_mask, surface_map, position, angle):
    grip = 1.0
    sample_offsets = (
        pygame.Vector2(),
        pygame.Vector2(20, 12),
        pygame.Vector2(20, -12),
        pygame.Vector2(-20, 12),
        pygame.Vector2(-20, -12),
    )
    for offset in sample_offsets:
        sample_pos = position + offset.rotate(-angle + 180)
        x, y = int(sample_pos.x), int(sample_pos.y)
        if surface_map is not None and surface_map.get_rect().collidepoint(x, y):
            color = surface_map.get_at((x, y))[:3]
            if color[2] > 120 and color[1] > 100 and color[0] < 60:
                grip = min(grip, 0.32)
                continue
        if col_mask is None or not col_mask.get_rect().collidepoint(x, y):
            continue
        red, green, blue = col_mask.get_at((x, y))[:3]
        if red > 220 and green > 210 and blue < 60:
            grip = min(grip, 1.0)
        elif red in range(150, 216) and green in range(85, 151) and blue in range(55, 121):
            grip = min(grip, 0.78)
        elif green > red and green > blue:
            grip = min(grip, 0.58)
    return grip


def _sprites_overlap(
    first_image: pygame.Surface,
    first_center: tuple[float, float] | pygame.Vector2,
    second_image: pygame.Surface,
    second_center: tuple[float, float] | pygame.Vector2,
    angle: float = 0,
) -> bool:
    rotated_first = pygame.transform.rotate(first_image, angle)
    first_rect = rotated_first.get_rect(
        center=(round(first_center[0]), round(first_center[1]))
    )
    second_rect = second_image.get_rect(
        center=(round(second_center[0]), round(second_center[1]))
    )
    if not first_rect.colliderect(second_rect):
        return False
    offset = (second_rect.left - first_rect.left, second_rect.top - first_rect.top)
    first_mask = pygame.mask.from_surface(rotated_first)
    second_mask = pygame.mask.from_surface(second_image)
    return first_mask.overlap(second_mask, offset) is not None


_HEADLIGHT_BEAM_BASE = pygame.Surface((340, 220), pygame.SRCALPHA)
pygame.draw.polygon(
    _HEADLIGHT_BEAM_BASE,
    (255, 245, 190, 80),
    ((0, 110), (340, 0), (340, 220)),
)
pygame.draw.polygon(
    _HEADLIGHT_BEAM_BASE,
    (255, 250, 215, 70),
    ((0, 110), (290, 55), (290, 165)),
)


def _get_headlight_beam(angle):
    forward = pygame.Vector2(1, 0).rotate(-angle + 180)
    screen_angle = math.degrees(math.atan2(forward.y, forward.x))
    return pygame.transform.rotate(_HEADLIGHT_BEAM_BASE, -screen_angle)


def _headlight_obstacle(col_mask, x, y):
    mask_width, mask_height = col_mask.get_size()
    if not (0 <= x < mask_width and 0 <= y < mask_height):
        return True

    pixel = col_mask.get_at((x, y))
    if pixel.r < 50 and pixel.g < 50 and pixel.b < 50:
        return True
    if pixel.r <= 200 or pixel.g >= 50 or pixel.b >= 50:
        return False

    red_neighbors = 0
    for neighbor_y in range(max(0, y - 1), min(mask_height, y + 2)):
        for neighbor_x in range(max(0, x - 1), min(mask_width, x + 2)):
            neighbor = col_mask.get_at((neighbor_x, neighbor_y))
            if neighbor.r > 200 and neighbor.g < 50 and neighbor.b < 50:
                red_neighbors += 1
    return red_neighbors >= 5


def _clip_headlight_beam(beam, beam_rect, world_origin, screen_origin, forward, col_mask):
    origin = pygame.Vector2(world_origin)
    screen_origin = pygame.Vector2(screen_origin)
    forward_angle = math.degrees(math.atan2(forward.y, forward.x))
    endpoints = []

    for angle_offset in range(-18, 19, 3):
        ray_direction = pygame.Vector2(1, 0).rotate(forward_angle + angle_offset)
        distance = 340
        for step in range(3, 341, 3):
            sample = origin + ray_direction * step
            if _headlight_obstacle(col_mask, int(sample.x), int(sample.y)):
                distance = step
                break
        endpoints.append(screen_origin + ray_direction * distance)

    clip_mask = pygame.Surface(beam.get_size(), pygame.SRCALPHA)
    polygon = [
        (round(screen_origin.x - beam_rect.left), round(screen_origin.y - beam_rect.top)),
        *[
            (round(point.x - beam_rect.left), round(point.y - beam_rect.top))
            for point in endpoints
        ],
    ]
    pygame.draw.polygon(clip_mask, (255, 255, 255, 255), polygon)
    clipped_beam = beam.copy()
    clipped_beam.blit(clip_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return clipped_beam


class Car:
    _ACCELERATION_BANDS = ((70.0, 0.9), (90.0, 0.35), (120.0, 0.16))

    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.angle = 0
        self.speed: float = 0.0
        self.vehicle_class = "sport"
        self.is_police = False
        self.handling = 0.82
        self.max_speed = 16.25
        self.accel = 0.09
        self.friction = 0.04
        self.brake_force = 0.3
        self.motion_velocity = pygame.Vector2()

        self.skid_marks = []
        self.just_hit = False
        self.is_drifting = False
        self.is_braking = False

        # --- Vehicle damage system ---
        self.health = 180.0  # Current health.
        self.max_health = 180.0
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
            self.image = load_image("cars/tornado/tornado_special.png", alpha=True)
            self.image = pygame.transform.scale(self.image, (96, 48))
        except (pygame.error, OSError):
            self.image = pygame.Surface((96, 48))
            self.image.fill((0, 0, 255))

    def _accelerate_forward(self, frame_scale, traction=1.0):
        remaining_frames = frame_scale
        max_kmh = self.max_speed * 8

        while remaining_frames > 0:
            current_kmh = self.speed * 8
            if current_kmh >= max_kmh:
                self.speed = self.max_speed
                return

            for limit_kmh, acceleration_per_frame in self._ACCELERATION_BANDS:
                if current_kmh < limit_kmh:
                    band_limit = min(limit_kmh, max_kmh)
                    acceleration_per_frame *= traction
                    break
            else:
                band_limit = max_kmh
                acceleration_per_frame = self._ACCELERATION_BANDS[-1][1] * traction

            frames_to_limit = (band_limit - current_kmh) / acceleration_per_frame
            applied_frames = min(remaining_frames, frames_to_limit)
            current_kmh += acceleration_per_frame * applied_frames
            self.speed = min(current_kmh / 8, self.max_speed)
            remaining_frames -= applied_frames

    def update(self, keys, col_mask, active, npc_cars=None, frame_scale=1.0, surface_map=None):
        left_pressed = False
        right_pressed = False
        handbrake_pressed = False
        self.is_drifting = False
        self.is_braking = False
        surface_grip = _get_surface_grip(col_mask, surface_map, self.pos, self.angle)
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
            self.is_braking = (
                (keys[pygame.K_s] or keys[pygame.K_DOWN]) and self.speed > 0
            ) or (
                (keys[pygame.K_w] or keys[pygame.K_UP]) and self.speed < 0
            )
            current_accel = self.accel * frame_scale
            if abs(self.speed) > 10: current_accel = self.accel / 3
            if abs(self.speed) > 10: current_accel *= frame_scale

            if keys[pygame.K_w] or keys[pygame.K_UP]:
                if self.speed < 0:
                    self.speed += self.brake_force * frame_scale
                else:
                    self._accelerate_forward(frame_scale, surface_grip)
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
            handbrake_pressed = keys[pygame.K_SPACE] and abs(self.speed) > 0.5
            if handbrake_pressed:
                self.speed *= 0.985 ** frame_scale
            if abs(self.speed) > 0.5:
                steer = 5.0 - (min(abs(self.speed) / 2, 1.0))
                if handbrake_pressed:
                    steer *= 1.5
                direction = 1 if self.speed > 0 else -1
                if left_pressed: self.angle += steer * direction * frame_scale
                if right_pressed: self.angle -= steer * direction * frame_scale

        # 3. Movement and collision. At higher speed the car's momentum
        # follows steering more slowly, so it slides sideways during turns.
        current_kmh = abs(self.speed) * 8
        is_turning = left_pressed != right_pressed
        self.is_drifting = active and current_kmh > 30 and (is_turning or handbrake_pressed)
        desired_velocity = pygame.Vector2(self.speed, 0).rotate(-self.angle + 180)
        if self.is_drifting:
            drift_intensity = min((current_kmh - 30) / 90, 1.0) ** 1.5
            grip = (0.55 - 0.35 * drift_intensity) * surface_grip
            if handbrake_pressed:
                grip *= 0.28
            if current_kmh >= 100:
                speed_loss_kmh_per_second = 7.0 if current_kmh <= 110 else 10.0
                speed_reduction = speed_loss_kmh_per_second * frame_scale / (60 * 8)
                if self.speed > 0:
                    self.speed = max(0.0, self.speed - speed_reduction)
                elif self.speed < 0:
                    self.speed = min(0.0, self.speed + speed_reduction)
        elif current_kmh > 30:
            grip = 0.42 * surface_grip * self.handling
        else:
            grip = 0.65 * surface_grip * self.handling
        if self.is_drifting:
            grip *= self.handling
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
                    if not getattr(npc, "is_alive", True):
                        continue
                    # Check nearby traffic around the player’s car.
                    if test_pos.distance_to(npc.pos) < 95:  # Detection distance.
                        if _sprites_overlap(
                            self.image,
                            test_pos,
                            npc.image,
                            npc.pos,
                            self.angle,
                        ):
                            return True  # Treat the other car as an obstacle.
            w, h = 40, 18
            points = [
                test_pos + pygame.Vector2(dx, dy).rotate(-self.angle + 180)
                for dx in (-w, -w / 2, 0, w / 2, w)
                for dy in (-h, -h / 2, 0, h / 2, h)
            ]
            red_hits = 0
            for point in points:
                mask_x, mask_y = int(point.x), int(point.y)
                if (
                    col_mask is None
                    or not col_mask.get_rect().collidepoint(mask_x, mask_y)
                ):
                    return True
                pixel = col_mask.get_at((mask_x, mask_y))
                is_black_wall = pixel.r < 50 and pixel.g < 50 and pixel.b < 50
                is_red_marking = pixel.r > 200 and pixel.g < 50 and pixel.b < 50
                if is_black_wall:
                    return True
                if is_red_marking:
                    red_hits += 1
            # Red is also used for dashed road markings; only broad red blocks
            # in the collision mask represent solid obstacles.
            return red_hits >= 8

        if check_at_pos(next_pos):
            impact_speed = velocity.length()
            if impact_speed > 1.5:
                self.just_hit = True
                damage = min(65.0, impact_speed * 2.0)
                self.health -= damage
                if self.health <= 0:
                    self.health = 0
                    self.is_broken = True

            if velocity.length_squared() > 0:
                self.pos -= velocity.normalize() * 5 * frame_scale
            bounce_factor = min(0.9, 0.45 + impact_speed * 0.04)
            self.motion_velocity *= -bounce_factor
            forward = pygame.Vector2(1, 0).rotate(-self.angle + 180)
            self.speed = max(
                -self.max_speed / 2,
                min(self.max_speed, self.motion_velocity.dot(forward)),
            )
        else:
            old_pos = pygame.Vector2(self.pos.x, self.pos.y)
            self.pos = next_pos

            # Tire tracks.
            is_braking = active and ((keys[pygame.K_s] and self.speed > 2) or (keys[pygame.K_w] and self.speed < -2))
            if is_braking or self.is_drifting:
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

    def draw_headlights(self, screen, offset_x, offset_y, col_mask=None):
        self.draw_headlight_beams(screen, offset_x, offset_y, col_mask)
        self.draw_headlight_lamps(screen, offset_x, offset_y)

    def draw_headlight_beams(self, screen, offset_x, offset_y, col_mask=None):
        center = pygame.Vector2(self.pos.x + offset_x, self.pos.y + offset_y)
        forward = pygame.Vector2(1, 0).rotate(-self.angle + 180)
        side = pygame.Vector2(-forward.y, forward.x)
        beam = _get_headlight_beam(self.angle)

        for lamp_offset in (side * 13, side * -13):
            world_origin = self.pos + forward * 43 + lamp_offset
            screen_origin = center + forward * 43 + lamp_offset
            beam_rect = beam.get_rect(center=screen_origin + forward * 170)
            clipped_beam = (
                _clip_headlight_beam(
                    beam,
                    beam_rect,
                    world_origin,
                    screen_origin,
                    forward,
                    col_mask,
                )
                if col_mask is not None
                else beam
            )
            screen.blit(clipped_beam, beam_rect)

    def draw_headlight_lamps(self, screen, offset_x, offset_y):
        center = pygame.Vector2(self.pos.x + offset_x, self.pos.y + offset_y)
        forward = pygame.Vector2(1, 0).rotate(-self.angle + 180)
        side = pygame.Vector2(-forward.y, forward.x)
        front_center = center + forward * 43
        for lamp_center in (front_center + side * 13, front_center - side * 13):
            pygame.draw.circle(
                screen,
                (255, 250, 190),
                (round(lamp_center.x), round(lamp_center.y)),
                4,
            )

    def draw(self, screen, offset_x, offset_y, lights_on=False, col_mask=None):
        center = pygame.Vector2(
            self.pos.x + offset_x,
            self.pos.y + offset_y,
        )
        forward = pygame.Vector2(1, 0).rotate(-self.angle + 180)
        side = pygame.Vector2(-forward.y, forward.x)

        if lights_on:
            self.draw_headlight_beams(screen, offset_x, offset_y, col_mask)

        for p1l, p2l, p1r, p2r in self.skid_marks:
            pygame.draw.line(screen, (45, 45, 45), (p1l.x + offset_x, p1l.y + offset_y),
                             (p2l.x + offset_x, p2l.y + offset_y), 5)
            pygame.draw.line(screen, (45, 45, 45), (p1r.x + offset_x, p1r.y + offset_y),
                             (p2r.x + offset_x, p2r.y + offset_y), 5)

        rotated = pygame.transform.rotate(self.image, self.angle)
        rect = rotated.get_rect(center=center)

        screen.blit(rotated, rect)
        if lights_on:
            self.draw_headlight_lamps(screen, offset_x, offset_y)
        rear_light_color = (255, 0, 0) if self.is_braking else (125, 18, 12)
        rear_light_radius = 7 if self.is_braking else 3
        rear_center = center - forward * 39
        for lamp_center in (rear_center + side * 13, rear_center - side * 13):
            pygame.draw.circle(
                screen,
                rear_light_color,
                (round(lamp_center.x), round(lamp_center.y)),
                rear_light_radius,
            )

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


def draw_handgun(
    screen,
    player_position,
    target_position,
    offset_x,
    offset_y,
    player_angle=None,
    weapon_type="pistol",
):
    start = pygame.Vector2(player_position) + pygame.Vector2(offset_x, offset_y)
    direction = pygame.Vector2(target_position) - pygame.Vector2(player_position)
    if direction.length_squared() == 0:
        return
    weapon_length = 35 if weapon_type in ("shotgun", "rifle") else 25
    if player_angle is not None:
        desired_angle = -math.degrees(math.atan2(direction.x, direction.y))
        angle_delta = (desired_angle - player_angle + 180) % 360 - 180
        limited_angle = player_angle + max(-45, min(45, angle_delta))
        angle_radians = math.radians(limited_angle)
        direction = pygame.Vector2(-math.sin(angle_radians), math.cos(angle_radians))
    direction = direction.normalize()
    side = pygame.Vector2(-direction.y, direction.x)
    grip = start + direction * 7
    barrel = start + direction * weapon_length - side * 10
    points = (
        grip + side * 3,
        grip - side * 3,
        barrel - side * 2,
        barrel + side * 2,
    )
    pygame.draw.polygon(screen, (40, 40, 45), points)
    pygame.draw.line(
        screen,
        (20, 20, 24),
        (round(barrel.x), round(barrel.y)),
        (round((barrel + direction * 5).x), round((barrel + direction * 5).y)),
        2,
    )


def draw_player_status(screen, player, ammo, reserve_ammo, wanted_level, labels):
    """Draw ammunition and wanted status in the lower-left corner."""
    screen_height = screen.get_height()
    small_font = pygame.font.Font(None, 24)

    # The minimap now owns the health display, so keep these clear of it.
    ammo_text = labels.get("ammo", "Ammo: {current}/{reserve}").format(
        current=ammo,
        reserve=reserve_ammo,
    )
    ammo_surface = small_font.render(ammo_text, True, (255, 255, 255))
    screen.blit(ammo_surface, (20, screen_height - 52))

    stars = "* " * wanted_level + "- " * (5 - wanted_level)
    wanted_text = labels.get("wanted", "Wanted: {stars}").format(stars=stars)
    wanted_surface = small_font.render(wanted_text, True, (255, 190, 90))
    screen.blit(wanted_surface, (20, screen_height - 27))


def _format_gps_distance(distance: float) -> str:
    if distance >= 999.5:
        return f"{distance / 1000:.1f} km"
    return f"{distance:.0f} m"


def _draw_gps_marker(surface, center, radius):
    pygame.draw.circle(surface, (15, 15, 15), center, radius + 3)
    pygame.draw.circle(surface, (255, 255, 255), center, radius + 1)
    pygame.draw.circle(surface, (255, 112, 0), center, radius)
    pygame.draw.circle(surface, (255, 255, 255), center, max(2, radius // 3))


def _sector_polygon_points(center, radius, start_angle, end_angle, steps=72):
    """Return the center and arc points for a screen-coordinate pie sector."""
    cx, cy = center
    points = [(round(cx), round(cy))]
    for step in range(steps + 1):
        angle = math.radians(start_angle + (end_angle - start_angle) * step / steps)
        points.append((round(cx + math.cos(angle) * radius), round(cy + math.sin(angle) * radius)))
    return points


def _minimap_gps_position(player_position, destination, ratio_x, ratio_y, offset, center, radius):
    player_point = pygame.Vector2(
        player_position[0] * ratio_x + offset[0],
        player_position[1] * ratio_y + offset[1],
    )
    destination_point = pygame.Vector2(
        destination[0] * ratio_x + offset[0],
        destination[1] * ratio_y + offset[1],
    )
    center_point = pygame.Vector2(center)
    relative_destination = destination_point - center_point
    if relative_destination.length_squared() <= radius**2:
        return round(destination_point.x), round(destination_point.y)

    direction = destination_point - player_point
    a = direction.length_squared()
    if a == 0:
        return round(center_point.x), round(center_point.y)
    relative_player = player_point - center_point
    b = relative_player.dot(direction)
    c = relative_player.length_squared() - radius**2
    discriminant = max(0.0, b * b - a * c)
    distance = (-b + math.sqrt(discriminant)) / a
    edge_point = player_point + direction * distance
    return round(edge_point.x), round(edge_point.y)


def draw_gta_minimap(
    screen,
    bg_img,
    target,
    world_w,
    world_h,
    house_pos=(7738, 2325),
    gps: GPS | None = None,
    labels: Mapping[str, str] | None = None,
    *,
    hunger=100.0,
    health=100.0,
):
    """Draw a glass HUD with a two-thirds radar, hunger wedge, and health ring."""

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

    distance: float | None = None
    destination: tuple[float, float] | None = None
    if gps is not None:
        distance = gps.distance_to((target.pos.x, target.pos.y))
        destination = gps.destination
    # Keep distant destinations visible at the radar edge, pointing outward.
    if destination is not None:
        marker_pos = _minimap_gps_position(
            (target.pos.x, target.pos.y),
            destination,
            ratio_x,
            ratio_y,
            (ox, oy),
            (half_size, half_size),
            half_size - 14,
        )
        _draw_gps_marker(mini_surf, marker_pos, 9)

    # The lower 120 degrees are reserved for the glass hunger panel; the
    # remaining 240 degrees show the world radar.
    radar_mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.polygon(
        radar_mask,
        (255, 255, 255, 255),
        _sector_polygon_points((half_size, half_size), half_size, 150, 390),
    )
    mini_surf.blit(radar_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    glass = pygame.Surface((size, size), pygame.SRCALPHA)
    hunger_sector = _sector_polygon_points(
        (half_size, half_size), half_size - 1, 30, 150
    )
    pygame.draw.polygon(glass, (12, 42, 58, 224), hunger_sector)
    pygame.draw.lines(
        glass,
        (118, 225, 239, 190),
        False,
        hunger_sector[1:],
        2,
    )
    pygame.draw.line(glass, (160, 235, 245, 110), (half_size, half_size + 6),
                     (half_size, size - 8), 1)
    screen.blit(glass, (x, y))

    # Localized satiety readout and fill bar sit inside the lower glass segment.
    text_labels = labels or {}
    hunger_value = max(0, min(100, round(float(hunger))))
    hunger_text = text_labels.get("hunger_meter", "HUNGER {value}%").format(
        value=hunger_value
    )
    hunger_font = pygame.font.Font(None, 15)
    hunger_surface = hunger_font.render(hunger_text, True, (238, 250, 255))
    hunger_surface.set_alpha(245)
    screen.blit(
        hunger_surface,
        hunger_surface.get_rect(center=(x + half_size, y + half_size + 17)),
    )
    hunger_bar = pygame.Rect(x + 48, y + size - 17, 104, 7)
    pygame.draw.rect(screen, (7, 20, 28), hunger_bar, border_radius=4)
    fill_width = round(hunger_bar.width * hunger_value / 100)
    if fill_width:
        hunger_color = (82, 218, 158) if hunger_value > 20 else (238, 151, 70)
        pygame.draw.rect(
            screen,
            hunger_color,
            (hunger_bar.x, hunger_bar.y, fill_width, hunger_bar.height),
            border_radius=4,
        )

    # A full ring is the health bar: its colored arc shrinks with current HP.
    center_on_screen = (x + half_size, y + half_size)
    health_ratio = max(0.0, min(1.0, float(health) / 100.0))
    ring_rect = pygame.Rect(
        center_on_screen[0] - half_size - 8,
        center_on_screen[1] - half_size - 8,
        size + 16,
        size + 16,
    )
    pygame.draw.circle(screen, (15, 25, 32), center_on_screen, half_size + 8, 5)
    health_color = (67, 224, 142) if health_ratio > 0.5 else (
        (247, 181, 75) if health_ratio > 0.2 else (239, 75, 67)
    )
    if health_ratio > 0:
        pygame.draw.arc(
            screen,
            health_color,
            ring_rect,
            math.radians(270),
            math.radians(270 + 360 * health_ratio),
            5,
        )

    # Draw the minimap on the main screen.
    # Map.
    screen.blit(mini_surf, (x, y))
    pygame.draw.circle(screen, (209, 237, 244), center_on_screen, half_size, 2)
    pygame.draw.arc(screen, (91, 171, 190), ring_rect, math.radians(30),
                    math.radians(150), 3)

    health_text = text_labels.get("health_meter", "HP {value}%").format(
        value=round(health_ratio * 100)
    )
    health_font = pygame.font.Font(None, 15)
    health_surface = health_font.render(health_text, True, (245, 255, 255))
    health_back = health_surface.get_rect(center=(x + half_size, y + 15))
    health_back.inflate_ip(8, 4)
    pygame.draw.rect(screen, (8, 20, 28, 185), health_back, border_radius=5)
    screen.blit(health_surface, health_surface.get_rect(center=health_back.center))
    if distance is not None:
        text = text_labels.get("gps_distance", "Distance: {distance}").format(
            distance=_format_gps_distance(distance)
        )
        distance_font = pygame.font.Font(None, 22)
        rendered_distance = distance_font.render(text, True, (255, 215, 0))
        screen.blit(rendered_distance, (x, y - rendered_distance.get_height() - 8))

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
            t.get("stats_max_speed", "Top speed: {value} km/h").format(
                value=round(stats.get("max_speed_kmh", 0))
            ),
            t.get("stats_longest_drift", "Longest drift: {value} m").format(
                value=round(stats.get("longest_drift_m", 0))
            ),
            t.get("stats_no_crash", "Longest drive without a crash: {value} m").format(
                value=round(stats.get("distance_without_crash_m", 0))
            ),
            t.get("stats_honor", "Honor: {value}").format(
                value=round(stats.get("honor", 0))
            ),
            t.get("stats_respect", "Respect: {value}").format(
                value=round(stats.get("respect", 0))
            ),
        ]
        line_step = min(48, max(32, (height - 300) // len(lines)))
        for index, line in enumerate(lines):
            rendered = small_font.render(line, True, (220, 220, 220))
            scale = min(
                1.0,
                (width - 80) / rendered.get_width(),
                (line_step - 4) / rendered.get_height(),
            )
            if scale < 1:
                rendered = pygame.transform.smoothscale(
                    rendered,
                    (
                        max(1, int(rendered.get_width() * scale)),
                        max(1, int(rendered.get_height() * scale)),
                    ),
                )
            screen.blit(
                rendered,
                rendered.get_rect(center=(width // 2, 135 + index * line_step)),
            )

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


def selection_menu(screen, title, options, font, small_font, back_label, settings):
    """Show a keyboard- and mouse-navigable list; return an option index or status."""
    pygame.mouse.set_visible(True)
    clock = pygame.time.Clock()
    selected_index = 0
    last_hovered = None
    menu_options = [*options, back_label]

    while True:
        width, height = screen.get_size()
        screen.fill((14, 14, 20))
        title_surface = font.render(title, True, (255, 255, 255))
        screen.blit(title_surface, title_surface.get_rect(center=(width // 2, height // 4)))

        row_height = min(70, max(54, (height - 180) // len(menu_options)))
        first_y = max(height // 2 - row_height * len(menu_options) // 2, height // 3)
        button_width = min(700, width - 80)
        rects = [
            pygame.Rect(
                (width - button_width) // 2,
                first_y + index * row_height,
                button_width,
                row_height - 8,
            )
            for index in range(len(menu_options))
        ]

        mouse_position = pygame.mouse.get_pos()
        hovered_index = next(
            (index for index, rect in enumerate(rects) if rect.collidepoint(mouse_position)),
            None,
        )
        if hovered_index != last_hovered:
            if hovered_index is not None:
                play_menu_sound("hover")
            last_hovered = hovered_index

        for index, (label, rect) in enumerate(zip(menu_options, rects)):
            if hovered_index == index:
                selected_index = index
            pygame.draw.rect(
                screen,
                (212, 91, 18) if selected_index == index else (55, 55, 65),
                rect,
                border_radius=8,
            )
            label_surface = small_font.render(label, True, (255, 255, 255))
            screen.blit(label_surface, label_surface.get_rect(center=rect.center))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "EXIT", screen
            if event.type == pygame.VIDEORESIZE:
                screen = apply_window_resize(event.size, settings)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    play_menu_sound("click")
                    return "BACK", screen
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected_index = (selected_index - 1) % len(menu_options)
                    play_menu_sound("hover")
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected_index = (selected_index + 1) % len(menu_options)
                    play_menu_sound("hover")
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    play_menu_sound("click")
                    if selected_index == len(options):
                        return "BACK", screen
                    return selected_index, screen
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for index, rect in enumerate(rects):
                    if rect.collidepoint(event.pos):
                        play_menu_sound("click")
                        if index == len(options):
                            return "BACK", screen
                        return index, screen

        clock.tick(FPS)


def save_slot_menu(screen, font, small_font, settings, trans_dict, languages, game_state, controls=None):
    """Show save slot selection menu with 5 slots."""
    from settings_manager import get_all_save_slots, save_to_slot
    
    pygame.mouse.set_visible(True)
    sel = 0
    clock = pygame.time.Clock()
    last_hovered = None
    
    while True:
        t = trans_dict[languages[settings['lang_idx']]]
        slots = get_all_save_slots()
        
        slot_labels = []
        for slot in slots:
            if slot.get("empty"):
                slot_labels.append(f"Slot {slot['index'] + 1}: Empty")
            else:
                time_str = f"{int(slot['game_time'] // 60):02d}:{int(slot['game_time'] % 60):02d}"
                slot_labels.append(f"Slot {slot['index'] + 1}: {slot['money']} UAH | {time_str} | {slot['game_state']}")
        
        slot_labels.append("Back")
        
        screen.fill((0, 0, 0))
        m_pos = pygame.mouse.get_pos()
        rects = [pygame.Rect(50, 150 + i * 70, 700, 60) for i in range(len(slot_labels))]
        
        title = font.render("Select Save Slot", True, (212, 91, 18))
        screen.blit(title, (50, 80))
        
        for event in pygame.event.get():
            if controls is not None:
                controls.process_event(event)
            if event.type == pygame.QUIT:
                return "EXIT"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    play_menu_sound("click")
                    return "BACK"
                if event.key == pygame.K_UP:
                    sel = (sel - 1) % len(slot_labels)
                    play_menu_sound("hover")
                if event.key == pygame.K_DOWN:
                    sel = (sel + 1) % len(slot_labels)
                    play_menu_sound("hover")
                if event.key == pygame.K_RETURN:
                    play_menu_sound("click")
                    if sel == len(slot_labels) - 1:  # Back
                        return "BACK"
                    else:  # Save to slot
                        save_to_slot(sel, game_state)
                        return "SAVED"
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, r in enumerate(rects):
                    if r.collidepoint(event.pos):
                        play_menu_sound("click")
                        if i == len(slot_labels) - 1:  # Back
                            return "BACK"
                        else:  # Save to slot
                            save_to_slot(i, game_state)
                            return "SAVED"
        
        for i, label in enumerate(slot_labels):
            if rects[i].collidepoint(m_pos):
                if last_hovered != i:
                    play_menu_sound("hover")
                last_hovered = i
                sel = i
            color = (212, 91, 18) if i == sel else (255, 255, 255)
            txt = small_font.render(label, True, color)
            screen.blit(txt, (50, 150 + i * 70))
        
        if not any(rect.collidepoint(m_pos) for rect in rects):
            last_hovered = None
        
        pygame.display.flip()
        clock.tick(FPS)


def pause_menu(screen, font, small_font, settings, trans_dict, languages, controls=None, stats=None, on_change=None, game_state=None):
    pygame.mouse.set_visible(True)
    sel = 0
    clock = pygame.time.Clock()
    last_hovered = None

    def activate_option(index, translations):
        if index == 0:
            return "CONTINUE"
        if index == 1:
            if game_state is not None:
                save_result = save_slot_menu(screen, font, small_font, settings, trans_dict, languages, game_state, controls)
                if save_result == "EXIT":
                    return "EXIT"
                return None
            return None
        if index == 2:
            stats_result = stats_dialog(screen, font, small_font, translations, stats, controls)
            return "EXIT" if stats_result == "EXIT" else None
        if index == 3:
            settings_result = settings_sub_menu(screen, font, settings, trans_dict, languages, controls, on_change)
            return settings_result if settings_result in ("EXIT", "VIDEO_CHANGED") else None
        elif index == 4 and confirm_dialog(screen, font, small_font, translations, controls):
            return "MENU"
        return None

    while True:
        t = trans_dict[languages[settings['lang_idx']]]
        options = [t["resume"], "Save Game", t["stats"], t["settings"], t["menu"]]

        screen.fill((0, 0, 0))
        m_pos = pygame.mouse.get_pos()
        rects = [pygame.Rect(50, 180 + i * 90, 500, 60) for i in range(len(options))]

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


# noinspection DuplicatedCode
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


# noinspection DuplicatedCode
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


# noinspection DuplicatedCode
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
def draw_debug_coords(screen, target, mode_label, fps=None):
    """Draw the target's world coordinates and frame rate for debugging."""
    if target is None:
        return
    position = getattr(target, "pos", None)
    if not isinstance(position, pygame.Vector2):
        return
    try:
        debug_f = pygame.font.SysFont("Consolas", 20, bold=True)
    except pygame.error:
        debug_f = pygame.font.SysFont("Arial", 20)

    curr_x, curr_y = map(int, position)

    fps_text = f" | FPS: {fps:.0f}" if fps is not None else ""
    debug_text = f"X: {curr_x} Y: {curr_y} | MODE: {mode_label}{fps_text}"
    txt_surf = debug_f.render(debug_text, True, (255, 255, 0))

    # Text background.
    bg_rect = pygame.Rect(10, 10, txt_surf.get_width() + 10, 30)
    bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
    bg_surf.fill((0, 0, 0, 180))

    screen.blit(bg_surf, (10, 10))
    screen.blit(txt_surf, (15, 15))


def full_screen_map(
    screen,
    map_img,
    target,
    world_w,
    world_h,
    house_pos=(7738, 2325),
    controls=None,
    gps: GPS | None = None,
    labels: Mapping[str, str] | None = None,
):
    """Draw the zoomable full-screen map and its icons."""
    house_icon = _get_house_icon()

    screen_width, screen_height = screen.get_size()
    map_zoom = 1.5
    scaled_w = int(screen_width * map_zoom)
    scaled_h = int(screen_height * map_zoom)
    map_off_x = int((0.5 - target.pos.x / world_w) * scaled_w)
    map_off_y = int((0.5 - target.pos.y / world_h) * scaled_h)
    clock = pygame.time.Clock()
    running = True
    labels = labels or {}

    while running:
        screen.fill((20, 20, 20))
        scaled_w = int(screen_width * map_zoom)
        scaled_h = int(screen_height * map_zoom)
        map_rect = pygame.Rect(0, 0, scaled_w, scaled_h)
        map_rect.center = (screen_width // 2 + map_off_x, screen_height // 2 + map_off_y)
        for event in pygame.event.get():
            if controls is not None:
                controls.process_event(event)
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.MOUSEWHEEL:
                map_zoom += event.y * 0.1
                map_zoom = max(1.0, min(5.0, map_zoom))
            if event.type == pygame.MOUSEBUTTONDOWN and gps is not None:
                if event.button == 1 and map_rect.collidepoint(event.pos):
                    map_x = (event.pos[0] - map_rect.left) / scaled_w
                    map_y = (event.pos[1] - map_rect.top) / scaled_h
                    gps.set_destination(
                        (
                            max(0.0, min(float(world_w), map_x * world_w)),
                            max(0.0, min(float(world_h), map_y * world_h)),
                        )
                    )
                    play_menu_sound("click")
                elif event.button == 3:
                    gps.clear_destination()
                    play_menu_sound("click")
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_TAB, pygame.K_ESCAPE]:
                    running = False
                elif gps is not None and event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                    gps.clear_destination()

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

        distance: float | None = None
        destination: tuple[float, float] | None = None
        if gps is not None:
            distance = gps.distance_to((target.pos.x, target.pos.y))
            destination = gps.destination
        if destination is not None:
            dx, dy = world_to_map(*destination)
            _draw_gps_marker(screen, (dx, dy), max(6, int(10 * map_zoom)))

        if distance is not None:
            text_labels = labels or {}
            distance_text = text_labels.get("gps_distance", "Distance: {distance}").format(
                distance=_format_gps_distance(distance)
            )
            distance_font = pygame.font.Font(None, 30)
            rendered_distance = distance_font.render(distance_text, True, (255, 215, 0))
            screen.blit(rendered_distance, (20, 20))

        hint_font = pygame.font.Font(None, 24)
        text_labels = labels or {}
        set_hint = text_labels.get("gps_set", "Left-click: set destination")
        clear_hint = text_labels.get("gps_clear", "Right-click/Backspace: clear destination")
        for index, hint_text in enumerate((set_hint, clear_hint)):
            rendered_hint = hint_font.render(hint_text, True, (240, 240, 240))
            screen.blit(
                rendered_hint,
                (20, screen_height - rendered_hint.get_height() * (2 - index) - 16),
            )

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


def update_combat_system(frame_scale, fleeing_drivers, hostile_officers, npc_cars, projectiles,
                          atom, car, in_car, col_mask, wanted, honor_and_respect):
    """Update all combat-related entities and handle projectile collisions."""
    for driver in fleeing_drivers:
        driver.update(col_mask, frame_scale)
    fleeing_drivers[:] = [driver for driver in fleeing_drivers if driver.is_alive]

    for officer in hostile_officers:
        officer.update(frame_scale)
    for npc in npc_cars:
        if getattr(npc, "is_police", False):
            npc.fire_cooldown = max(0.0, npc.fire_cooldown - frame_scale)

    police_nearby = any(
        getattr(npc, "is_police", False)
        and getattr(npc, "is_alive", True)
        and npc.pos.distance_to(atom.pos) < 900
        for npc in npc_cars
    ) or any(officer.pos.distance_to(atom.pos) < 900 for officer in hostile_officers)
    wanted.update(frame_scale, nearby_police=police_nearby)

    if wanted.level:
        target_position = car.pos if in_car else atom.pos
        for police in npc_cars:
            if (
                not getattr(police, "is_police", False)
                or not getattr(police, "is_alive", True)
                or police.pos.distance_to(target_position) > 650
                or police.fire_cooldown > 0
            ):
                continue
            projectile = create_projectile(
                police.pos,
                target_position,
                "police",
                speed=15.0,
                damage=12.0,
            )
            if projectile is not None:
                projectiles.append(projectile)
                police.fire_cooldown = 75.0

        for officer in hostile_officers:
            if (
                officer.pos.distance_to(target_position) > 650
                or officer.fire_cooldown > 0
            ):
                continue
            projectile = create_projectile(
                officer.pos,
                target_position,
                "police",
                speed=17.0,
                damage=16.0,
            )
            if projectile is not None:
                projectiles.append(projectile)
                officer.fire_cooldown = 60.0

    remaining_projectiles = []
    for projectile in projectiles:
        old_position = pygame.Vector2(projectile.position)
        if not projectile.update(frame_scale):
            continue
        if projectile_hits_wall(old_position, projectile.position, col_mask):
            continue

        if projectile.owner == "player":
            hit_car = next(
                (
                    npc for npc in npc_cars
                    if getattr(npc, "is_alive", True)
                    and npc.pos.distance_squared_to(projectile.position) < 38**2
                ),
                None,
            )
            if hit_car is not None:
                hit_position = pygame.Vector2(hit_car.pos)
                hit_police = getattr(hit_car, "is_police", False)
                hit_car.is_alive = False
                if hit_police:
                    hostile_officers.append(
                        HostileOfficer(hit_position + pygame.Vector2(35, 0))
                    )
                    wanted.raise_level(2)
                    honor_and_respect.change(honor=-12, respect=-7)
                else:
                    fleeing_drivers.append(FleeingDriver(hit_position, atom.pos))
                    wanted.raise_level(1)
                    honor_and_respect.change(honor=-10, respect=-6)
                continue

            hit_officer = next(
                (
                    officer for officer in hostile_officers
                    if officer.is_alive
                    and officer.pos.distance_squared_to(projectile.position) < 22**2
                ),
                None,
            )
            if hit_officer is not None:
                hit_officer.is_alive = False
                wanted.raise_level(1)
                continue

            hit_driver = next(
                (
                    driver for driver in fleeing_drivers
                    if driver.is_alive
                    and driver.pos.distance_squared_to(projectile.position) < 18**2
                ),
                None,
            )
            if hit_driver is not None:
                hit_driver.is_alive = False
                honor_and_respect.change(honor=-25, respect=-20)
                wanted.raise_level(2)
                continue
        elif in_car:
            if car.pos.distance_squared_to(projectile.position) < 42**2:
                car.health = max(0, car.health - projectile.damage)
                if car.health == 0:
                    car.is_broken = True
                continue
        elif atom.pos.distance_squared_to(projectile.position) < 20**2:
            atom.take_damage(projectile.damage)
            continue

        remaining_projectiles.append(projectile)
    projectiles[:] = remaining_projectiles
    hostile_officers[:] = [officer for officer in hostile_officers if officer.is_alive]


def save_session_statistics(money, total_earned, total_spent, game_time, collected_treasures,
                            personal_records, honor_and_respect):
    """Save the last session statistics."""
    save_statistics({
        "money": money,
        "earned": total_earned,
        "spent": total_spent,
        "time": f"{int(game_time / 60):02d}:{int(game_time % 60):02d}",
        "treasures": len(collected_treasures),
        "max_speed_kmh": personal_records["max_speed_kmh"],
        "longest_drift_m": personal_records["longest_drift_m"],
        "distance_without_crash_m": personal_records["distance_without_crash_m"],
        "honor": honor_and_respect.honor,
        "respect": honor_and_respect.respect,
    })


def build_game_state_data(game_state, atom, atom_h, car, weapons, wanted,
                          honor_and_respect, money, total_earned, total_spent, game_time,
                          collected_treasures, distance_since_crash, current_drift_distance,
                          survival=None):
    """Build the serializable state shared by manual and automatic saves."""
    return {
        "game_state": game_state,
        "player": {
            "x": atom.pos.x,
            "y": atom.pos.y,
            "angle": atom.angle,
        },
        "hero_health": atom.health,
        "hunger": survival.hunger if survival is not None else 100.0,
        "survival_minute_progress": (
            survival.minutes_into_hour if survival is not None else game_time % 60
        ),
        "ammo": weapons.ammo,
        "reserve_ammo": weapons.reserve_ammo,
        "weapon": weapons.selected,
        "honor": honor_and_respect.honor,
        "respect": honor_and_respect.respect,
        "wanted_level": wanted.level,
        "wanted_escape_timer": wanted.escape_timer,
        "house_player": {
            "x": atom_h.pos.x,
            "y": atom_h.pos.y,
            "angle": atom_h.angle,
        },
        "car": {
            "x": car.pos.x,
            "y": car.pos.y,
            "angle": car.angle,
            "speed": car.speed,
            "health": car.health,
            "is_broken": car.is_broken,
        },
        "money": money,
        "earned": total_earned,
        "spent": total_spent,
        "game_time": game_time,
        "collected_treasures": sorted(collected_treasures),
        "distance_streak": distance_since_crash,
        "drift_streak": current_drift_distance,
    }


def save_game_state(game_state, atom, atom_h, car, weapons, wanted,
                    honor_and_respect, money, total_earned, total_spent, game_time,
                    collected_treasures, distance_since_crash, current_drift_distance,
                    survival=None):
    """Persist the current open-world state."""
    save_game_save(build_game_state_data(
        game_state, atom, atom_h, car, weapons, wanted, honor_and_respect,
        money, total_earned, total_spent, game_time, collected_treasures,
        distance_since_crash, current_drift_distance, survival,
    ))


def handle_car_audio(car, in_car, sounds, e_chan, c_chan):
    if getattr(car, 'just_hit', False):
        crash_sound = sounds.get('crash')
        if crash_sound is not None:
            c_chan.play(crash_sound)
        car.just_hit = False

    if not in_car:
        e_chan.stop()
        return

    # 1. Engine audio.
    if not e_chan.get_busy():
        e_chan.play(sounds['engine'], loops=-1)

    # Adjust volume based on speed.
    vol = min(0.6, 0.2 + (abs(car.speed) / 20.0))
    e_chan.set_volume(vol)

def play_car_horn(sounds, channel) -> None:
    horn = sounds.get("beep")
    if horn is not None:
        channel.play(horn)


def get_ambient_color(game_time_minutes):
    """
    game_time_minutes: Time in minutes, from 0 to 1440.
    Return the (red, green, blue, alpha) overlay color.
    """
    h = game_time_minutes / 60.0

    # Daytime (08:00–18:00) is fully lit.
    if 8 <= h < 18:
        return 0, 0, 0, 0
    if h >= 21 or h < 5:
        return 15, 15, 40, 160
    if 5 <= h < 8:
        transition = (h - 5) / 3.0
    else:
        transition = (h - 18) / 3.0
    smooth_transition = transition * transition * (3 - 2 * transition)
    darkness = 1 - smooth_transition if h < 8 else smooth_transition
    return 15, 15, 40, round(160 * darkness)


def fade_screen(screen, fade_out, duration=0.8):
    frame = screen.copy()
    overlay = pygame.Surface(screen.get_size())
    overlay.fill((0, 0, 0))
    clock = pygame.time.Clock()
    elapsed = 0.0
    while elapsed < duration:
        elapsed = min(duration, elapsed + clock.tick(60) / 1000)
        progress = elapsed / duration
        alpha = round(255 * (progress if fade_out else 1 - progress))
        screen.blit(frame, (0, 0))
        overlay.set_alpha(alpha)
        screen.blit(overlay, (0, 0))
        pygame.display.flip()
        pygame.event.pump()
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



def run_open_world(screen, settings, *, continue_game=True):
    """Run ATOF's continuous open-world game session."""
    WORLD_WIDTH = _constants.WORLD_WIDTH
    WORLD_HEIGHT = _constants.WORLD_HEIGHT
    HOUSE_SLEEP_SPOT = _constants.HOUSE_SLEEP_SPOT
    traffic_timer = 0
    traffic_state = "RED"  # RED pauses route N; GREEN pauses route A1.
    frame_count = 0
    keyboard = KeyboardState()
    # Spawn the configured traffic and police at game start.
    npc_cars = traffic.init_traffic(18)
    fleeing_drivers: list[FleeingDriver] = []
    hostile_officers: list[HostileOfficer] = []
    projectiles: list[Projectile] = []
    map_scale = 4.0
    current_world_width = int(WORLD_WIDTH * map_scale)
    current_world_height = int(WORLD_HEIGHT * map_scale)
    camera = Camera2D(
        screen.get_size(),
        (current_world_width, current_world_height),
    )
    resources = load_game_resources(
        screen.get_size(),
        (current_world_width, current_world_height),
    )
    # Load the game resources.
    target_y = 450.0
    phone_y_offset = 450.0
    game_audio = resources.audio
    phone_click_sfx = game_audio.phone_click
    current_app = 0  # 0 is the phone menu; 1–9 are apps.
    game_save = load_game_save() if continue_game else None
    money = game_save.get("money", 100) if game_save else 100
    total_earned = game_save.get("earned", 0) if game_save else 0
    total_spent = game_save.get("spent", 0) if game_save else 0
    money_history = [("+100", "start")] if not game_save else []
    # Keep track of collected treasures so they cannot be collected repeatedly.
    collected_treasures = set()
    phone_active = False  # Phone state.
    phone_settings = get_phone_settings()
    weapons = WeaponWheel(
        game_save.get("ammo", 7) if game_save else 7,
        game_save.get("reserve_ammo", 49) if game_save else 49,
        game_save.get("weapon", "pistol") if game_save else "pistol",
    )
    wanted = WantedLevel(
        game_save.get("wanted_level", 0) if game_save else 0,
        game_save.get("wanted_escape_timer", 0) if game_save else 0,
    )
    # --- Time and lighting ---
    game_time = game_save.get("game_time", 480.0) if game_save else 480.0
    night_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    wake_overlay = pygame.Surface(screen.get_size())
    car_sfx = game_audio.car_sounds
    step_sounds = game_audio.footsteps

    def apply_audio_settings():
        configure_game_audio(settings, game_audio)
        traffic.configure_audio(settings)

    apply_audio_settings()

    engine_chan = game_audio.engine_channel
    crash_chan = game_audio.crash_channel
    foot_chan = game_audio.footstep_channel
    horn_chan = game_audio.horn_channel
    clock = pygame.time.Clock()
    frame_clock = FrameClock()
    frame_renderer = LayeredRenderer()
    languages = SUPPORTED_LANGUAGES

    assets = resources.assets
    atom_img = assets.atom
    original_nav_map = assets.original_nav_map
    world_bg = assets.world_background
    full_map_img = assets.full_map
    col_mask = assets.collision_mask
    house_visual = assets.house_visual
    house_collision = assets.house_collision
    house_info = assets.house_info

    show_debug = False
    game_state = game_save.get("game_state", "HOUSE") if game_save else "HOUSE"
    scene_manager = SceneManager(game_state)
    scene_manager.register("CITY")
    scene_manager.register("HOUSE")
    in_car = False

    # GAME OBJECTS
    atom = Player(7738, 2330)
    car = Car(7985, 2383)
    car.angle = 270
    if game_save:
        player_data = game_save.get("player", {})
        atom.pos.update(player_data.get("x", 7738), player_data.get("y", 2330))
        atom.angle = player_data.get("angle", 0)
        atom.health = game_save.get("hero_health", atom.max_health)
        car_data = game_save.get("car", {})
        car.pos.update(car_data.get("x", 7985), car_data.get("y", 2383))
        car.angle = car_data.get("angle", 270)
        car.speed = car_data.get("speed", 0)
        car.motion_velocity = pygame.Vector2(car.speed, 0).rotate(-car.angle + 180)
        car.health = min(car_data.get("health", car.max_health), car.max_health)
        car.is_broken = car_data.get("is_broken", False)
    survival = SurvivalNeeds(
        game_save.get("hunger", 100.0) if game_save else 100.0,
        game_save.get("survival_minute_progress", game_time % 60) if game_save else game_time % 60,
    )
    atom_h = HousePlayer(162, 161)
    atom_h.pos.update(HOUSE_SLEEP_SPOT)
    if game_save and game_save.get("game_state") == "HOUSE":
        house_data = game_save.get("house_player", {})
        atom_h.pos.update(
            house_data.get("x", 147),
            house_data.get("y", 156),
        )
        atom_h.angle = house_data.get("angle", 0)
    gps = GPS()
    if game_save:
        collected_treasures.update(game_save.get("collected_treasures", []))
    personal_records = load_statistics()
    honor_and_respect = HonorAndRespect(
        game_save.get("honor", personal_records.get("honor", 0)) if game_save else personal_records.get("honor", 0),
        game_save.get("respect", personal_records.get("respect", 0)) if game_save else personal_records.get("respect", 0),
    )
    distance_since_crash = game_save.get("distance_streak", 0.0) if game_save else 0.0
    current_drift_distance = game_save.get("drift_streak", 0.0) if game_save else 0.0
    sleep_requested = False
    wake_fade_started = None
    manual_headlights = False
    radio = GameRadio(settings)

    game_font, small_font = resources.game_font, resources.small_font

    translations = {
        "English": {
            "hint": "[F] Enter / steal car", "enter": "[E] Enter House", "exit": "[E] Exit House",
            "resume": "Resume", "stats": "Stats", "settings": "Settings", "menu": "To Menu",
            "vol": "Volume", "lang": "Language", "back": "Back",
            "volume": "Volume", "music_vol": "Music Volume", "npc_vol": "NPC Volume",
            "crash_vol": "Crash Volume", "button_vol": "Button Volume",
            "footsteps_vol": "Footsteps Volume",
            "audio_hint": "Up/Down selects a sound; Left/Right adjusts it; Esc returns",
            "repair": "Hold [R] to repair", "confirm_q": "Leave the game?",
            "confirm_w": "Progress in this session will be lost.", "yes": "YES", "no": "NO",
            "stats_title": "Session statistics", "stats_money": "Money: {money} UAH",
            "stats_time": "Time: {time}", "stats_treasures": "Treasures found: {treasures}",
            "stats_earned": "Total earned: {amount} UAH", "stats_spent": "Total spent: {amount} UAH", "stats_hint": "Press Esc or Enter to return",
            "stats_honor": "Honor: {value}", "stats_respect": "Respect: {value}",
            "player_hp": "HP: {current}/{maximum}", "ammo": "Ammo: {current}/{reserve}",
            "wanted": "Wanted: {stars}", "reload": "Reloaded", "empty_ammo": "Out of ammo",
            "weapon_hint": "Mouse: move while armed | Left Shift: sprint | LMB: fire | R: reload",
            "none": "Unarmed", "pistol": "Mathew 37", "shotgun": "Svityaz 111", "rifle": "Goida G-2", "smg": "WR Mini .45",
            "steal_hint": "[F] Steal vehicle",
            "gps_distance": "Distance: {distance}", "gps_set": "Left-click: set destination",
            "gps_clear": "Right-click/Backspace: clear destination",
            "radio_on": "{station} · {genre} · {track} | V: radio off | ,/<: previous | ./>: next",
            "radio_paused": "{station} · {genre} · {track} | V: radio on | ,/<: previous | ./>: next",
            "radio_off": "RADIO OFF | V: on | ,/<: previous station | ./>: next station",
        },
        "Українська": {
            "hint": "[F] Сісти / викрасти авто", "enter": "[E] Увійти в дім", "exit": "[E] Вийти з дому",
            "resume": "Продовжити", "stats": "Статистика", "settings": "Налаштування", "menu": "В меню",
            "vol": "Гучність", "lang": "Мова", "back": "Назад",
            "volume": "Гучність", "music_vol": "Гучність музики", "npc_vol": "Гучність НПС",
            "crash_vol": "Гучність аварій", "button_vol": "Гучність кнопок",
            "footsteps_vol": "Гучність кроків",
            "audio_hint": "↑/↓ обирає звук; ←/→ змінює гучність; Esc — назад",
            "repair": "Тримайте [R] для ремонту", "confirm_q": "Вийти з гри?",
            "confirm_w": "Прогрес цієї сесії буде втрачено.", "yes": "ТАК", "no": "НІ",
            "stats_title": "Статистика сесії", "stats_money": "Гроші: {money} UAH",
            "stats_time": "Час: {time}", "stats_treasures": "Знайдено скарбів: {treasures}",
            "stats_earned": "Всього зароблено: {amount} UAH", "stats_spent": "Всього витрачено: {amount} UAH", "stats_hint": "Натисніть Esc або Enter, щоб повернутися",
            "stats_honor": "Честь: {value}", "stats_respect": "Повага: {value}",
            "player_hp": "ЗД: {current}/{maximum}", "ammo": "Патрони: {current}/{reserve}",
            "wanted": "Розшук: {stars}", "reload": "Перезаряджено", "empty_ammo": "Немає патронів",
            "weapon_hint": "Миша: рух зі зброєю | Лівий Shift: біг | ЛКМ: стріляти | R: перезарядити",
            "none": "Без зброї", "pistol": "Mathew 37", "shotgun": "Svityaz 111", "rifle": "Goida G-2", "smg": "WR Mini .45",
            "steal_hint": "[F] Викрасти авто",
            "gps_distance": "Відстань: {distance}", "gps_set": "ЛКМ: поставити точку",
            "gps_clear": "ПКМ/Backspace: прибрати точку",
            "radio_on": "{station} · {genre} · {track} | V: вимкнути | ,/<: попередня | ./>: наступна",
            "radio_paused": "{station} · {genre} · {track} | V: увімкнути | ,/<: попередня | ./>: наступна",
            "radio_off": "РАДІО ВИМКНЕНО | V: увімкнути | ,/<: попередня станція | ./>: наступна станція",
        },
        "Русский": {
            "hint": "[F] Сесть / угнать авто", "enter": "[E] Войти в дом", "exit": "[E] Выйти из дома",
            "resume": "Продолжить", "stats": "Статистика", "settings": "Настройки", "menu": "В меню",
            "vol": "Громкость", "lang": "Язык", "back": "Назад",
            "volume": "Громкость", "music_vol": "Громкость музыки", "npc_vol": "Громкость НПС",
            "crash_vol": "Громкость аварий", "button_vol": "Громкость кнопок",
            "footsteps_vol": "Громкость шагов",
            "audio_hint": "↑/↓ выбирает звук; ←/→ меняет громкость; Esc — назад",
            "repair": "Удерживайте [R], чтобы починить", "confirm_q": "Выйти из игры?",
            "confirm_w": "Прогресс этой сессии будет потерян.", "yes": "ДА", "no": "НЕТ",
            "stats_title": "Статистика сессии", "stats_money": "Деньги: {money} UAH",
            "stats_time": "Время: {time}", "stats_treasures": "Найдено сокровищ: {treasures}",
            "stats_earned": "Всего заработано: {amount} UAH", "stats_spent": "Всего потрачено: {amount} UAH", "stats_hint": "Нажмите Esc или Enter, чтобы вернуться",
            "stats_honor": "Честь: {value}", "stats_respect": "Уважение: {value}",
            "player_hp": "ЗД: {current}/{maximum}", "ammo": "Патроны: {current}/{reserve}",
            "wanted": "Розыск: {stars}", "reload": "Перезаряжено", "empty_ammo": "Нет патронов",
            "weapon_hint": "Мышь: движение с оружием | Левый Shift: бег | ЛКМ: стрелять | R: перезарядить",
            "none": "Без оружия", "pistol": "Mathew 37", "shotgun": "Svityaz 111", "rifle": "Goida G-2", "smg": "WR Mini .45",
            "steal_hint": "[F] Угнать авто",
            "gps_distance": "Расстояние: {distance}", "gps_set": "ЛКМ: поставить точку",
            "gps_clear": "ПКМ/Backspace: убрать точку",
            "radio_on": "{station} · {genre} · {track} | V: выключить | ,/<: предыдущая | ./>: следующая",
            "radio_paused": "{station} · {genre} · {track} | V: включить | ,/<: предыдущая | ./>: следующая",
            "radio_off": "РАДИО ВЫКЛЮЧЕНО | V: включить | ,/<: предыдущая станция | ./>: следующая станция",
        },
        "Español": {
            "hint": "[F] Entrar / robar coche", "enter": "[E] Entrar en casa", "exit": "[E] Salir de casa",
            "resume": "Reanudar", "stats": "Estadísticas", "settings": "Ajustes", "menu": "Volver al menú",
            "vol": "Volumen", "lang": "Idioma", "back": "Atrás",
            "volume": "Volumen", "music_vol": "Volumen de la música", "npc_vol": "Volumen de los NPC",
            "crash_vol": "Volumen de choques", "button_vol": "Volumen de botones",
            "footsteps_vol": "Volumen de pasos",
            "audio_hint": "↑/↓ elegir sonido; ←/→ ajustar volumen; Esc para volver",
            "repair": "Mantén [R] para reparar", "confirm_q": "¿Salir del juego?",
            "confirm_w": "Se perderá el progreso de esta sesión.", "yes": "SÍ", "no": "NO",
            "stats_title": "Estadísticas de la sesión", "stats_money": "Dinero: {money} UAH",
            "stats_time": "Tiempo: {time}", "stats_treasures": "Tesoros encontrados: {treasures}",
            "stats_earned": "Total ganado: {amount} UAH", "stats_spent": "Total gastado: {amount} UAH",
            "stats_hint": "Pulsa Esc o Enter para volver",
            "stats_honor": "Honor: {value}", "stats_respect": "Respeto: {value}",
            "player_hp": "Salud: {current}/{maximum}", "ammo": "Munición: {current}/{reserve}",
            "wanted": "Búsqueda: {stars}", "reload": "Recargado", "empty_ammo": "Sin munición",
            "weapon_hint": "Ratón: moverse armado | Mayús izq.: correr | Clic izq.: disparar | R: recargar",
            "none": "Sin arma", "pistol": "Mathew 37", "shotgun": "Svityaz 111", "rifle": "Goida G-2", "smg": "WR Mini .45",
            "steal_hint": "[F] Robar vehículo",
            "gps_distance": "Distancia: {distance}", "gps_set": "Clic izquierdo: marcar destino",
            "gps_clear": "Clic derecho/Retroceso: borrar destino",
            "radio_on": "{station} · {genre} · {track} | V: apagar | ,/<: anterior | ./>: siguiente",
            "radio_paused": "{station} · {genre} · {track} | V: encender | ,/<: anterior | ./>: siguiente",
            "radio_off": "RADIO APAGADA | V: encender | ,/<: emisora anterior | ./>: siguiente",
        },
        "Deutsch": {
            "hint": "[F] Einsteigen / Auto stehlen", "enter": "[E] Haus betreten", "exit": "[E] Haus verlassen",
            "resume": "Fortsetzen", "stats": "Statistik", "settings": "Einstellungen", "menu": "Zum Hauptmenü",
            "vol": "Lautstärke", "lang": "Sprache", "back": "Zurück",
            "volume": "Lautstärke", "music_vol": "Musiklautstärke", "npc_vol": "NPC-Lautstärke",
            "crash_vol": "Lautstärke für Unfälle", "button_vol": "Tastenlautstärke",
            "footsteps_vol": "Schrittlautstärke",
            "audio_hint": "↑/↓ Ton wählen; ←/→ Lautstärke ändern; Esc zurück",
            "repair": "[R] zum Reparieren halten", "confirm_q": "Spiel verlassen?",
            "confirm_w": "Der Fortschritt dieser Sitzung geht verloren.", "yes": "JA", "no": "NEIN",
            "stats_title": "Sitzungsstatistik", "stats_money": "Geld: {money} UAH",
            "stats_time": "Zeit: {time}", "stats_treasures": "Gefundene Schätze: {treasures}",
            "stats_earned": "Insgesamt verdient: {amount} UAH", "stats_spent": "Insgesamt ausgegeben: {amount} UAH",
            "stats_hint": "Esc oder Enter drücken, um zurückzukehren",
            "stats_honor": "Ehre: {value}", "stats_respect": "Ansehen: {value}",
            "player_hp": "LP: {current}/{maximum}", "ammo": "Munition: {current}/{reserve}",
            "wanted": "Gesucht: {stars}", "reload": "Nachgeladen", "empty_ammo": "Keine Munition",
            "weapon_hint": "Maus: mit Waffe bewegen | Linke Umschalttaste: sprinten | Linksklick: schießen | R: nachladen",
            "none": "Keine Waffe", "pistol": "Mathew 37", "shotgun": "Svityaz 111", "rifle": "Goida G-2", "smg": "WR Mini .45",
            "steal_hint": "[F] Auto stehlen",
            "gps_distance": "Entfernung: {distance}", "gps_set": "Linksklick: Ziel setzen",
            "gps_clear": "Rechtsklick/Backspace: Ziel löschen",
            "radio_on": "{station} · {genre} · {track} | V: ausschalten | ,/<: zurück | ./>: weiter",
            "radio_paused": "{station} · {genre} · {track} | V: einschalten | ,/<: zurück | ./>: weiter",
            "radio_off": "RADIO AUS | V: einschalten | ,/<: vorheriger Sender | ./>: nächster Sender",
        },
        "Français": {
            "hint": "[F] Monter / voler une voiture", "enter": "[E] Entrer dans la maison", "exit": "[E] Sortir de la maison",
            "resume": "Reprendre", "stats": "Statistiques", "settings": "Paramètres", "menu": "Menu principal",
            "vol": "Volume", "lang": "Langue", "back": "Retour",
            "volume": "Volume", "music_vol": "Volume de la musique", "npc_vol": "Volume des PNJ",
            "crash_vol": "Volume des collisions", "button_vol": "Volume des boutons",
            "footsteps_vol": "Volume des pas",
            "audio_hint": "↑/↓ choisir le son ; ←/→ régler le volume ; Échap pour revenir",
            "repair": "Maintenir [R] pour réparer", "confirm_q": "Quitter la partie ?",
            "confirm_w": "La progression de cette session sera perdue.", "yes": "OUI", "no": "NON",
            "stats_title": "Statistiques de la session", "stats_money": "Argent : {money} UAH",
            "stats_time": "Temps : {time}", "stats_treasures": "Trésors trouvés : {treasures}",
            "stats_earned": "Total gagné : {amount} UAH", "stats_spent": "Total dépensé : {amount} UAH",
            "stats_hint": "Appuyez sur Échap ou Entrée pour revenir",
            "stats_honor": "Honneur : {value}", "stats_respect": "Respect : {value}",
            "player_hp": "Santé : {current}/{maximum}", "ammo": "Munitions : {current}/{reserve}",
            "wanted": "Recherché : {stars}", "reload": "Rechargé", "empty_ammo": "Plus de munitions",
            "weapon_hint": "Souris : avancer armé | Maj gauche : courir | Clic gauche : tirer | R : recharger",
            "none": "Désarmé", "pistol": "Mathew 37", "shotgun": "Svityaz 111", "rifle": "Goida G-2", "smg": "WR Mini .45",
            "steal_hint": "[F] Voler la voiture",
            "gps_distance": "Distance : {distance}", "gps_set": "Clic gauche : définir la destination",
            "gps_clear": "Clic droit/Retour arrière : supprimer la destination",
            "radio_on": "{station} · {genre} · {track} | V : éteindre | ,/< : précédente | ./> : suivante",
            "radio_paused": "{station} · {genre} · {track} | V : allumer | ,/< : précédente | ./> : suivante",
            "radio_off": "RADIO ÉTEINTE | V : allumer | ,/< : station précédente | ./> : station suivante",
        }
    }

    per_language_labels = {
        "English": {
            "sleep_save": "Press [E] / [T] by the bed to sleep and save",
            "hunger_meter": "HUNGER {value}%", "health_meter": "HP {value}%",
            "radio_genre_rock": "Alternative rock", "radio_genre_synthwave": "Synthwave",
            "radio_genre_folk": "Folk / world",
            "video": "Video", "window_mode": "Window mode", "window_mode_value": "Resizable",
            "resolution": "Resolution", "fps_limit": "Frame rate limit",
            "fps_unlimited": "Unlimited",
            "video_hint": "FPS is not monitor Hz. Use the title bar button to maximize.",
            "stats_max_speed": "Top speed: {value} km/h",
            "stats_longest_drift": "Longest drift: {value} m",
            "stats_no_crash": "Longest drive without a crash: {value} m",
        },
        "Українська": {
            "sleep_save": "Натисніть [E] / [T] біля ліжка, щоб заснути й зберегтися",
            "hunger_meter": "СИТІСТЬ {value}%", "health_meter": "ЗД {value}%",
            "radio_genre_rock": "Альтернативний рок", "radio_genre_synthwave": "Синтвейв",
            "radio_genre_folk": "Фолк / етно",
            "video": "Відео", "window_mode": "Режим вікна", "window_mode_value": "Змінний розмір",
            "resolution": "Роздільність", "fps_limit": "Ліміт кадрів (FPS)",
            "fps_unlimited": "Без обмежень",
            "video_hint": "FPS — не герци монітора. Натисніть кнопку в заголовку, щоб розгорнути вікно.",
            "stats_max_speed": "Максимальна швидкість: {value} км/год",
            "stats_longest_drift": "Найдовший занос: {value} м",
            "stats_no_crash": "Найдовша поїздка без аварій: {value} м",
        },
        "Русский": {
            "sleep_save": "Нажмите [E] / [T] у кровати, чтобы поспать и сохраниться",
            "hunger_meter": "СЫТОСТЬ {value}%", "health_meter": "ЗД {value}%",
            "radio_genre_rock": "Альтернативный рок", "radio_genre_synthwave": "Синтвейв",
            "radio_genre_folk": "Фолк / этно",
            "video": "Видео", "window_mode": "Режим окна", "window_mode_value": "Изменяемый размер",
            "resolution": "Разрешение", "fps_limit": "Лимит кадров (FPS)",
            "fps_unlimited": "Без ограничений",
            "video_hint": "FPS — не герцы монитора. Нажмите кнопку в заголовке, чтобы развернуть окно.",
            "stats_max_speed": "Максимальная скорость: {value} км/ч",
            "stats_longest_drift": "Самый длинный занос: {value} м",
            "stats_no_crash": "Самая длинная поездка без аварий: {value} м",
        },
        "Español": {
            "sleep_save": "Pulsa [E] / [T] junto a la cama para dormir y guardar",
            "hunger_meter": "HAMBRE {value}%", "health_meter": "SALUD {value}%",
            "radio_genre_rock": "Rock alternativo", "radio_genre_synthwave": "Synthwave",
            "radio_genre_folk": "Folk / tradicional",
            "video": "Vídeo", "window_mode": "Modo de ventana", "window_mode_value": "Redimensionable",
            "resolution": "Resolución", "fps_limit": "Límite de fotogramas (FPS)",
            "fps_unlimited": "Sin límite",
            "video_hint": "FPS no son los Hz. Usa el botón de la barra superior para maximizar.",
            "stats_max_speed": "Velocidad máxima: {value} km/h",
            "stats_longest_drift": "Derrape más largo: {value} m",
            "stats_no_crash": "Trayecto más largo sin choque: {value} m",
        },
        "Deutsch": {
            "sleep_save": "Am Bett [E] / [T] drücken, um zu schlafen und zu speichern",
            "hunger_meter": "HUNGER {value}%", "health_meter": "LP {value}%",
            "radio_genre_rock": "Alternative Rock", "radio_genre_synthwave": "Synthwave",
            "radio_genre_folk": "Folk / Weltmusik",
            "video": "Video", "window_mode": "Fenstermodus", "window_mode_value": "Größe änderbar",
            "resolution": "Auflösung", "fps_limit": "Bildratenlimit (FPS)",
            "fps_unlimited": "Unbegrenzt",
            "video_hint": "FPS sind nicht Monitor-Hz. Mit der Schaltfläche in der Titelleiste maximieren.",
            "stats_max_speed": "Höchstgeschwindigkeit: {value} km/h",
            "stats_longest_drift": "Längster Drift: {value} m",
            "stats_no_crash": "Längste Fahrt ohne Unfall: {value} m",
        },
        "Français": {
            "sleep_save": "Appuyez sur [E] / [T] près du lit pour dormir et sauvegarder",
            "hunger_meter": "FAIM {value}%", "health_meter": "SANTÉ {value}%",
            "radio_genre_rock": "Rock alternatif", "radio_genre_synthwave": "Synthwave",
            "radio_genre_folk": "Folk / musique du monde",
            "video": "Vidéo", "window_mode": "Mode fenêtre", "window_mode_value": "Redimensionnable",
            "resolution": "Résolution", "fps_limit": "Limite d’images (FPS)",
            "fps_unlimited": "Illimitée",
            "video_hint": "Les FPS ne sont pas les Hz. Utilisez le bouton de la barre de titre.",
            "stats_max_speed": "Vitesse maximale : {value} km/h",
            "stats_longest_drift": "Dérapage le plus long : {value} m",
            "stats_no_crash": "Trajet le plus long sans accident : {value} m",
        },
    }
    for language, labels in per_language_labels.items():
        translations[language].update(labels)

    def nearby_traffic_car(
        position,
        radius: float = 90,
    ) -> traffic.TrafficCar | None:
        candidates: list[traffic.TrafficCar] = [
            npc for npc in npc_cars
            if getattr(npc, "is_alive", True)
            and npc.pos.distance_squared_to(position) <= radius * radius
        ]
        closest = min(
            candidates,
            key=lambda npc: npc.pos.distance_squared_to(position),
            default=None,
        )
        if (
            closest is not None
            and closest.pos.distance_squared_to(position) < car.pos.distance_squared_to(position)
        ):
            return closest
        return None

    def hijack_traffic_car(npc):
        nonlocal car, in_car
        stolen_position = pygame.Vector2(npc.pos)
        stolen_angle = npc.angle
        stolen_police = npc.is_police
        forward = pygame.Vector2(1, 0).rotate(stolen_angle + 180)
        driver_position = stolen_position - forward * 35
        if stolen_police:
            hostile_officers.append(HostileOfficer(stolen_position + forward * 40))
            wanted.raise_level(3)
            honor_and_respect.change(honor=-15, respect=-8)
        else:
            fleeing_drivers.append(FleeingDriver(driver_position, atom.pos))
            wanted.raise_level(1)
            honor_and_respect.change(honor=-8, respect=-5)

        npc.is_alive = False
        replacement = Car(stolen_position.x, stolen_position.y)
        replacement.angle = stolen_angle
        replacement.vehicle_class = "stolen-police" if stolen_police else "stolen-sedan"
        replacement.is_police = stolen_police
        replacement.image = (
            traffic.get_police_car_image()
            if stolen_police
            else traffic.get_traffic_car_image()
        )
        replacement.max_speed = 13.0 if stolen_police else 11.5
        replacement.handling = 0.7 if stolen_police else 0.62
        car = replacement
        in_car = True
        atom.pos.update(car.pos)

    def reload_weapon():
        weapons.reload(game_audio)

    def update_combat(frame_scale):
        update_combat_system(frame_scale, fleeing_drivers, hostile_officers, npc_cars,
                                    projectiles, atom, car, in_car, col_mask, wanted, honor_and_respect)

    def save_sleep_game():
        save_game_state(game_state, atom, atom_h, car, weapons, wanted,
                                        honor_and_respect, money, total_earned, total_spent, game_time,
                                        collected_treasures, distance_since_crash, current_drift_distance,
                                        survival)
        save_session_statistics(money, total_earned, total_spent, game_time, collected_treasures,
                                        personal_records, honor_and_respect)

    def save_last_session_stats():
        save_session_statistics(money, total_earned, total_spent, game_time, collected_treasures,
                                        personal_records, honor_and_respect)

    def get_current_game_state():
        return build_game_state_data(
            game_state,
            atom,
            atom_h,
            car,
            weapons,
            wanted,
            honor_and_respect,
            money,
            total_earned,
            total_spent,
            game_time,
            collected_treasures,
            distance_since_crash,
            current_drift_distance,
            survival,
        )

    running = True
    frame_clock.reset()
    while running:
        frame_scale = frame_clock.tick(clock, FPS)
        target = car if in_car else atom
        off_x = off_y = 0
        traffic_timer += frame_scale / 60
        if traffic_timer > 5:  # Switch the traffic-light phase every five seconds.
            traffic_state = "GREEN" if traffic_state == "RED" else "RED"
            traffic_timer = 0
        phone_y_offset += (target_y - phone_y_offset) * (1 - (5 / 6) ** frame_scale)
        # Update the phone slide animation before drawing it.
        target_y = 0.0 if phone_active else 450.0
        current_lang_name = languages[settings['lang_idx']]
        t = translations.get(current_lang_name, translations["English"])
        keys = keyboard
        # One real second advances one in-game minute; survival uses that same clock.
        game_minute_delta = frame_scale / 60
        game_time = (game_time + game_minute_delta) % 1440
        survival.advance(game_minute_delta, atom)

        frame_count += frame_scale
        if frame_count >= 60:
            traffic.analyze_traffic_jams(npc_cars)
            frame_count %= 60

        # Update weapon reload state
        weapons.update_reload()

        # 1. Process events.
        for event in pygame.event.get():
            keyboard.process_event(event)
            weapons.process_event(event, screen.get_size())
            if event.type == pygame.VIDEORESIZE:
                screen = apply_window_resize(event.size, settings)
                camera.resize(screen.get_size())
                full_map_img = pygame.transform.scale(original_nav_map, (WIDTH, HEIGHT))
                night_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                wake_overlay = pygame.Surface(screen.get_size())
                save_settings(settings)
            if event.type == pygame.QUIT:
                save_last_session_stats()
                return "EXIT"
            if event.type == pygame.KEYDOWN:
                # --- Phone controls ---
                if keyboard.matches(event, pygame.K_m):
                    phone_active = not phone_active
                    current_app = 0
                    phone_click_sfx.play()  # Play a sound when M opens or closes the phone.

                if phone_active:
                    # BACKSPACE controls.
                    if event.key == pygame.K_BACKSPACE:
                        if current_app != 0:
                            current_app = 0  # Return to the phone menu.
                            phone_click_sfx.play()
                        else:
                            phone_active = False  # Close the phone.
                            phone_click_sfx.play()

                    # Open phone apps from the home screen.
                    elif current_app == 0:
                        if keyboard.matches(event, pygame.K_1) or event.key == pygame.K_KP1:
                            current_app = 1
                            phone_click_sfx.play()
                        elif keyboard.matches(event, pygame.K_2) or event.key == pygame.K_KP2:
                            current_app = 2
                            phone_click_sfx.play()
                    elif current_app == 2:
                        # Number keys select one of the available phone case colors.
                        phone_color_keys = {
                            pygame.K_1: 0, pygame.K_KP1: 0,
                            pygame.K_2: 1, pygame.K_KP2: 1,
                            pygame.K_3: 2, pygame.K_KP3: 2,
                            pygame.K_4: 3, pygame.K_KP4: 3,
                            pygame.K_5: 4, pygame.K_KP5: 4,
                        }
                        if event.key in phone_color_keys:
                            phone_settings["case_idx"] = phone_color_keys[event.key]
                            save_phone_settings(phone_settings)
                            phone_click_sfx.play()
                if event.key == pygame.K_F3:
                    show_debug = not show_debug
                if event.key == pygame.K_TAB:
                    full_screen_map(
                        screen, full_map_img, (car if in_car else atom),
                        current_world_width, current_world_height,
                        controls=keyboard, gps=gps, labels=t
                    )
                if event.key == pygame.K_ESCAPE:
                    radio_was_playing = radio.is_playing
                    radio.pause()
                    res = pause_menu(
                        screen, game_font, small_font, settings, translations, languages, keyboard,
                        {
                            "money": money,
                            "earned": total_earned,
                            "spent": total_spent,
                            "time": f"{int(game_time / 60):02d}:{int(game_time % 60):02d}",
                            "treasures": len(collected_treasures),
                            "max_speed_kmh": personal_records["max_speed_kmh"],
                            "longest_drift_m": personal_records["longest_drift_m"],
                            "distance_without_crash_m": personal_records[
                                "distance_without_crash_m"
                            ],
                            "honor": honor_and_respect.honor,
                            "respect": honor_and_respect.respect,
                        },
                        on_change=save_settings,
                        game_state=get_current_game_state(),
                    )
                    apply_audio_settings()
                    if res == "VIDEO_CHANGED":
                        screen = apply_video_settings(settings)
                        camera.resize(screen.get_size())
                        full_map_img = pygame.transform.scale(original_nav_map, (WIDTH, HEIGHT))
                        night_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    clock.tick(0)
                    frame_clock.reset()
                    if res in ["MENU", "EXIT"]:
                        radio.stop()
                        save_last_session_stats()
                        return res
                    if radio_was_playing:
                        radio.resume()
                if (
                    keyboard.matches(event, pygame.K_f)
                    and game_state == "CITY"
                    and not phone_active
                ):
                    old_in_car = in_car  # Save the previous state before toggling.
                    nearby_car = nearby_traffic_car(atom.pos) if not in_car else None
                    if nearby_car is not None:
                        hijack_traffic_car(nearby_car)
                    else:
                        in_car = handle_car_logic(atom, car, in_car)

                    # Play the sound only when the state changes.
                    if in_car != old_in_car:
                        if in_car:
                            car_sfx['door_open'].play()
                            radio.resume()
                        else:
                            car_sfx['door_close'].play()
                            radio.pause()
                if (
                    event.type == pygame.KEYDOWN
                    and game_state == "CITY"
                    and not in_car
                    and not phone_active
                    and not (car.is_broken and atom.pos.distance_to(car.pos) < 100)
                    and keyboard.matches(event, pygame.K_r)
                ):
                    reload_weapon()
                if game_state == "CITY" and in_car and not getattr(event, "repeat", False):
                    if keyboard.matches(event, pygame.K_h):
                        manual_headlights = not manual_headlights
                    if keyboard.matches(event, pygame.K_e):
                        play_car_horn(car_sfx, horn_chan)
                        traffic.respond_to_horn(npc_cars, car.pos)
                    if keyboard.matches(event, pygame.K_v):
                        radio.toggle()
                    if keyboard.matches(event, pygame.K_COMMA):
                        radio.cycle_station(-1)
                    if keyboard.matches(event, pygame.K_PERIOD):
                        radio.cycle_station(1)
                sleep_key_pressed = (
                    keyboard.matches(event, pygame.K_e)
                    or event.key == pygame.K_t
                    or getattr(event, "unicode", "").lower() in ("t", "т")
                )
                if sleep_key_pressed:
                    if game_state == "HOUSE":
                        if is_at_sleep_spot(game_state, atom_h.pos):
                            sleep_requested = True
                        elif keyboard.matches(event, pygame.K_e) and check_house_exit(
                            atom_h, house_info
                        ):
                            scene_manager.transition("CITY")
                            game_state = scene_manager.current
                            atom.pos = pygame.Vector2(7731, 2326)
                    elif keyboard.matches(event, pygame.K_e) and not in_car:
                        if atom.pos.distance_to(pygame.Vector2(7738, 2330)) < 80:
                            scene_manager.transition("HOUSE")
                            game_state = scene_manager.current
                            atom_h.pos = pygame.Vector2(HOUSE_SLEEP_SPOT)
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and game_state == "CITY"
                and not in_car
                and not phone_active
            ):
                target_position = camera.screen_to_world(event.pos)
                if weapons.selected == "knife":
                    hit = weapons.melee_target(
                        atom.pos,
                        target_position,
                        [*npc_cars, *hostile_officers, *fleeing_drivers],
                    )
                    if hit is not None:
                        hit.is_alive = False
                        wanted.raise_level(2 if getattr(hit, "is_police", False) else 1)
                        honor_and_respect.change(honor=-20, respect=-15)
                else:
                    projectiles.extend(weapons.fire(atom.pos, target_position))
                direction = target_position - atom.pos
                if direction.length_squared():
                    atom.angle = -math.degrees(math.atan2(direction.x, direction.y))

        radio.update()

        # 2. Update the game state.

        if game_state == "CITY":
            target = car if in_car else atom

            # Update all traffic and pass the collision mask.
            # 1. Update traffic and police.
            for npc in npc_cars:
                # Pass the arguments used by traffic.py.
                npc.update(col_mask, car, npc_cars, traffic_state, frame_scale)
            if in_car:
                previous_car_pos = pygame.Vector2(car.pos)
                car.update(
                    keys,
                    col_mask,
                    True,
                    npc_cars,
                    frame_scale,
                    surface_map=world_bg,
                )
                atom.pos = pygame.Vector2(car.pos)
                travelled = previous_car_pos.distance_to(car.pos)
                if car.just_hit:
                    distance_since_crash = 0.0
                    current_drift_distance = 0.0
                else:
                    distance_since_crash += travelled
                    personal_records["distance_without_crash_m"] = max(
                        personal_records["distance_without_crash_m"],
                        distance_since_crash,
                    )
                    if car.is_drifting:
                        current_drift_distance += travelled
                        personal_records["longest_drift_m"] = max(
                            personal_records["longest_drift_m"],
                            current_drift_distance,
                        )
                    else:
                        current_drift_distance = 0.0
                personal_records["max_speed_kmh"] = max(
                    personal_records["max_speed_kmh"],
                    abs(car.speed) * 8,
                )
            else:
                atom.update(
                    keys,
                    col_mask,
                    car,
                    npc_cars,
                    frame_scale,
                    cursor_world=camera.screen_to_world(pygame.mouse.get_pos()),
                    armed=(
                        weapons.selected != "none"
                        and not weapons.wheel_open
                        and not phone_active
                    ),
                    can_sprint=survival.can_sprint and not phone_active,
                )
                car.update(
                    keys,
                    col_mask,
                    False,
                    npc_cars,
                    frame_scale,
                    surface_map=world_bg,
                )

                # Treasures and secrets.
                if "guard" not in collected_treasures and atom.pos.distance_to(pygame.Vector2(8909, 1139)) < 60:
                    money += 100
                    total_earned += 100
                    money_history.append(("+100", "guard"))
                    collected_treasures.add("guard")

                if "exit" not in collected_treasures and atom.pos.distance_to(pygame.Vector2(4549, 5245)) < 60:
                    money += 111
                    total_earned += 111
                    money_history.append(("+111", "bridge"))
                    collected_treasures.add("exit")

                # Repair logic.
                if car.is_broken and atom.pos.distance_to(car.pos) < 100:
                    if money >= 50 and keys[pygame.K_r]:
                        car.repair_progress += frame_scale
                        if car.repair_progress >= 180:  # Three seconds at 60 FPS.
                            car.health = car.max_health
                            car.is_broken = False
                            car.repair_progress = 0
                            money -= 50
                            total_spent += 50
                            money_history.append(("-50", "repair"))
                    else:
                        car.repair_progress = 0

            handle_surface_footsteps(keys, in_car, game_state, atom.pos, col_mask, step_sounds, foot_chan)
            handle_car_audio(car, in_car, car_sfx, engine_chan, crash_chan)
            update_combat(frame_scale)
            off_x, off_y = camera.follow(target.pos)
        else:
            atom_h.update(keys, house_collision, frame_scale)
            if "nightstand" not in collected_treasures:
                if atom_h.pos.distance_to(pygame.Vector2(206, 199)) < 40:
                    money += 200
                    total_earned += 200
                    money_history.append(("+200", "nightstand"))
                    collected_treasures.add("nightstand")

            if "sofa" not in collected_treasures:
                if atom_h.pos.distance_to(pygame.Vector2(723, 128)) < 40:
                    money += 300
                    total_earned += 300
                    money_history.append(("+300", "sofa"))
                    collected_treasures.add("sofa")
            handle_surface_footsteps(keys, in_car, game_state, atom_h.pos, None, step_sounds, foot_chan)

        if atom.health <= 0:
            fade_screen(screen, True, duration=0.35)
            radio.pause()
            if game_state != "HOUSE":
                scene_manager.transition("HOUSE")
            game_state = "HOUSE"
            in_car = False
            atom_h.pos.update(HOUSE_SLEEP_SPOT)
            atom.health = atom.max_health
            wanted.clear()
            projectiles.clear()
            hostile_officers.clear()
            weapons.ammo = 12
            car.speed = 0
            car.motion_velocity.update(0, 0)
            target = atom_h
            wake_fade_started = time.perf_counter()

        # 3. Build and render explicit engine-owned scene layers.
        frame_renderer.begin_frame()
        if game_state == "CITY":
            headlights_on = in_car and manual_headlights

            def draw_city_background():
                screen.fill((30, 30, 30))
                screen.blit(world_bg, (off_x, off_y))

            def draw_city_world():
                car.draw(screen, off_x, off_y)
                draw_car_smoke(screen, car, off_x, off_y)
                for npc in npc_cars:
                    npc.draw(screen, off_x, off_y)
                for driver in fleeing_drivers:
                    driver.draw(screen, off_x, off_y)
                for officer in hostile_officers:
                    officer.draw(screen, off_x, off_y)
                for projectile in projectiles:
                    projectile.draw(screen, off_x, off_y)
                if in_car:
                    return

                screen_position = camera.world_to_screen(atom.pos)
                draw_atom_character(
                    screen, screen_position.x, screen_position.y, atom_img, atom.angle
                )
                if weapons.selected != "none" and not weapons.wheel_open:
                    draw_handgun(
                        screen,
                        atom.pos,
                        camera.screen_to_world(pygame.mouse.get_pos()),
                        off_x,
                        off_y,
                        atom.angle,
                        weapons.selected,
                    )
                draw_city_hints(screen, small_font, atom, car, t)
                if nearby_traffic_car(atom.pos) is not None:
                    steal_text = small_font.render(t["steal_hint"], True, (255, 210, 100))
                    screen.blit(
                        steal_text,
                        (WIDTH // 2 - steal_text.get_width() // 2, HEIGHT - 155),
                    )
                if car.is_broken and atom.pos.distance_to(car.pos) < 100:
                    rendered = small_font.render(t["repair"], True, (255, 255, 255))
                    screen.blit(
                        rendered,
                        (WIDTH // 2 - rendered.get_width() // 2, HEIGHT // 2 + 100),
                    )
                    if car.repair_progress > 0:
                        pygame.draw.rect(
                            screen, (0, 0, 0),
                            (WIDTH // 2 - 100, HEIGHT // 2 + 140, 200, 15),
                        )
                        progress_width = int(200 * (car.repair_progress / 180))
                        pygame.draw.rect(
                            screen, (0, 120, 255),
                            (WIDTH // 2 - 100, HEIGHT // 2 + 140, progress_width, 15),
                        )
                        pygame.draw.rect(
                            screen, (255, 255, 255),
                            (WIDTH // 2 - 100, HEIGHT // 2 + 140, 200, 15), 2,
                        )

            def draw_city_lighting():
                ambient = get_ambient_color(game_time)
                if ambient[3] > 0:
                    night_overlay.fill(ambient)
                    screen.blit(night_overlay, (0, 0))
                if headlights_on:
                    car.draw_headlights(screen, off_x, off_y, col_mask)

            def draw_city_ui():
                if in_car:
                    car.draw_speedometer(screen)
                draw_player_status(
                    screen,
                    atom,
                    weapons.ammo,
                    weapons.reserve_ammo,
                    wanted.level,
                    t,
                )
                weapons.draw(screen, t)
                draw_gta_minimap(
                    screen,
                    original_nav_map,
                    target,
                    current_world_width,
                    current_world_height,
                    gps=gps,
                    labels=t,
                    hunger=survival.hunger,
                    health=atom.health,
                )
                if in_car:
                    radio_label = t["radio_on"] if radio.is_on else t["radio_off"]
                    screen.blit(
                        small_font.render(
                            radio_label.format(
                                station=radio.station_name,
                                genre=t[radio.station_genre_key],
                                track=radio.track_name,
                            ),
                            True,
                            (255, 255, 255),
                        ),
                        (20, 50),
                    )
                else:
                    hint = small_font.render(t["weapon_hint"], True, (255, 255, 255))
                    screen.blit(hint, (20, HEIGHT - hint.get_height() - 20))

            frame_renderer.submit(RenderLayer.BACKGROUND, draw_city_background)
            frame_renderer.submit(RenderLayer.WORLD, draw_city_world)
            frame_renderer.submit(RenderLayer.LIGHTING, draw_city_lighting)
            frame_renderer.submit(RenderLayer.UI, draw_city_ui)
        else:
            def draw_house_background():
                draw_house_scene(
                    screen, house_visual, house_info, atom_h, small_font, t
                )

            def draw_house_ui():
                if is_at_sleep_spot(game_state, atom_h.pos):
                    sleep_text = small_font.render(t["sleep_save"], True, (255, 255, 255))
                    screen.blit(
                        sleep_text,
                        sleep_text.get_rect(center=(WIDTH // 2, HEIGHT - 80)),
                    )

            frame_renderer.submit(RenderLayer.BACKGROUND, draw_house_background)
            frame_renderer.submit(RenderLayer.UI, draw_house_ui)
        frame_renderer.render()

        # In-game clock.
        h, m = int(game_time / 60), int(game_time % 60)
        time_text = small_font.render(f"{h:02d}:{m:02d}", True, (255, 255, 255))
        screen.blit(time_text, (WIDTH - 100, 20))

        if show_debug:
            draw_debug_coords(
                screen,
                (atom_h if game_state == "HOUSE" else target),
                game_state,
                clock.get_fps(),
            )
        if phone_y_offset < 449.0:
            draw_mobile_phone(screen, money, game_time, small_font,
                                     current_app, phone_settings, phone_y_offset, money_history,
                                     current_lang_name)

        if wake_fade_started is not None:
            fade_progress = (time.perf_counter() - wake_fade_started) / 1.2
            if fade_progress >= 1:
                wake_fade_started = None
            else:
                wake_overlay.fill((0, 0, 0))
                wake_overlay.set_alpha(round(255 * (1 - fade_progress)))
                screen.blit(wake_overlay, (0, 0))

        pygame.display.flip()
        if sleep_requested:
            fade_screen(screen, True)
            game_time = (game_time + 540) % 1440
            survival.advance(540, atom)
            if atom.health <= 0:
                atom.health = atom.max_health
                atom_h.pos.update(HOUSE_SLEEP_SPOT)
            save_sleep_game()
            sleep_requested = False
            wake_fade_started = time.perf_counter()

    save_last_session_stats()
    return "EXIT"
