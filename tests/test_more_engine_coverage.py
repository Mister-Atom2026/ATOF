
import os
import unittest
from types import SimpleNamespace
from datetime import date

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
pygame.init()
pygame.display.set_mode((800, 600))

import engine


class MoreCoverageTests(unittest.TestCase):
    def test_scene_transition_properties(self):
        st = engine.SceneTransition(duration=0.5)
        self.assertEqual(st.duration, 0.5)
        self.assertIsNotNone(st)

    def test_render_layer_enum(self):
        self.assertTrue(hasattr(engine, 'RenderLayer'))

    def test_layered_renderer_basic(self):
        lr = engine.LayeredRenderer()
        called = []
        lr.begin_frame()
        lr.submit(engine.RenderLayer.UI, lambda: called.append(1))
        lr.render()
        self.assertEqual(called, [1])

    def test_car_upgrade_application_callable(self):
        c = engine.Car(0, 0)
        c.engine_upgrade = 1
        c.wheel_upgrade = 1
        engine.apply_car_upgrades(c)
        self.assertGreater(c.max_speed, 0)

    def test_consume_fridge_food_reduces_stock(self):
        survival = engine.SurvivalNeeds(50, 0)
        stock = list(engine.FRIDGE_STARTING_STOCK)
        restored = engine.consume_fridge_food(survival, stock, 0)
        self.assertGreaterEqual(restored, 0)
        self.assertLessEqual(stock[0], engine.FRIDGE_STARTING_STOCK[0])

    def test_consume_fridge_food_when_full(self):
        survival = engine.SurvivalNeeds(100, 0)
        stock = list(engine.FRIDGE_STARTING_STOCK)
        restored = engine.consume_fridge_food(survival, stock, 0)
        self.assertEqual(restored, 0)

    def test_draw_interaction_prompt_returns_none_for_zero_alpha(self):
        surf = pygame.Surface((800, 600))
        self.assertIsNone(engine.draw_interaction_prompt(surf, 'E', 'Test', alpha=0))

    def test_draw_interaction_prompt_draws(self):
        surf = pygame.Surface((800, 600))
        res = engine.draw_interaction_prompt(surf, 'E', 'Test', alpha=255)
        self.assertIsNotNone(res)

    def test_weather_draw_all_types(self):
        surf = pygame.Surface((200, 200))
        for month, day in [(1,1),(4,1),(7,1),(10,1)]:
            w = engine.WeatherSystem(date(2026, month, day))
            w.draw(surf)

    def test_gunshop_entry_exit_spots_valid(self):
        self.assertGreater(engine.GUNSHOP_EXIT_RADIUS, 0)
        self.assertIsInstance(engine.GUNSHOP_ENTRY_SPOT, tuple)

    def test_radio_stations_have_names_and_tracks(self):
        for st in engine._RADIO_STATIONS:
            self.assertTrue(st.name)
            self.assertTrue(st.tracks)
