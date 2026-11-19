"""Regression coverage for mission 01 — «Пробудження»."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1, 1))

import engine
import story_mission


class StoryMissionDataTests(unittest.TestCase):
    def test_all_dialogues_have_speaker_emotion_and_text(self):
        expected_counts = {2: 15, 3: 7, 4: 9, 5: 8}
        self.assertEqual(set(story_mission.DIALOGUES), set(expected_counts))
        for stage, lines in story_mission.DIALOGUES.items():
            self.assertEqual(len(lines), expected_counts[stage], f"stage {stage}")
            for speaker, emotion, text in lines:
                self.assertIn(speaker, story_mission.NAMES)
                self.assertIn(emotion, story_mission.EMOTION_INDEX)
                self.assertTrue(text.strip())

    def test_portrait_files_exist_for_every_line(self):
        for lines in story_mission.DIALOGUES.values():
            for speaker, emotion, _text in lines:
                path = story_mission.portrait_path(speaker, emotion)
                self.assertTrue(os.path.exists(path), path)
                image = pygame.image.load(path)
                self.assertEqual(image.get_size(), (128, 128), path)

    def test_spawn_and_kitchen_are_walkable(self):
        collision = engine.load_image(story_mission.HOUSE_COLLISION)
        for x, y in (story_mission.ATOM_SPAWN, story_mission.COPPER_HOUSE,
                     story_mission.KITCHEN_HINT):
            sx, sy = int(x / story_mission.HOUSE_SCALE), int(y / story_mission.HOUSE_SCALE)
            self.assertNotEqual(collision.get_at((sx, sy))[:3], (0, 0, 0), (x, y))

    def test_city_waypoint_uses_real_walkable_map_coordinates(self):
        collision = engine.load_image("world/vyshneve_collision.png")
        for x, y in (story_mission.CITY_SPAWN, story_mission.CITY_WAYPOINT):
            sx = int(x / story_mission.WORLD_W * collision.get_width())
            sy = int(y / story_mission.WORLD_H * collision.get_height())
            red, green, blue = collision.get_at((sx, sy))[:3]
            self.assertFalse(red > 200 and green < 50 and blue < 50, (x, y))

    def test_mission_can_be_constructed(self):
        mission = story_mission.StoryMission(pygame.display.get_surface(), {})
        self.assertEqual(mission.scene, 1)
        self.assertEqual(tuple(mission.pos), story_mission.ATOM_SPAWN)
        self.assertFalse(mission.dialogue_active)


if __name__ == "__main__":
    unittest.main()
