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

    def test_player_health_is_clamped_at_zero(self):
        player = engine.Player(10, 20)

        player.take_damage(35)
        self.assertEqual(player.health, 65)
        player.take_damage(100)
        self.assertEqual(player.health, 0)

    def test_wanted_level_cools_off_and_can_be_cleared(self):
        wanted = engine.WantedLevel()

        wanted.raise_level(2)
        self.assertEqual(wanted.level, 2)
        timer = wanted.escape_timer
        wanted.update(120, nearby_police=True)
        self.assertEqual(wanted.escape_timer, timer)
        wanted.update(timer)
        self.assertEqual(wanted.level, 1)
        wanted.clear()
        self.assertEqual(wanted.level, 0)

    def test_weapon_wheel_selects_with_middle_mouse_and_releases(self):
        weapons = engine.WeaponWheel()
        screen_size = (800, 600)

        weapons.process_event(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                button=2,
                pos=(500, 300),
            ),
            screen_size,
        )
        self.assertTrue(weapons.wheel_open)
        self.assertEqual(weapons.selected, "pistol")

        weapons.process_event(
            pygame.event.Event(
                pygame.MOUSEMOTION,
                pos=(400, 400),
                rel=(-100, 100),
                buttons=(False, False, True),
            ),
            screen_size,
        )
        self.assertEqual(weapons.selected, "knife")

        weapons.process_event(
            pygame.event.Event(
                pygame.MOUSEBUTTONUP,
                button=2,
                pos=(400, 400),
            ),
            screen_size,
        )
        self.assertFalse(weapons.wheel_open)

    def test_weapon_wheel_fires_pistol_and_spread_shotgun(self):
        weapons = engine.WeaponWheel(ammo=2, reserve_ammo=5, selected="pistol")

        pistol_shots = weapons.fire((0, 0), (100, 0))
        self.assertEqual(len(pistol_shots), 1)
        self.assertEqual(weapons.ammo, 1)

        weapons.selected = "shotgun"
        shotgun_pellets = weapons.fire((0, 0), (100, 0))
        self.assertEqual(len(shotgun_pellets), 5)
        self.assertEqual(weapons.ammo, 0)
        self.assertEqual(weapons.reload(), 5)
        self.assertEqual(weapons.ammo, 5)
        self.assertEqual(weapons.reserve_ammo, 0)

    def test_unarmed_selection_does_not_consume_ammo(self):
        weapons = engine.WeaponWheel(ammo=3, selected="none")

        self.assertEqual(weapons.fire((0, 0), (100, 0)), [])
        self.assertEqual(weapons.ammo, 3)

    def test_honor_and_respect_are_bounded(self):
        reputation = engine.HonorAndRespect(95, -95)

        reputation.change(honor=20, respect=-20)

        self.assertEqual(reputation.honor, 100)
        self.assertEqual(reputation.respect, -100)

    def test_projectile_stops_at_collision_mask_walls(self):
        mask = pygame.Surface((40, 20))
        mask.fill((255, 255, 255))
        mask.set_at((20, 10), (0, 0, 0))

        self.assertTrue(engine.projectile_hits_wall((10, 10), (30, 10), mask))
        self.assertFalse(engine.projectile_hits_wall((10, 5), (30, 5), mask))

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
                ["Load Save", "Choose Chapter"],
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

    def test_save_normalization_includes_health_ammo_and_honor(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "savegame.json"
            with patch.object(settings_manager, "GAME_SAVE_PATH", save_path):
                save_path.write_text(
                    '{"player":{"x":1,"y":2},"car":{"x":3,"y":4},'
                    '"hero_health":130,"ammo":20,"reserve_ammo":50,'
                    '"honor":-120,"respect":120,"wanted_level":7}',
                    encoding="utf-8",
                )
                saved = settings_manager.load_game_save()

        self.assertEqual(saved["hero_health"], 100)
        self.assertEqual(saved["ammo"], 12)
        self.assertEqual(saved["reserve_ammo"], 50)
        self.assertEqual(saved["honor"], -100)
        self.assertEqual(saved["respect"], 100)
        self.assertEqual(saved["wanted_level"], 5)

    def test_statistics_persist_honor_and_respect(self):
        with tempfile.TemporaryDirectory() as directory:
            statistics_path = Path(directory) / "statistics.json"
            with patch.object(settings_manager, "STATISTICS_PATH", statistics_path):
                settings_manager.save_statistics({"honor": -30, "respect": 45})
                statistics = settings_manager.load_statistics()

        self.assertEqual(statistics["honor"], -30)
        self.assertEqual(statistics["respect"], 45)


if __name__ == "__main__":
    unittest.main()
