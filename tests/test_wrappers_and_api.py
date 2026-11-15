
import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import engine
import open_world
import video_intro
import house
import navigator


class WrapperTests(unittest.TestCase):
    def test_open_world_run_delegates_to_engine(self):
        with patch.object(engine, 'run_open_world', return_value='OK') as m:
            self.assertEqual(open_world.run(None, {}, continue_game=False), 'OK')
            m.assert_called_once()

    def test_video_intro_exports(self):
        self.assertIs(video_intro.play_intro_videos, engine.play_intro_videos)
        self.assertTrue(hasattr(video_intro, 'VIDEO_EXTENSIONS'))

    def test_house_and_navigator_reexports(self):
        self.assertIs(house.HousePlayer, engine.HousePlayer)
        self.assertIs(navigator.GPS, engine.GPS)


class EngineAPITests(unittest.TestCase):
    def test_handle_car_logic_enter_exit(self):
        atom = engine.Player(100, 100)
        car = engine.Car(100, 100)
        self.assertTrue(engine.handle_car_logic(atom, car, False))
        atom.pos.update(500, 500)
        self.assertFalse(engine.handle_car_logic(atom, car, False))
        self.assertFalse(engine.handle_car_logic(atom, car, True))

    def test_check_house_exit_false_on_wrong_color(self):
        info = pygame.Surface((10, 10))
        info.fill((0, 0, 0))
        atom_h = engine.HousePlayer(5, 5)
        self.assertFalse(engine.check_house_exit(atom_h, info))

    def test_projectile_creation_and_update(self):
        p = engine.create_projectile((0, 0), (100, 0), 'player', speed=10.0, damage=5.0)
        self.assertIsNotNone(p)
        alive = p.update(1.0)
        self.assertIsInstance(alive, bool)

    def test_projectile_hits_wall_helper(self):
        mask = pygame.Surface((50, 50))
        mask.fill((255, 255, 255))
        self.assertFalse(engine.projectile_hits_wall((0, 0), (10, 10), mask))

    def test_camera_resize_and_follow(self):
        cam = engine.Camera2D((800, 600), (2000, 2000))
        cam.resize((1024, 768))
        self.assertEqual(tuple(map(int, cam.viewport_size)), (1024, 768))
        cam.follow(pygame.Vector2(500, 500))
        self.assertIsInstance(cam.offset.x, (int, float))

    def test_scene_manager_register_and_hooks(self):
        sm = engine.SceneManager('A')
        sm.register('A')
        sm.register('B')
        self.assertIn('A', sm._hooks)
        self.assertIn('B', sm._hooks)

    def test_fade_screen_function_exists(self):
        self.assertTrue(callable(engine.fade_screen))

    def test_load_image_callable(self):
        self.assertTrue(callable(engine.load_image))
