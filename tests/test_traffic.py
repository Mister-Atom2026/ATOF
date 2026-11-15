
import os
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import traffic
import constants


class TrafficTests(unittest.TestCase):
    def test_init_traffic_count(self):
        cars = traffic.init_traffic(5, police_chance=0.0)
        self.assertEqual(len(cars), 5)
        for car in cars:
            self.assertTrue(hasattr(car, 'pos'))
            self.assertTrue(getattr(car, 'is_alive', True))

    def test_init_traffic_can_create_police(self):
        cars = traffic.init_traffic(10, police_chance=1.0)
        self.assertTrue(any(getattr(c, 'is_police', False) for c in cars))

    def test_respond_to_horn_sets_pause_timer(self):
        cars = traffic.init_traffic(3, police_chance=0.0)
        target = cars[0]
        target.pos.update(100, 100)
        for c in cars[1:]:
            c.pos.update(10000, 10000)
        traffic.respond_to_horn(cars, pygame.Vector2(100, 100), radius=500, pause_frames=30)
        self.assertGreaterEqual(getattr(target, 'horn_pause_timer', 0), 30)

    def test_prepare_and_world_obstacle_mask(self):
        surf = pygame.Surface((10, 10))
        surf.fill((255, 255, 255))
        traffic.prepare_collision_mask(surf)
        mask = traffic._world_obstacle_mask(surf)
        self.assertIsNotNone(mask)

    def test_can_move_to_false_on_blocked_mask(self):
        col = pygame.Surface((200, 200))
        col.fill((0, 0, 0))
        traffic.prepare_collision_mask(col)
        car = traffic.init_traffic(1, police_chance=0.0)[0]
        car.pos.update(50, 50)
        self.assertFalse(traffic.can_move_to(car, pygame.Vector2(50, 50), [], col_mask=col))
