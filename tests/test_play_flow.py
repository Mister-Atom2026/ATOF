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

    def test_continue_story_loads_saved_chapter(self):
        chapter = engine.get_available_chapters()[0]
        with (
            patch.object(main, "show_selection_menu", return_value=0),
            patch.object(main.engine, "load_game_save", return_value={"chapter_id": "ch1"}),
            patch.object(main, "launch_chapter", return_value=True) as launch,
        ):
            self.assertTrue(main.start_play_flow())

        launch.assert_called_once_with(chapter, continue_story=True)

    def test_choose_chapter_starts_a_fresh_run_and_shows_number_and_title(self):
        chapter = engine.get_available_chapters()[0]
        with (
            patch.object(main, "show_selection_menu", side_effect=(1, 0)) as menu,
            patch.object(main, "launch_chapter", return_value=True) as launch,
        ):
            self.assertTrue(main.start_play_flow())

        self.assertEqual(menu.call_args_list[1].args[1], ["1. Driver Inferno"])
        launch.assert_called_once_with(chapter, continue_story=False)

    def test_continue_without_save_starts_first_available_chapter_fresh(self):
        chapter = engine.get_available_chapters()[0]
        with (
            patch.object(main, "show_selection_menu", return_value=0),
            patch.object(main.engine, "load_game_save", return_value=None),
            patch.object(main, "launch_chapter", return_value=True) as launch,
        ):
            self.assertTrue(main.start_play_flow())

        launch.assert_called_once_with(chapter, continue_story=False)

    def test_back_from_chapter_picker_returns_to_play_choices(self):
        with patch.object(
            main,
            "show_selection_menu",
            side_effect=(1, "BACK", "BACK"),
        ) as menu:
            self.assertTrue(main.start_play_flow())

        self.assertEqual(menu.call_count, 3)


if __name__ == "__main__":
    unittest.main()
