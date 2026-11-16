"""Radio/music playback primitives for ATOF.

In-game radio is enabled: stations behave like modern open-world game radio —
a live playlist clock keeps running while the player tunes away, switching
stations resumes at the current position, and volume follows the music setting.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import pygame


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


ASSET_ROOT = Path(__file__).resolve().parent


RADIO_STATIONS: tuple[RadioStation, ...] = (
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
            RadioTrack(
                "Soft and Furious - 02 - Queen",
                "radio/night_shift/soft_and_furious_queen.ogg",
                205.427982,
            ),
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

# Backward-compatible alias for older engine code.
_RADIO_STATIONS = RADIO_STATIONS


def get_music_volume(audio_settings: dict | None = None) -> float:
    if isinstance(audio_settings, dict):
        try:
            return float(audio_settings.get("music_volume", 0.2))
        except (TypeError, ValueError):
            return 0.2
    return 0.2


class GameRadio:
    """Play stations as live playlists whose clocks keep running while tuned away."""

    def __init__(
        self,
        settings,
        *,
        monotonic_clock=None,
        allow_playback=True,
        in_game=False,
        audio_settings: dict | None = None,
        asset_root: Path | None = None,
    ):
        self.settings = settings
        self.monotonic_clock = monotonic_clock or time.monotonic
        self._allow_playback = bool(allow_playback)
        self._in_game = bool(in_game)
        self.audio_settings = audio_settings
        self.asset_root = asset_root or ASSET_ROOT
        self.started_at = self.monotonic_clock()
        self.station_index = 0
        self.silent_mode = True
        self.is_on = False
        self.is_playing = False
        self._paused_for_game = False
        self._loaded_track: tuple[int, int] | None = None

    @property
    def allow_playback(self) -> bool:
        return self._allow_playback

    @allow_playback.setter
    def allow_playback(self, value: bool) -> None:
        self._allow_playback = bool(value)
        if not self._playback_permitted:
            self._stop_audio_only()

    @property
    def in_game(self) -> bool:
        return self._in_game

    @property
    def _playback_permitted(self) -> bool:
        # Radio now plays in-game as well; only the explicit flag can mute it.
        return bool(self.allow_playback)

    def set_in_game(self, in_game: bool) -> None:
        self._in_game = bool(in_game)

    @property
    def station_name(self) -> str:
        if self.silent_mode:
            return "Radio Silent"
        return RADIO_STATIONS[self.station_index].name

    @property
    def station_genre_key(self) -> str:
        if self.silent_mode:
            return "radio_genre_silent"
        return RADIO_STATIONS[self.station_index].genre_key

    @property
    def track_name(self) -> str:
        station = RADIO_STATIONS[self.station_index]
        track_index, _offset = self._live_track_position(self.station_index)
        return station.tracks[track_index].title

    def _live_track_position(self, station_index: int, now: float | None = None) -> tuple[int, float]:
        station = RADIO_STATIONS[station_index]
        if not station.tracks:
            return 0, 0.0
        now = self.monotonic_clock() if now is None else now
        playlist_duration = sum(track.duration for track in station.tracks)
        if playlist_duration <= 0:
            return 0, 0.0
        playlist_position = max(0.0, now - self.started_at) % playlist_duration
        for track_index, track in enumerate(station.tracks):
            if playlist_position < track.duration:
                return track_index, playlist_position
            playlist_position -= track.duration
        return 0, 0.0

    def _stop_audio_only(self) -> None:
        if self._playback_permitted:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self.is_playing = False
        self._loaded_track = None

    def _play_live_track(self, *, force: bool = False) -> None:
        station = RADIO_STATIONS[self.station_index]
        if not station.tracks or self.silent_mode or not self.is_on or self._paused_for_game:
            return
        track_index, offset = self._live_track_position(self.station_index)
        track_key = (self.station_index, track_index)
        if not self._playback_permitted:
            # Playback explicitly disabled: the live station clock keeps running.
            self._loaded_track = track_key
            self.is_playing = False
            return
        if self._loaded_track == track_key and self.is_playing and pygame.mixer.music.get_busy():
            return
        if self._loaded_track == track_key and self.is_playing and not force:
            return
        try:
            pygame.mixer.music.load(str(self.asset_root / station.tracks[track_index].path))
            pygame.mixer.music.play(start=offset)
            pygame.mixer.music.set_volume(get_music_volume(self.audio_settings))
            self._loaded_track = track_key
            self.is_playing = True
        except pygame.error:
            self.is_playing = False

    def toggle(self) -> None:
        if self.silent_mode:
            self.silent_mode = False
            self.is_on = True
            self._play_live_track(force=True)
            return
        self.is_on = not self.is_on
        self._paused_for_game = False
        if not self.is_on:
            self._stop_audio_only()
            return
        self._play_live_track(force=True)

    def pause(self) -> None:
        if self.is_playing or self.is_on:
            if self._playback_permitted and self.is_playing:
                try:
                    pygame.mixer.music.pause()
                except Exception:
                    pass
            self.is_playing = False
            self._paused_for_game = True

    def resume(self) -> None:
        if not self._paused_for_game:
            return
        self._paused_for_game = False
        if self.is_on:
            self._play_live_track(force=True)

    def cycle_station(self, direction: int) -> None:
        position = 0 if self.silent_mode else self.station_index + 1
        position = (position + direction) % (len(RADIO_STATIONS) + 1)
        self.silent_mode = position == 0
        if not self.silent_mode:
            self.station_index = position - 1
        self.is_on = not self.silent_mode
        self.is_playing = False
        self._loaded_track = None
        if self.is_on and not self._paused_for_game:
            self._play_live_track(force=True)
        else:
            self._stop_audio_only()

    def update(self) -> None:
        if self.is_on and not self._paused_for_game:
            self._play_live_track()

    def stop(self) -> None:
        self._stop_audio_only()
        self.silent_mode = True
        self.is_on = False
        self._paused_for_game = False
