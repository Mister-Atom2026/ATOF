import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import main
import engine


class PlayFlowTests(unittest.TestCase):
    def setUp(self):
        self.previous_language = main.APP_SETTINGS["lang_idx"]
        main.APP_SETTINGS["lang_idx"] = engine.SUPPORTED_LANGUAGES.index("English")

    def tearDown(self):
        main.APP_SETTINGS["lang_idx"] = self.previous_language

    def test_saved_game_starts_the_open_world(self):
        with (
            patch.object(main.engine, "load_game_save", return_value={"money": 100}),
            patch.object(main, "launch_open_world", return_value=True) as launch,
        ):
            self.assertTrue(main.start_open_world())

        launch.assert_called_once_with(continue_game=True)

    def test_missing_save_starts_a_fresh_open_world(self):
        with (
            patch.object(main.engine, "load_game_save", return_value=None),
            patch.object(main, "launch_open_world", return_value=True) as launch,
        ):
            self.assertTrue(main.start_open_world())

        launch.assert_called_once_with(continue_game=False)

    def test_play_menu_option_opens_the_world_directly(self):
        with (
            patch.object(main, "start_open_world", return_value=True) as launch,
        ):
            self.assertTrue(main.activate_menu_option(0))

        launch.assert_called_once_with()

    def test_engine_owns_the_open_world_entrypoint(self):
        self.assertTrue(callable(engine.run_open_world))


if __name__ == "__main__":
    unittest.main()
