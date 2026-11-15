
import importlib
import unittest
import constants as _constants


class ConstantsTests(unittest.TestCase):
    def setUp(self):
        self.constants = importlib.reload(_constants)

    def test_display_and_world_dimensions(self):
        c = self.constants
        self.assertIsInstance(c.WIDTH, int)
        self.assertIsInstance(c.HEIGHT, int)
        self.assertGreater(c.WIDTH, 0)
        self.assertGreater(c.HEIGHT, 0)
        self.assertEqual(c.WORLD_WIDTH, 1280 * 4)
        self.assertEqual(c.WORLD_HEIGHT, 720 * 4)
        self.assertGreater(c.FPS, 0)

    def test_map_paths_and_colors(self):
        c = self.constants
        self.assertTrue(c.MAP_MINI.endswith('.png'))
        self.assertTrue(c.MAP_COLLISION.endswith('.png'))
        self.assertEqual(c.C_WALL, (136, 0, 21))
        self.assertEqual(c.C_ROAD, (255, 242, 0))
        self.assertEqual(c.C_DIRT, (185, 122, 87))

    def test_house_and_garage_constants(self):
        c = self.constants
        self.assertEqual(c.HOUSE_SLEEP_SPOT, (147, 156))
        self.assertEqual(c.HOUSE_SLEEP_RADIUS, 24)
        self.assertEqual(c.HOUSE_ENTRY_SPOT, (300, 70))
        self.assertEqual(c.GARAGE_POS, (7991, 2338))
        self.assertEqual(c.GARAGE_RADIUS, 100)

    def test_traffic_constants(self):
        c = self.constants
        self.assertEqual(c.NPC_TRAFFIC_LIMIT, 22)
        self.assertGreater(c.NPC_RESPAWN_SECONDS, 0)
