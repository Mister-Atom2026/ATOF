
import os
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import engine


class HelperFunctionTests(unittest.TestCase):
    def test_is_at_sleep_spot(self):
        self.assertTrue(engine.is_at_sleep_spot('HOUSE', engine.HOUSE_SLEEP_SPOT))
        self.assertFalse(engine.is_at_sleep_spot('CITY', engine.HOUSE_SLEEP_SPOT))
        self.assertFalse(engine.is_at_sleep_spot('HOUSE', (0, 0)))

    def test_format_gps_distance(self):
        s = engine._format_gps_distance(50)
        self.assertIsInstance(s, str)
        s2 = engine._format_gps_distance(1500)
        self.assertIsInstance(s2, str)

    def test_interaction_text_fallback(self):
        self.assertIsInstance(engine._interaction_text('English', 'enter_house'), str)
        self.assertIsInstance(engine._interaction_text('Українська', 'sleep'), str)

    def test_fridge_foods_and_stock(self):
        self.assertEqual(len(engine.FRIDGE_FOODS), 3)
        self.assertEqual(len(engine.FRIDGE_STARTING_STOCK), 3)

    def test_supported_languages(self):
        self.assertEqual(len(engine.SUPPORTED_LANGUAGES), 6)

    def test_weapon_textures_and_assets_paths_constants(self):
        self.assertTrue(hasattr(engine, 'GUNSHOP_POS'))
        self.assertTrue(hasattr(engine, 'GUNSHOP_EXIT_SPOT'))


class SceneAndCameraExtraTests(unittest.TestCase):
    def test_scene_manager_initial_state(self):
        sm = engine.SceneManager('CITY')
        self.assertEqual(sm.current, 'CITY')

    def test_camera_world_to_screen_and_back(self):
        cam = engine.Camera2D((800, 600), (4000, 4000))
        cam.offset.update(0, 0)
        s = cam.world_to_screen(pygame.Vector2(100, 100))
        w = cam.screen_to_world(s)
        self.assertAlmostEqual(w.x, 100, delta=1)
        self.assertAlmostEqual(w.y, 100, delta=1)

    def test_frame_clock_basic(self):
        clock = pygame.time.Clock()
        fc = engine.FrameClock()
        dt = fc.tick(clock, 60)
        self.assertIsInstance(dt, float)
