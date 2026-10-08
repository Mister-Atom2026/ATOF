import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1, 1))

import engine
import settings_manager


class EngineRuntimeTests(unittest.TestCase):
    def test_camera_follow_and_coordinate_conversion(self):
        camera = engine.Camera2D((100, 80), (500, 400))

        self.assertEqual(camera.follow((250, 200)), (-200, -160))
        self.assertEqual(camera.world_to_screen((250, 200)), pygame.Vector2(50, 40))
        self.assertEqual(camera.screen_to_world((50, 40)), pygame.Vector2(250, 200))

    def test_camera_clamps_to_world_edges(self):
        camera = engine.Camera2D((100, 80), (500, 400))

        self.assertEqual(camera.follow((0, 0)), (0, 0))
        self.assertEqual(camera.follow((500, 400)), (-400, -320))

    def test_scene_transition_runs_exit_before_enter(self):
        calls = []
        scenes = engine.SceneManager("HOUSE")
        scenes.register("HOUSE", on_exit=lambda next_scene, _: calls.append(("exit", next_scene)))
        scenes.register("CITY", on_enter=lambda previous, _: calls.append(("enter", previous)))

        self.assertTrue(scenes.transition("CITY"))
        self.assertFalse(scenes.transition("CITY"))
        self.assertEqual(scenes.current, "CITY")
        self.assertEqual(scenes.previous, "HOUSE")
        self.assertEqual(calls, [("exit", "CITY"), ("enter", "HOUSE")])

    def test_scene_transition_rejects_unregistered_scene(self):
        scenes = engine.SceneManager("HOUSE")

        with self.assertRaises(KeyError):
            scenes.transition("CITY")
        self.assertEqual(scenes.current, "HOUSE")

    def test_renderer_executes_callbacks_by_layer(self):
        calls = []
        renderer = engine.LayeredRenderer()
        renderer.submit(engine.RenderLayer.UI, lambda: calls.append("ui"))
        renderer.submit(engine.RenderLayer.BACKGROUND, lambda: calls.append("background"))
        renderer.submit(engine.RenderLayer.WORLD, lambda: calls.append("world"))

        renderer.render()

        self.assertEqual(calls, ["background", "world", "ui"])

    def test_frame_clock_bounds_elapsed_step(self):
        clock = pygame.time.Clock()
        frame_clock = engine.FrameClock()
        with patch("engine.time.perf_counter", side_effect=(10.0, 10.0001, 11.0)):
            frame_clock.reset()
            self.assertEqual(frame_clock.tick(clock, 0), 0.05)
            self.assertEqual(frame_clock.tick(clock, 0), 3.0)

    def test_legacy_modules_reexport_engine_types(self):
        from house import HousePlayer
        from navigator import GPS

        self.assertIs(HousePlayer, engine.HousePlayer)
        self.assertIs(GPS, engine.GPS)

    def test_chapter_registry_exposes_number_and_title(self):
        chapters = engine.get_available_chapters()

        self.assertEqual(
            [(chapter.number, chapter.title) for chapter in chapters],
            [(1, "Driver Inferno")],
        )

    def test_engine_loads_registered_chapter_module(self):
        chapter = engine.load_chapter("ch1")

        self.assertTrue(callable(chapter.run))

    def test_engine_rejects_unknown_chapter_ids(self):
        with self.assertRaises(KeyError):
            engine.load_chapter("missing")

    def test_selection_menu_returns_selected_option(self):
        screen = pygame.display.set_mode((800, 600))
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)

        with patch("pygame.event.get", return_value=[event]):
            result, returned_screen = engine.selection_menu(
                screen,
                "Play",
                ["Continue Story", "Choose Chapter"],
                pygame.font.SysFont(None, 32),
                pygame.font.SysFont(None, 24),
                "Back",
                {},
            )

        self.assertEqual(result, 0)
        self.assertIs(returned_screen, screen)

    def test_game_save_keeps_chapter_identifier_and_supports_old_saves(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "savegame.json"
            with patch.object(settings_manager, "GAME_SAVE_PATH", save_path):
                settings_manager.save_game_save({
                    "chapter_id": "chapter-2",
                    "game_state": "CITY",
                    "player": {"x": 1, "y": 2},
                    "car": {"x": 3, "y": 4},
                })
                self.assertEqual(settings_manager.load_game_save()["chapter_id"], "chapter-2")

                save_path.write_text(
                    '{"game_state":"CITY","player":{"x":1,"y":2},"car":{"x":3,"y":4}}',
                    encoding="utf-8",
                )
                self.assertEqual(settings_manager.load_game_save()["chapter_id"], "ch1")


if __name__ == "__main__":
    unittest.main()
