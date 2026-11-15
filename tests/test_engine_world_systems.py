
import os
import math
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import engine


class GPSTests(unittest.TestCase):
    def test_gps_set_clear_and_distance(self):
        gps = engine.GPS()
        self.assertIsNone(gps.destination)
        self.assertIsNone(gps.distance_to((0, 0)))
        gps.set_destination((100, 100))
        self.assertAlmostEqual(gps.distance_to((100, 100)), 0.0)
        self.assertAlmostEqual(gps.distance_to((100, 200)), 100.0)
        gps.clear_destination()
        self.assertIsNone(gps.destination)

    def test_get_dist_static(self):
        self.assertAlmostEqual(engine.GPS.get_dist((0, 0), (3, 4)), 5.0)


class WeatherSystemTests(unittest.TestCase):
    def test_label_returns_string_for_languages(self):
        w = engine.WeatherSystem(date(2026, 7, 1))
        for lang in engine.SUPPORTED_LANGUAGES:
            self.assertIsInstance(w.label(lang), str)

    def test_winter_grip_reduced(self):
        w = engine.WeatherSystem(date(2026, 1, 10))
        self.assertLessEqual(w.grip_multiplier, 1.0)

    def test_non_winter_grip_and_types(self):
        w = engine.WeatherSystem(date(2026, 6, 10))
        self.assertIn(w.weather, {'clear', 'rain', 'fog'})
        self.assertGreater(w.grip_multiplier, 0)

    def test_update_changes_timer(self):
        w = engine.WeatherSystem(date(2026, 6, 10))
        t0 = w.timer
        w.update(1.0)
        self.assertNotEqual(w.timer, t0)

    def test_draw_does_not_crash(self):
        surf = pygame.Surface((200, 200))
        for month in (1, 6):
            w = engine.WeatherSystem(date(2026, month, 10))
            w.draw(surf)


class RadioTests(unittest.TestCase):
    def test_stations_and_tracks_exist(self):
        self.assertEqual(len(engine._RADIO_STATIONS), 3)
        total = sum(len(s.tracks) for s in engine._RADIO_STATIONS)
        self.assertGreaterEqual(total, 6)

    def test_game_radio_initial_state_and_toggle(self):
        r = engine.GameRadio({'music_volume': 50})
        self.assertFalse(r.is_on)
        r.cycle_station(1)
        self.assertEqual(r.station_index, 0)
        r.stop()
        self.assertFalse(r.is_on)


class SurvivalTests(unittest.TestCase):
    def test_hunger_clamped(self):
        s = engine.SurvivalNeeds(150, 0)
        self.assertEqual(s.hunger, 100.0)
        s = engine.SurvivalNeeds(-5, 0)
        self.assertEqual(s.hunger, 0.0)

    def test_sleep_caps_and_regen_logic(self):
        p = SimpleNamespace(health=50, max_health=100, take_damage=lambda a: None)
        s = engine.SurvivalNeeds(10, 0)
        s.sleep(60, p)
        self.assertEqual(s.hunger, 70.0)
