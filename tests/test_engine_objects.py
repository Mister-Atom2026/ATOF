
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import engine
import constants


class WantedAndHonorTests(unittest.TestCase):
    def test_wanted_bounds_and_clear(self):
        w = engine.WantedLevel(10)
        self.assertEqual(w.level, 5)
        w.clear()
        self.assertEqual(w.level, 0)

    def test_raise_wanted(self):
        w = engine.WantedLevel(0)
        w.raise_level(2)
        self.assertEqual(w.level, 2)

    def test_honor_and_respect_clamp(self):
        hr = engine.HonorAndRespect(999, -999)
        self.assertEqual(hr.honor, 100.0)
        self.assertEqual(hr.respect, -100.0)
        hr.change(honor=-10, respect=10)
        self.assertEqual(hr.honor, 90.0)
        self.assertEqual(hr.respect, -90.0)


class WeaponWheelTests(unittest.TestCase):
    def test_new_game_defaults(self):
        w = engine.WeaponWheel.new_game()
        self.assertIn('pistol', w.WEAPONS)
        self.assertIn(w.selected, w.WEAPONS)

    def test_weapon_stats_exist(self):
        self.assertIn('pistol', engine.WeaponWheel.WEAPON_STATS)
        self.assertIn('shotgun', engine.WeaponWheel.WEAPON_STATS)

    def test_ammo_capacities(self):
        self.assertGreater(engine.WeaponWheel.WEAPON_STATS['pistol']['mag_size'], 0)
        self.assertGreater(engine.WeaponWheel.WEAPON_STATS['pistol']['reserve_max'], 0)
        self.assertEqual(engine.WeaponWheel.STARTING_AMMO['pistol'], 7)


class CarAndPlayerTests(unittest.TestCase):
    def test_car_initial_state(self):
        c = engine.Car(100, 200)
        self.assertEqual(tuple(map(int, c.pos)), (100, 200))
        self.assertTrue(hasattr(c, 'health'))
        self.assertTrue(hasattr(c, 'max_speed'))

    def test_player_initial_state(self):
        p = engine.Player(10, 20)
        self.assertEqual(tuple(map(int, p.pos)), (10, 20))
        self.assertEqual(p.health, 100.0)

    def test_house_player_initial_state(self):
        h = engine.HousePlayer(5, 6)
        self.assertEqual(tuple(map(int, h.pos)), (5, 6))


class GunshopConstantsTests(unittest.TestCase):
    def test_gunshop_constants_defined(self):
        self.assertEqual(tuple(map(int, engine.GUNSHOP_POS)), (10027, 4902))
        self.assertEqual(engine.GUNSHOP_RADIUS, 80)
        self.assertEqual(engine.GUNSHOP_ENTRY_SPOT, (352, 40))
        self.assertEqual(tuple(map(int, engine.GUNSHOP_EXIT_SPOT)), (352, 0))
        self.assertEqual(engine.GUNSHOP_EXIT_RADIUS, 40)
        self.assertEqual(tuple(map(int, engine.GUNSHOP_COUNTER_POS)), (145, 224))

    def test_interaction_texts_have_gunshop_keys(self):
        for lang in engine.SUPPORTED_LANGUAGES:
            t = engine._INTERACTION_TEXTS[lang]
            self.assertIn('enter_gunshop', t)
            self.assertIn('exit_gunshop', t)
            self.assertTrue(t['enter_gunshop'])
            self.assertTrue(t['exit_gunshop'])

    def test_garage_texts_for_all_languages(self):
        for lang in engine.SUPPORTED_LANGUAGES:
            gt = engine._GARAGE_TEXTS[lang]
            self.assertIn('title', gt)
            self.assertIn('take', gt)
            self.assertIn('leave', gt)
            self.assertEqual(len(gt['engine_tiers']), 6)
            self.assertEqual(len(gt['wheel_tiers']), 6)
