"""Tests for the NPC traffic vehicle physics in :mod:`traffic`.

The tests run head-less with the dummy SDL drivers and use a synthetic, all
white collision map so only the behaviour under test influences the cars.
"""

import math
import os
import random
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import traffic


class TrafficPhysicsTests(unittest.TestCase):
    def setUp(self):
        random.seed(1234)
        traffic.set_weather_grip(1.0)
        self._saved_nodes = dict(traffic.TRAFFIC_NODES)
        traffic.TRAFFIC_NODES['TEST'] = {'pos': (3900, 2000), 'next': ['TEST']}

        self.clear_mask = pygame.Surface((4000, 4000))
        self.clear_mask.fill((255, 255, 255))
        traffic.prepare_collision_mask(self.clear_mask)

    def tearDown(self):
        traffic.TRAFFIC_NODES.clear()
        traffic.TRAFFIC_NODES.update(self._saved_nodes)
        traffic.set_weather_grip(1.0)

    # -- helpers ------------------------------------------------------------

    def _make_car(self, pos=(2000, 2000), angle=180, node_pos=(3900, 2000),
                  police=False, max_kmh=50.0):
        traffic.TRAFFIC_NODES['TEST']['pos'] = node_pos
        cls = traffic.PoliceTrafficCar if police else traffic.TrafficCar
        car = cls('TEST', 1)
        car.pos = pygame.Vector2(pos)
        car.angle = angle
        car.target_node = 'TEST'
        car.max_speed = traffic._kmh_to_speed(max_kmh)
        car.current_speed = 0.0
        car.speed = 0.0
        car.image = (traffic.get_rotated_police_resources(angle) if police
                     else traffic.get_rotated_resources(angle))
        return car

    # -- API compatibility --------------------------------------------------

    def test_public_api_still_available(self):
        for name in ('TrafficCar', 'PoliceTrafficCar', 'can_move_to',
                     'init_traffic', 'prepare_collision_mask', 'respond_to_horn',
                     'analyze_traffic_jams', 'get_rotated_resources',
                     'get_rotated_police_resources', 'configure_audio'):
            self.assertTrue(hasattr(traffic, name), name)
        car = self._make_car()
        # Old positional call shape must still work, as must the new optional
        # grip keyword used by weather-aware callers.
        car.update(self.clear_mask, None, [], 'RED', 1.0)
        car.update(self.clear_mask, None, [], 'RED', 1.0, weather_grip=0.5)
        self.assertTrue(math.isfinite(car.pos.x) and math.isfinite(car.pos.y))

    def test_realistic_speed_limits(self):
        cars = [traffic.TrafficCar('A', i) for i in range(12)]
        speeds_kmh = [traffic._speed_to_kmh(c.max_speed) for c in cars]
        for value in speeds_kmh:
            self.assertGreaterEqual(value, 40.0)
            self.assertLessEqual(value, 60.0)
        police = [traffic.PoliceTrafficCar('A', i) for i in range(12)]
        police_kmh = [traffic._speed_to_kmh(c.max_speed) for c in police]
        for value in police_kmh:
            self.assertGreaterEqual(value, 65.0)
            self.assertLessEqual(value, 100.0)
        self.assertGreater(sum(police_kmh) / len(police_kmh),
                           sum(speeds_kmh) / len(speeds_kmh))

    # -- acceleration / braking / steering ---------------------------------

    def test_accelerates_smoothly_and_respects_speed_limit(self):
        car = self._make_car()
        car.update(self.clear_mask, None, [], 'RED', 1.0)
        self.assertGreater(car.current_speed, 0.0)
        self.assertLess(car.current_speed, car.max_speed * 0.5)
        self.assertEqual(car.current_speed, car.speed)
        for _ in range(90):
            car.update(self.clear_mask, None, [], 'RED', 1.0)
        self.assertGreaterEqual(car.current_speed, car.max_speed * 0.85)
        self.assertLessEqual(car.current_speed, car.max_speed + 1e-9)
        self.assertGreater(car.pos.x, 2100.0)

    def test_brakes_for_vehicle_ahead_without_overlapping(self):
        car = self._make_car()
        other = self._make_car(pos=(2130, 2000))
        for _ in range(25):
            car.update(self.clear_mask, None, [other], 'RED', 1.0)
        self.assertLess(car.current_speed, car.max_speed * 0.6)
        self.assertGreater(car.pos.x, 2000.0)
        self.assertLess(car.pos.x, other.pos.x)
        self.assertTrue(traffic.can_move_to(other, other.pos, [car], self.clear_mask))
        self.assertFalse(car.just_hit)

    def test_steers_and_slows_before_a_turn(self):
        car = self._make_car(node_pos=(2000, 2400))
        speeds = []
        for _ in range(30):
            car.update(self.clear_mask, None, [], 'RED', 1.0)
            speeds.append(car.current_speed)
        self.assertGreater(car.angle, 240.0)
        self.assertLess(min(speeds[10:]), car.max_speed * 0.6)
        self.assertGreater(car.pos.y, 2005.0)

    def test_frame_scale_keeps_acceleration_consistent(self):
        single = self._make_car()
        double = self._make_car()
        for _ in range(40):
            single.update(self.clear_mask, None, [], 'RED', 1.0)
        for _ in range(20):
            double.update(self.clear_mask, None, [], 'RED', 2.0)
        self.assertAlmostEqual(single.current_speed, double.current_speed, delta=0.6)

    # -- masks and collision reaction ---------------------------------------

    def test_can_move_to_allows_clear_road_and_blocks_wall(self):
        car = self._make_car()
        self.assertTrue(traffic.can_move_to(car, pygame.Vector2(2100, 2000),
                                            [], self.clear_mask))
        wall = pygame.Surface((4000, 4000))
        wall.fill((255, 255, 255))
        pygame.draw.rect(wall, (0, 0, 0), pygame.Rect(2100, 1900, 80, 200))
        traffic.prepare_collision_mask(wall)
        self.assertFalse(traffic.can_move_to(car, pygame.Vector2(2200, 2000),
                                             [], wall))

    def test_reaction_sets_recoil_and_reverses_speed(self):
        car = self._make_car()
        car.current_speed = 4.0
        car.register_collision(impact_speed=4.0, frame_scale=1.0)
        self.assertTrue(car.just_hit)
        self.assertGreater(car.collision_recoil, 0.0)
        self.assertLess(car.current_speed, 0.0)
        self.assertEqual(car.current_speed, car.speed)

    def test_full_wall_stops_car_without_crossing(self):
        wall = pygame.Surface((4000, 4000))
        wall.fill((255, 255, 255))
        pygame.draw.rect(wall, (0, 0, 0), pygame.Rect(2150, 1850, 60, 300))
        traffic.prepare_collision_mask(wall)
        car = self._make_car()
        speeds = []
        for _ in range(120):
            car.update(wall, None, [], 'RED', 1.0)
            speeds.append(car.current_speed)
        # The centre must stay in front of the wall; the silhouette test
        # tolerates a thin overlap (painted lane dashes), but never lets the
        # car drive through the solid part.
        self.assertLess(car.pos.x, 2140.0)
        self.assertFalse(traffic.can_move_to(car, pygame.Vector2(2200, 2000), [], wall))
        self.assertEqual(car.current_speed, 0.0)
        self.assertLess(min(speeds), car.max_speed * 0.5)
        # A stuck car must not slowly rotate away from its route.
        self.assertLess(abs(traffic._angle_delta(car.angle, 180.0)), 20.0)

    def test_partial_wall_is_rounded_and_speed_recovers(self):
        wall = pygame.Surface((4000, 4000))
        wall.fill((255, 255, 255))
        pygame.draw.rect(wall, (0, 0, 0), pygame.Rect(2150, 1850, 60, 140))
        traffic.prepare_collision_mask(wall)
        car = self._make_car()
        for _ in range(130):
            car.update(wall, None, [], 'RED', 1.0)
        self.assertGreater(car.pos.x, 2250.0)
        self.assertGreater(car.current_speed, car.max_speed * 0.7)

    # -- slippery road ------------------------------------------------------

    def test_low_grip_slows_acceleration_and_steering(self):
        dry = self._make_car()
        wet = self._make_car()
        for _ in range(12):
            dry.update(self.clear_mask, None, [], 'RED', 1.0, weather_grip=1.0)
            wet.update(self.clear_mask, None, [], 'RED', 1.0, weather_grip=0.5)
        self.assertGreater(dry.current_speed, wet.current_speed)
        self.assertGreater(traffic._effective_turn_rate(dry, 1.0),
                           traffic._effective_turn_rate(wet, 0.5))
        self.assertGreater(traffic._lookahead_distance(wet.current_speed, 0.5),
                           traffic._lookahead_distance(dry.current_speed, 1.0))
        self.assertTrue(math.isfinite(wet.current_speed))

    def test_weather_grip_api_and_mapping_state(self):
        traffic.set_weather_grip(0.4)
        self.assertAlmostEqual(traffic.get_weather_grip(), 0.4)
        traffic.set_weather_grip(-3)
        self.assertEqual(traffic.get_weather_grip(), traffic.MIN_GRIP)
        traffic.set_weather_grip(5)
        self.assertEqual(traffic.get_weather_grip(), 1.0)
        traffic.set_weather_grip(1.0)

        normal = self._make_car()
        rainy = self._make_car()
        for _ in range(12):
            normal.update(self.clear_mask, None, [], 'RED', 1.0)
            rainy.update(self.clear_mask, None, [], {'weather_grip': 0.35}, 1.0)
        self.assertGreater(normal.current_speed, rainy.current_speed)

    # -- police -------------------------------------------------------------

    def test_police_chase_accelerates_and_apprehends(self):
        patrol = traffic.PoliceTrafficCar('TEST', 2)
        patrol.pos = pygame.Vector2(2000, 2000)
        patrol.angle = 180
        patrol.target_node = 'TEST'
        patrol.image = traffic.get_rotated_police_resources(patrol.angle)
        target = self._make_car(pos=(2140, 2000))

        speeds = []
        for _ in range(120):
            patrol.update(self.clear_mask, None, [target], 'RED', 1.0)
            speeds.append(patrol.current_speed)
            if target.is_stopped_by_police:
                break
        self.assertEqual(patrol.state, 'patrol')
        self.assertTrue(target.is_stopped_by_police)
        self.assertGreater(max(speeds), 0.0)
        self.assertLessEqual(max(speeds), patrol.max_speed + 1e-9)
        self.assertEqual(patrol.current_speed, patrol.speed)


if __name__ == '__main__':
    unittest.main()
