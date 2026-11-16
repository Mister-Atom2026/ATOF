"""Regression tests for wanted level, fines and bribes."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import engine
import settings_manager
import wanted_system


class WantedStateMechanicsTests(unittest.TestCase):
    def test_fines_are_clamped_and_accumulate(self):
        state = wanted_system.WantedState()
        self.assertEqual(state.add_fine(-50), 0)
        self.assertEqual(state.add_fine(300, "theft"), 300)
        self.assertEqual(state.add_fine(200, "damage"), 200)
        self.assertEqual(state.fines, 500)
        self.assertEqual(state.total_fine, 500)
        self.assertEqual(state.fine_reasons, ["theft", "damage"])

        state.add_fine(10 ** 9)
        self.assertEqual(state.fines, wanted_system.MAX_FINE)

    def test_raise_level_can_issue_a_fine(self):
        state = wanted_system.WantedState()
        self.assertEqual(state.raise_level(2, fine=800, reason="theft"), 2)
        self.assertEqual(state.level, 2)
        self.assertEqual(state.fines, 800)
        self.assertGreater(state.escape_timer, 0)
        # Non-positive amounts still bump the level by at least one.
        self.assertEqual(state.raise_level(0), 3)

    def test_bribe_cost_includes_stars_and_fines(self):
        state = wanted_system.WantedState(level=2, fines=500)
        self.assertEqual(state.bribe_cost(), 2 * 400 + 500)
        self.assertEqual(wanted_system.WantedState().bribe_cost(), 0)

    def test_bribe_reduces_level_and_clears_fines(self):
        state = wanted_system.WantedState(level=3, fines=600)
        cost = state.bribe_cost()
        paid, amount = state.bribe(cost - 1)
        self.assertFalse(paid)
        self.assertEqual(amount, 0)
        self.assertEqual((state.level, state.fines), (3, 600))

        paid, amount = state.bribe(cost)
        self.assertTrue(paid)
        self.assertEqual(amount, cost)
        self.assertEqual(state.level, 2)
        self.assertEqual(state.fines, 0)
        self.assertEqual(state.fine_reasons, [])
        self.assertGreater(state.escape_timer, 0)

    def test_bribe_from_zero_level_only_pays_the_fine(self):
        state = wanted_system.WantedState(level=0, fines=250)
        paid, amount = state.bribe(250)
        self.assertTrue(paid)
        self.assertEqual(amount, 250)
        self.assertEqual(state.level, 0)
        self.assertEqual(state.fines, 0)

    def test_pay_fine_keeps_wanted_level(self):
        state = wanted_system.WantedState(level=4, fines=700)
        paid, amount = state.pay_fine(699)
        self.assertFalse(paid)
        self.assertEqual(amount, 0)
        self.assertEqual(state.fines, 700)

        paid, amount = state.pay_fine(700)
        self.assertTrue(paid)
        self.assertEqual(amount, 700)
        self.assertEqual(state.level, 4)
        self.assertEqual(state.fines, 0)

    def test_fines_survive_cooling_off_but_clear_on_reset(self):
        state = wanted_system.WantedState(level=1, fines=400)
        timer = state.escape_timer
        state.update(timer)
        self.assertEqual(state.level, 0)
        self.assertEqual(state.fines, 400)

        state.clear()
        self.assertEqual(state.level, 0)
        self.assertEqual(state.escape_timer, 0.0)
        self.assertEqual(state.fines, 0)

    def test_nearby_police_freezes_cooling_off(self):
        state = wanted_system.WantedState(level=2)
        timer = state.escape_timer
        state.update(timer * 4, nearby_police=True)
        self.assertEqual(state.escape_timer, timer)


class EngineIntegrationTests(unittest.TestCase):
    def test_engine_wanted_level_supports_fines(self):
        wanted = engine.WantedLevel(10, 5, -3)
        self.assertIsInstance(wanted, wanted_system.WantedState)
        self.assertEqual(wanted.level, 5)
        self.assertEqual(wanted.fines, 0)

        wanted.raise_level(1, fine=900, reason="theft")
        self.assertEqual(wanted.fines, 900)
        self.assertEqual(wanted.raise_level(10), 5)

    def test_fine_is_included_in_save_data(self):
        wanted = engine.WantedLevel(2, 123.0, 950)
        # Reuse the minimal helper setup from the existing save tests.
        state = engine.build_game_state_data(
            "CITY",
            engine.Player(1, 2),
            engine.Player(3, 4),
            engine.Car(5, 6),
            engine.WeaponWheel.new_game(),
            wanted,
            engine.HonorAndRespect(),
            100, 0, 0, 480, set(), 0, 0, None,
        )
        self.assertEqual(state["wanted_fines"], 950)

        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "savegame.json"
            with patch.object(settings_manager, "GAME_SAVE_PATH", save_path):
                settings_manager.save_game_save(state)
                loaded = settings_manager.load_game_save()

        self.assertEqual(loaded["wanted_fines"], 950)
        restored = engine.WantedLevel(
            loaded["wanted_level"],
            loaded["wanted_escape_timer"],
            loaded["wanted_fines"],
        )
        self.assertEqual((restored.level, restored.fines), (2, 950))

    def test_save_normalization_clamps_fines(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "savegame.json"
            with patch.object(settings_manager, "GAME_SAVE_PATH", save_path):
                save_path.write_text(
                    '{"game_state":"CITY","player":{"x":1,"y":2},'
                    '"car":{"x":3,"y":4},"wanted_fines":999999}',
                    encoding="utf-8",
                )
                loaded = settings_manager.load_game_save()
        self.assertEqual(loaded["wanted_fines"], wanted_system.MAX_FINE)

    def test_phone_translations_have_bribe_label(self):
        for language in engine.SUPPORTED_LANGUAGES:
            self.assertIn("bribe", engine.PHONE_TRANSLATIONS[language])

    def test_draw_player_status_shows_fine_and_bribe_hint(self):
        screen = pygame.Surface((400, 420))
        engine.draw_player_status(
            screen, None, 7, 48, 2,
            {"ammo": "Ammo {current}/{reserve}", "wanted": "Wanted {stars}"},
            fine=800, bribe_cost=1600, notice="Bribe paid",
        )


if __name__ == "__main__":
    unittest.main()
