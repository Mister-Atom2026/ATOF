
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import settings_manager as sm


class SettingsManagerTests(unittest.TestCase):
    def test_bounded_int_and_finite_number(self):
        self.assertEqual(sm._bounded_int('5', 1, 0, 10), 5)
        self.assertEqual(sm._bounded_int('bad', 3, 0, 10), 3)
        self.assertEqual(sm._bounded_int(99, 3, 0, 10), 10)
        self.assertEqual(sm._finite_number(1.5), 1.5)
        self.assertEqual(sm._finite_number(float('inf'), default=2.0), 2.0)
        self.assertEqual(sm._finite_number(True, default=2.0), 2.0)

    def test_normalize_weapon_ammo(self):
        caps = {'pistol': 7, 'shotgun': 2}
        self.assertEqual(sm._normalize_weapon_ammo({'ammo_by_weapon': {'pistol': 5, 'shotgun': 9}}, 'ammo_by_weapon', caps), {'pistol': 5, 'shotgun': 2})
        self.assertEqual(sm._normalize_weapon_ammo({}, 'ammo_by_weapon', caps), {})

    def test_normalize_garage_cars(self):
        data = {'garage_cars': [
            {'name': 'A', 'vehicle_class': 'sport', 'engine_upgrade': 2, 'wheel_upgrade': 1, 'health': 150, 'is_broken': False},
            {'vehicle_class': 'bad', 'engine_upgrade': 99, 'wheel_upgrade': -1},
            'bad',
        ]}
        cars = sm._normalize_garage_cars(data)
        self.assertIsInstance(cars, list)
        self.assertEqual(cars[0]['vehicle_class'], 'sport')
        self.assertEqual(cars[0]['engine_upgrade'], 2)
        self.assertEqual(cars[1]['vehicle_class'], 'sport')
        self.assertEqual(cars[1]['engine_upgrade'], 5)
        self.assertEqual(cars[1]['wheel_upgrade'], 0)
        self.assertIsNone(sm._normalize_garage_cars({}))

    def test_normalize_statistics(self):
        stats = sm._normalize_statistics({'money': 10, 'max_speed_kmh': 123.4, 'time': '01:02', 'honor': 999})
        self.assertEqual(stats['money'], 10)
        self.assertEqual(stats['max_speed_kmh'], 123.4)
        self.assertEqual(stats['honor'], sm._HONOR_MAX)
        self.assertIn('treasures', stats)

    def test_normalize_settings_defaults_and_clamps(self):
        s = sm._normalize_settings({'music_volume': 200, 'lang_idx': -5, 'video_width': 10, 'fps_limit': 999})
        self.assertEqual(s['music_volume'], 100)
        self.assertEqual(s['lang_idx'], 0)
        self.assertEqual(s['video_width'], 800)
        self.assertEqual(s['fps_limit'], 240)
        self.assertIn('keys', s)

    def test_save_and_load_settings_and_statistics(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            settings_path = base / 'settings.json'
            stats_path = base / 'stats.json'
            with patch.object(sm, 'SETTINGS_PATH', settings_path), patch.object(sm, 'STATISTICS_PATH', stats_path):
                settings = {'music_volume': 55, 'lang_idx': 1}
                sm.save_settings(settings)
                self.assertEqual(settings['music_volume'], 55)
                loaded = sm.load_settings()
                self.assertEqual(loaded['music_volume'], 55)
                sm.save_statistics({'money': 7, 'honor': 3})
                st = sm.load_statistics()
                self.assertEqual(st['money'], 7)
                self.assertEqual(st['honor'], 3)

    def test_save_slots_and_game_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            slots_dir = base / 'slots'
            slots_dir.mkdir()
            game_path = base / 'game.json'
            with patch.object(sm, 'SAVE_SLOTS_DIR', slots_dir), patch.object(sm, 'GAME_SAVE_PATH', game_path), patch.object(sm, 'SAVE_SLOT_COUNT', 5):
                state = {'money': 123, 'game_time': 600, 'game_state': 'CITY'}
                sm.save_to_slot(0, state)
                self.assertTrue(sm.get_save_slot_path(0).exists())
                loaded = sm.load_save_slot(0)
                self.assertEqual(loaded['money'], 123)
                all_slots = sm.get_all_save_slots()
                self.assertEqual(len(all_slots), 5)
                self.assertFalse(all_slots[0].get('empty'))
                self.assertTrue(all_slots[1].get('empty'))
                sm.save_game_save({
                    'money': 50,
                    'player': {'x': 1, 'y': 2, 'angle': 0},
                    'car': {'x': 3, 'y': 4, 'angle': 0},
                    'game_state': 'CITY',
                })
                self.assertTrue(game_path.exists())
                loaded_game = sm.load_game_save()
                self.assertIsNotNone(loaded_game)
                self.assertEqual(loaded_game['money'], 50)

    def test_invalid_slot_index_raises(self):
        with self.assertRaises(ValueError):
            sm.get_save_slot_path(-1)
        with self.assertRaises(ValueError):
            sm.get_save_slot_path(99)
