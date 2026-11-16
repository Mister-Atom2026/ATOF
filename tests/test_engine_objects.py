
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

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


class LocalizationCompletenessTests(unittest.TestCase):
    """Guard UI strings that are rendered outside the shared label tables."""

    def test_controls_menu_labels_for_all_languages(self):
        import main

        keys = (
            'controls_up', 'controls_down', 'controls_left', 'controls_right',
            'controls_interact', 'controls_enter_vehicle', 'controls_reload',
            'controls_sprint', 'controls_map', 'controls_phone',
            'controls_handbrake', 'controls_quick_nav', 'controls_journal',
            'controls_hint',
        )
        for lang in engine.SUPPORTED_LANGUAGES:
            labels = main._CONTROLS_TRANSLATIONS[lang]
            for key in keys:
                self.assertTrue(labels.get(key), f'{lang}.{key} missing')

    def test_tutorial_steps_for_all_languages(self):
        import engine_tutorial

        for lang in engine.SUPPORTED_LANGUAGES:
            steps = engine_tutorial.TUTORIAL_STEPS_BY_LANGUAGE[lang]
            self.assertEqual(len(steps), 12, lang)
            for index, step in enumerate(steps, 1):
                self.assertEqual(len(step), 3, f'{lang} step {index}')
                self.assertTrue(
                    all(isinstance(part, str) and part.strip() for part in step),
                    f'{lang} step {index} incomplete',
                )

    def test_story_ui_keys_for_all_languages(self):
        import ui_story

        keys = set(ui_story.STORY_UI_KEYS)
        for lang in engine.SUPPORTED_LANGUAGES:
            labels = engine._STORY_UI_TRANSLATIONS[lang]
            missing = sorted(keys - set(labels))
            self.assertFalse(missing, f'{lang} missing {missing}')
            for key in keys:
                self.assertTrue(labels[key], f'{lang}.{key} empty')

    def test_quick_nav_keys_for_all_languages(self):
        keys = (
            'quick_nav_title', 'poi_objective', 'poi_home', 'poi_gunshop',
            'poi_garage', 'poi_clear', 'poi_close', 'poi_hint',
        )
        for lang in engine.SUPPORTED_LANGUAGES:
            labels = engine._STORY_UI_TRANSLATIONS[lang]
            for key in keys:
                self.assertTrue(labels.get(key), f'{lang}.{key} missing')

    def test_keys_work_with_cyrillic_layout(self):
        scancode_k = getattr(pygame, 'KSCAN_K', None)
        scancode_j = getattr(pygame, 'KSCAN_J', None)
        if scancode_k is None or scancode_j is None:
            self.skipTest('physical scancodes unavailable in this pygame build')
        # On a Cyrillic layout the physical K/J keys report "л"/"г" as unicode.
        event_k = pygame.event.Event(pygame.KEYDOWN, key=ord('л'), scancode=scancode_k, unicode='л')
        event_j = pygame.event.Event(pygame.KEYDOWN, key=ord('г'), scancode=scancode_j, unicode='г')
        self.assertTrue(engine.KeyboardState.matches(event_k, pygame.K_k))
        self.assertTrue(engine.KeyboardState.matches(event_j, pygame.K_j))

    def test_rebindable_nav_and_journal_defaults(self):
        import inspect

        source = inspect.getsource(engine._controls_settings_menu)
        self.assertIn('"quick_nav": pygame.K_k', source)
        self.assertIn('"journal": pygame.K_j', source)

    def test_quick_location_entries(self):
        entries = engine._quick_location_entries(
            house_pos=(1, 2), gunshop_pos=(3, 4), garage_pos=(5, 6)
        )
        self.assertEqual(
            [entry[0] for entry in entries],
            ['home', 'gunshop', 'garage', 'clear', 'close'],
        )
        self.assertEqual(entries[0][1], (1.0, 2.0))

    def test_quick_location_entries_include_story_objective(self):
        class _Primary:
            id = 'obj1'
            target_position = (10.0, 20.0)

        class _Tracker:
            def primary_objective(self):
                return _Primary()

        class _Runtime:
            tracker_state = _Tracker()

        entries = engine._quick_location_entries(story_runtime=_Runtime())
        self.assertEqual(entries[0][0], 'objective')
        self.assertEqual(entries[0][1], (10.0, 20.0))

    def test_quick_locations_menu_closes_on_escape(self):
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 24)
        settings = {'lang_idx': 0}
        translations = {
            lang: dict(engine._STORY_UI_TRANSLATIONS[lang])
            for lang in engine.SUPPORTED_LANGUAGES
        }
        gps = engine.GPS()
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        with patch('pygame.event.get', side_effect=[[event]]):
            result = engine.quick_locations_menu(
                screen, font, font, settings, translations,
                engine.SUPPORTED_LANGUAGES, gps,
                house_pos=(1, 2), gunshop_pos=(3, 4), garage_pos=(5, 6),
            )
        self.assertEqual(result, 'BACK')
