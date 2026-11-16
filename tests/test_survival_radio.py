import os
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

import engine


class FakePlayer:
    def __init__(self, health=100.0):
        self.health = health
        self.max_health = 100.0

    def take_damage(self, amount):
        self.health = max(0.0, self.health - amount)


class SurvivalAndRadioTests(unittest.TestCase):
    def test_winter_weather_is_limited_to_snow_or_ice(self):
        for month in (12, 1, 2):
            weather = engine.WeatherSystem(date(2026, month, 15))
            self.assertIn(weather.weather, {"snow", "ice"})
            self.assertLess(weather.grip_multiplier, 1.0)

    def test_non_winter_weather_has_no_ice_or_snow(self):
        for month in (3, 6, 9):
            weather = engine.WeatherSystem(date(2026, month, 15))
            self.assertIn(weather.weather, {"clear", "rain", "fog"})

    def test_radio_stations_have_all_bundled_tracks(self):
        self.assertEqual(len(engine._RADIO_STATIONS), 3)
        self.assertEqual(sum(len(station.tracks) for station in engine._RADIO_STATIONS), 6)
        self.assertTrue(
            all(
                (engine._ASSET_ROOT / track.path).is_file()
                for station in engine._RADIO_STATIONS
                for track in station.tracks
            )
        )

    def test_hunger_drains_per_crossed_in_game_hour(self):
        needs = engine.SurvivalNeeds()
        player = FakePlayer(health=80)

        self.assertEqual(needs.advance(59, player), 0)
        self.assertEqual(needs.hunger, 100)
        self.assertEqual(needs.advance(1, player), 1)
        self.assertEqual(needs.hunger, 95)
        self.assertEqual(player.health, 85)

    def test_sleep_sets_hunger_to_seventy_percent_from_any_starting_value(self):
        for hunger in (100, 70, 25, 0):
            with self.subTest(hunger=hunger):
                needs = engine.SurvivalNeeds(hunger=hunger, minutes_into_hour=12)
                needs.sleep(540, FakePlayer())

                self.assertEqual(needs.hunger, 70)
                self.assertEqual(needs.minutes_into_hour, 12)

    def test_regeneration_applies_for_an_hour_started_above_seventy_hunger(self):
        needs = engine.SurvivalNeeds(hunger=75)
        player = FakePlayer(health=80)

        needs.advance(60, player)

        self.assertEqual(needs.hunger, 70)
        self.assertEqual(player.health, 85)

    def test_sprint_is_disabled_at_twenty_hunger(self):
        needs = engine.SurvivalNeeds(hunger=25)
        player = FakePlayer()

        needs.advance(60, player)

        self.assertEqual(needs.hunger, 20)
        self.assertFalse(needs.can_sprint)

    def test_starvation_damage_starts_an_hour_after_hunger_reaches_zero(self):
        needs = engine.SurvivalNeeds(hunger=5)
        player = FakePlayer(health=50)

        needs.advance(60, player)
        self.assertEqual(needs.hunger, 0)
        self.assertEqual(player.health, 50)
        needs.advance(60, player)
        self.assertEqual(player.health, 40)

    def test_armed_player_faces_cursor_without_moving_toward_it(self):
        with patch("engine.load_image", return_value=pygame.Surface((48, 48))):
            player = engine.Player(100, 100)
        collision = pygame.Surface((200, 200))
        collision.fill((255, 255, 255))
        keys = {key: False for key in (
            pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d,
            pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
            pygame.K_LSHIFT,
        )}

        player.update(
            keys,
            collision,
            cursor_world=(150, 100),
            armed=True,
        )

        self.assertEqual(player.pos, pygame.Vector2(100, 100))
        self.assertEqual(player.angle, -90)

    def test_left_shift_sprint_uses_hunger_permission(self):
        collision = pygame.Surface((200, 200))
        collision.fill((255, 255, 255))
        keys = {key: False for key in (
            pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d,
            pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
            pygame.K_LSHIFT,
        )}
        keys[pygame.K_d] = True
        keys[pygame.K_LSHIFT] = True
        positions = []
        with patch("engine.load_image", return_value=pygame.Surface((48, 48))):
            for can_sprint in (True, False):
                player = engine.Player(50, 50)
                player.update(keys, collision, can_sprint=can_sprint)
                positions.append(player.pos.x)

        self.assertGreater(positions[0] - 50, positions[1] - 50)

    def test_hunger_and_hour_progress_are_in_saved_game_state(self):
        atom = SimpleNamespace(pos=pygame.Vector2(10, 20), angle=30, health=80)
        atom_h = SimpleNamespace(pos=pygame.Vector2(5, 6), angle=0)
        car = SimpleNamespace(
            pos=pygame.Vector2(30, 40), angle=90, speed=2,
            health=150, is_broken=False,
        )
        weapons = SimpleNamespace(
            ammo=4,
            reserve_ammo=9,
            selected="pistol",
            ammo_by_weapon={"pistol": 4},
            reserve_ammo_by_weapon={"pistol": 9},
        )
        wanted = SimpleNamespace(level=1, escape_timer=2)
        reputation = SimpleNamespace(honor=5, respect=6)
        survival = engine.SurvivalNeeds(hunger=45, minutes_into_hour=12.5)

        state = engine.build_game_state_data(
            "CITY", atom, atom_h, car, weapons, wanted, reputation,
            100, 50, 10, 510, set(), 0, 0, survival,
        )

        self.assertEqual(state["hunger"], 45)
        self.assertEqual(state["survival_minute_progress"], 12.5)

    def test_radio_resumes_at_live_station_position(self):
        now = [0.0]
        radio = engine.GameRadio({}, monotonic_clock=lambda: now[0], allow_playback=True)
        music = pygame.mixer.music
        with (
            patch.object(music, "load") as load,
            patch.object(music, "play") as play,
            patch.object(music, "stop") as stop,
            patch.object(music, "get_busy", return_value=True),
        ):
            radio.toggle()
            self.assertTrue(radio.is_on)
            now[0] = 30.0
            radio.toggle()
            stop.assert_called_once_with()
            now[0] = 90.0
            radio.toggle()

        self.assertTrue(radio.is_on)
        self.assertEqual(load.call_count, 2)
        self.assertEqual(play.call_args.kwargs, {"start": 90.0})

    def test_radio_live_playlist_moves_to_next_track_at_exact_boundary(self):
        now = [0.0]
        radio = engine.GameRadio({}, monotonic_clock=lambda: now[0], allow_playback=True)

        now[0] = engine._RADIO_STATIONS[0].tracks[0].duration

        self.assertEqual(radio.track_name, "rooms for music.")

    def test_radio_stops_when_leaving_car_and_resumes_on_return(self):
        radio = engine.GameRadio(
            {}, monotonic_clock=lambda: 0.0, allow_playback=True, in_game=True
        )
        music = pygame.mixer.music
        with (
            patch.object(music, "load"),
            patch.object(music, "play") as play,
            patch.object(music, "stop") as stop,
            patch.object(music, "get_busy", return_value=True),
        ):
            radio.toggle()
            self.assertTrue(radio.is_playing)
            radio.pause_for_exit()
            stop.assert_called_once_with()
            self.assertFalse(radio.is_playing)
            self.assertTrue(radio.is_on)
            radio.update()
            play.assert_called_once()
            radio.resume()
            self.assertTrue(radio.is_playing)

    def test_engine_radio_accepts_in_game_construction(self):
        radio = engine.GameRadio(
            {"music_volume": 50}, allow_playback=True, in_game=True
        )
        self.assertTrue(radio.in_game)
        self.assertTrue(radio.allow_playback)

    def test_radio_plays_while_in_game(self):
        radio = engine.GameRadio({}, monotonic_clock=lambda: 0.0, allow_playback=True, in_game=True)
        music = pygame.mixer.music
        with (
            patch.object(music, "load") as load,
            patch.object(music, "play") as play,
            patch.object(music, "get_busy", return_value=True),
        ):
            radio.toggle()
            radio.update()
        self.assertTrue(radio.is_playing)
        load.assert_called_once()
        play.assert_called_once()

    def test_radio_does_not_play_mixer_when_playback_disabled(self):
        radio = engine.GameRadio({}, allow_playback=False)
        music = pygame.mixer.music
        with (
            patch.object(music, "load") as load,
            patch.object(music, "play") as play,
            patch.object(music, "stop") as stop,
            patch.object(music, "pause") as pause,
        ):
            radio.toggle()
            radio.cycle_station(1)
            radio.pause()
            radio.stop()

        load.assert_not_called()
        play.assert_not_called()
        stop.assert_not_called()
        pause.assert_not_called()
        self.assertFalse(radio.is_on)
        self.assertFalse(radio.is_playing)

    def _assert_color_close(self, actual, expected, tol=18):
        self.assertEqual(len(actual), 3)
        self.assertEqual(len(expected), 3)
        for a, e in zip(actual, expected):
            self.assertLessEqual(abs(a - e), tol, msg=f"{actual} not within ±{tol} of {expected}")

    def test_minimap_keeps_full_radar_inside_separate_status_arcs(self):
        screen = pygame.Surface((800, 600))
        background = pygame.Surface((80, 80))
        background.fill((80, 110, 80))
        target = type("Target", (), {"pos": pygame.Vector2(40, 40)})()

        with patch.object(engine, "_get_house_icon", return_value=None):
            engine.draw_gta_minimap(
                screen,
                background,
                target,
                80,
                80,
                labels={
                    "hunger_meter": "СИТІСТЬ {value}%",
                    "health_meter": "ЗД {value}%",
                },
                hunger=55,
                health=70,
            )

        self.assertEqual(screen.get_size(), (800, 600))
        # The radar occupies the lower-right corner; glass/vignette may subtly tint the map.
        radar_px = screen.get_at((670, 520))[:3]
        self._assert_color_close(radar_px, (80, 110, 80), tol=20)
        self.assertGreater(radar_px[1], radar_px[0], "radar sample should remain greenish")
        self.assertEqual(screen.get_at((130, 520))[:3], (0, 0, 0))
        # The outer ring keeps distinct green-health and orange-hunger arcs.
        health_arc = screen.get_at((779, 470))[:3]
        hunger_arc = screen.get_at((561, 470))[:3]
        self.assertGreater(health_arc[1], 140, health_arc)
        self.assertGreater(health_arc[1], health_arc[0], health_arc)
        self.assertGreater(hunger_arc[0], 180, hunger_arc)
        self.assertGreater(hunger_arc[1], 100, hunger_arc)
        self.assertGreater(hunger_arc[0], hunger_arc[2], hunger_arc)


if __name__ == "__main__":
    unittest.main()
