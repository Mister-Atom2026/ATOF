
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import vehicle_preservation as vp


def car(x, y, *, alive=True, police=False, arrested=False, death_timer=0.0):
    return SimpleNamespace(
        pos=pygame.Vector2(x, y),
        is_alive=alive,
        is_police=police,
        is_arrested=arrested,
        death_timer=death_timer,
    )


class AliveAndHijackableTests(unittest.TestCase):
    def test_missing_is_alive_defaults_to_alive(self):
        self.assertTrue(vp.is_car_alive(SimpleNamespace(pos=(0, 0))))
        self.assertFalse(vp.is_car_alive(None))

    def test_dead_car_is_not_alive(self):
        self.assertFalse(vp.is_car_alive(car(0, 0, alive=False)))

    def test_hijackable_requires_alive_and_not_arrested(self):
        self.assertTrue(vp.is_hijackable(car(0, 0)))
        self.assertFalse(vp.is_hijackable(car(0, 0, alive=False)))
        self.assertFalse(vp.is_hijackable(car(0, 0, arrested=True)))
        self.assertTrue(vp.is_hijackable(car(0, 0, police=True)))


class PreservePreviousCarTests(unittest.TestCase):
    def test_parks_normal_car(self):
        parked = []
        previous = car(10, 20)
        self.assertTrue(vp.preserve_previous_car(previous, parked))
        self.assertEqual(len(parked), 1)
        self.assertIs(parked[0], previous)

    def test_parks_police_car_by_default(self):
        # Regression: stolen police cars used to be dropped during hijack.
        parked = []
        previous = car(10, 20, police=True)
        self.assertTrue(vp.preserve_previous_car(previous, parked))
        self.assertIs(parked[0], previous)

    def test_can_opt_out_of_parking_police(self):
        parked = []
        previous = car(10, 20, police=True)
        self.assertFalse(vp.preserve_previous_car(previous, parked, include_police=False))
        self.assertEqual(parked, [])

    def test_none_is_never_parked(self):
        parked = []
        self.assertFalse(vp.preserve_previous_car(None, parked))
        self.assertEqual(parked, [])

    def test_does_not_duplicate_an_already_parked_car(self):
        previous = car(10, 20)
        parked = [car(0, 0), previous]
        self.assertFalse(vp.preserve_previous_car(previous, parked))
        self.assertEqual(len(parked), 2)

    def test_identity_not_equality(self):
        # Two distinct but value-equal objects must both be kept.
        first = car(10, 20)
        second = car(10, 20)
        parked = [first]
        self.assertTrue(vp.preserve_previous_car(second, parked))
        self.assertEqual(len(parked), 2)


class NearbyCarsTests(unittest.TestCase):
    def test_default_radius_is_100(self):
        self.assertEqual(vp.DEFAULT_NEARBY_RADIUS, 100.0)

    def test_filters_by_radius_inclusive(self):
        center = car(0, 0)
        inside = car(0, 99)
        boundary = car(100, 0)
        outside = car(101, 0)
        result = vp.filter_nearby_cars([center, inside, boundary, outside], center.pos)
        self.assertIn(inside, result)
        self.assertIn(boundary, result)
        self.assertNotIn(outside, result)
        # The centre is at distance 0 (<= radius) and is included unless excluded.
        self.assertIn(center, result)

    def test_exclude_parameter(self):
        source = car(0, 0)
        other = car(10, 0)
        result = vp.filter_nearby_cars([source, other], source.pos, exclude=source)
        self.assertNotIn(source, result)
        self.assertIn(other, result)

    def test_dead_cars_skipped_by_default(self):
        alive = car(10, 0)
        wreck = car(20, 0, alive=False)
        result = vp.filter_nearby_cars([alive, wreck], (0, 0))
        self.assertEqual(result, [alive])
        with_dead = vp.filter_nearby_cars([alive, wreck], (0, 0), include_dead=True)
        self.assertEqual(len(with_dead), 2)

    def test_accepts_tuple_and_vector_positions(self):
        target = car(50, 50)
        self.assertIn(target, vp.filter_nearby_cars([target], (0, 0), radius=100))
        self.assertIn(target, vp.filter_nearby_cars([target], pygame.Vector2(0, 0)))

    def test_invalid_position_returns_empty(self):
        self.assertEqual(vp.filter_nearby_cars([car(0, 0)], None), [])
        self.assertEqual(vp.filter_nearby_cars([car(0, 0)], (0, 0), radius=-1), [])

    def test_nearest_car(self):
        close = car(20, 0)
        farther = car(60, 0)
        outside = car(500, 0)
        found = vp.nearest_car([farther, outside, close], (0, 0))
        self.assertIs(found, close)
        self.assertIsNone(vp.nearest_car([outside], (0, 0)))
        self.assertIsNone(vp.nearest_car([], (0, 0)))

    def test_is_spawn_crowded(self):
        self.assertTrue(vp.is_spawn_crowded((0, 0), [car(30, 0)]))
        self.assertFalse(vp.is_spawn_crowded((0, 0), [car(300, 0)]))
        self.assertFalse(vp.is_spawn_crowded((0, 0), [car(30, 0, alive=False)]))


class AliveOrFadingTests(unittest.TestCase):
    def test_keeps_live_and_fading_wrecks(self):
        live = car(0, 0)
        fading = car(10, 0, alive=False, death_timer=120)
        gone = car(20, 0, alive=False, death_timer=0)
        kept = vp.alive_or_fading([live, fading, gone, None])
        self.assertEqual(kept, [live, fading])

    def test_death_timer_from_traffic_take_damage(self):
        import traffic

        npc = traffic.TrafficCar('A', 999)
        self.assertTrue(npc.is_alive)
        npc.take_damage(npc.health + 1)
        self.assertFalse(npc.is_alive)
        self.assertGreater(npc.death_timer, 0)
        # A freshly destroyed NPC must survive the respawn sweep (still fading).
        self.assertIn(npc, vp.alive_or_fading([npc]))
        # After the death clock runs out it no longer needs preserving.
        npc.death_timer = 0.0
        self.assertNotIn(npc, vp.alive_or_fading([npc]))


if __name__ == '__main__':
    unittest.main()
