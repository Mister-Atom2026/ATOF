"""Regression coverage for the player vehicle's driving physics."""

import inspect
import os
import unittest
from collections import defaultdict

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1, 1))

import engine


_KEY_ATTRIBUTES = {
    "w": "K_w",
    "s": "K_s",
    "a": "K_a",
    "d": "K_d",
    "space": "K_SPACE",
}


def _keys(**active):
    """Build a key-state mapping; anything not listed is simply not pressed."""
    keys = defaultdict(bool)
    for name, value in active.items():
        keys[getattr(pygame, _KEY_ATTRIBUTES[name])] = value
    return keys


def _wall_mask(wall_rect, size=(600, 600)):
    mask = pygame.Surface(size)
    mask.fill((255, 255, 255))
    pygame.draw.rect(mask, (0, 0, 0), wall_rect)
    return mask


class CarPhysicsTests(unittest.TestCase):
    def setUp(self):
        self.idle = _keys()

    def test_public_update_api_is_unchanged(self):
        parameters = list(inspect.signature(engine.Car.update).parameters)
        self.assertEqual(
            parameters,
            [
                "self",
                "keys",
                "col_mask",
                "active",
                "npc_cars",
                "frame_scale",
                "surface_map",
                "weather_grip",
            ],
        )
        car = engine.Car(0, 0)
        self.assertEqual(car.steer_input, 0.0)
        self.assertEqual(car.motion_velocity.length(), 0.0)
        self.assertFalse(car.is_drifting)
        self.assertFalse(car.is_braking)

    def test_throttle_accelerates_up_to_max_speed(self):
        car = engine.Car(0, 0)
        for _ in range(600):
            car.update(_keys(w=True), None, True)
        self.assertGreater(car.speed, 0.0)
        self.assertLessEqual(car.speed, car.max_speed)
        self.assertGreater(car.pos.length(), 0.0)

    def test_rain_reduces_acceleration(self):
        dry = engine.Car(0, 0)
        wet = engine.Car(0, 0)
        for _ in range(60):
            dry.update(_keys(w=True), None, True, weather_grip=1.0)
            wet.update(_keys(w=True), None, True, weather_grip=0.68)
        self.assertGreater(wet.speed, 0.0)
        self.assertGreater(dry.speed, wet.speed)

    def test_brake_overrides_throttle(self):
        car = engine.Car(0, 0)
        car.speed = 5.0
        car.update(_keys(w=True, s=True), None, True)
        self.assertLess(car.speed, 5.0)
        self.assertTrue(car.is_braking)

        parked = engine.Car(0, 0)
        parked.update(_keys(w=True, s=True), None, True)
        self.assertEqual(parked.speed, 0.0)

    def test_handbrake_outbrakes_service_brake_and_throttle(self):
        handbrake = engine.Car(0, 0)
        service = engine.Car(0, 0)
        handbrake.speed = 6.0
        service.speed = 6.0
        handbrake.update(_keys(w=True, space=True), None, True)
        service.update(_keys(w=True, s=True), None, True)
        self.assertLess(handbrake.speed, service.speed)
        self.assertTrue(handbrake.is_braking)

    def test_reverse_is_capped_and_slippery_roads_slow_it(self):
        dry = engine.Car(0, 0)
        wet = engine.Car(0, 0)
        for _ in range(60):
            dry.update(_keys(s=True), None, True, weather_grip=1.0)
            wet.update(_keys(s=True), None, True, weather_grip=0.68)
        self.assertLess(dry.speed, 0.0)
        self.assertGreaterEqual(dry.speed, -dry.max_speed * 0.5 - 1e-9)
        self.assertLess(abs(wet.speed), abs(dry.speed))

    def test_steering_input_settles_gradually(self):
        car = engine.Car(0, 0)
        car.speed = 3.0
        turning = _keys(a=True)
        car.update(turning, None, True)
        first = car.steer_input
        self.assertGreater(first, 0.0)
        self.assertLess(first, 1.0)
        for _ in range(20):
            car.update(turning, None, True)
        self.assertGreater(car.steer_input, first)

        angle_before_release = car.angle
        for _ in range(3):
            car.update(self.idle, None, True)
        self.assertGreater(car.angle, angle_before_release)

    def test_high_speed_has_tighter_steering_lock_than_low_speed(self):
        slow = engine.Car(0, 0)
        fast = engine.Car(0, 0)
        turning = _keys(a=True)
        for _ in range(40):
            slow.speed = 1.0
            fast.speed = 10.0
            slow.update(turning, None, True)
            fast.update(turning, None, True)
        self.assertGreater(slow.angle, 0.0)
        self.assertGreater(fast.angle, 0.0)
        self.assertGreater(slow.angle, fast.angle)

    def test_handbrake_turn_at_speed_triggers_drift(self):
        car = engine.Car(0, 0)
        car.speed = 12.0
        car.motion_velocity = pygame.Vector2(-12.0, 0)
        seen = False
        for _ in range(10):
            car.update(_keys(w=True, a=True, space=True), None, True)
            seen = seen or car.is_drifting
        self.assertTrue(seen)

    def test_slow_cornering_is_not_a_drift(self):
        car = engine.Car(0, 0)
        car.speed = 2.0
        for _ in range(10):
            car.update(_keys(w=True, a=True), None, True)
            self.assertFalse(car.is_drifting)

    def test_rain_makes_breaking_traction_easier(self):
        results = []
        for grip in (1.0, 0.68):
            car = engine.Car(0, 0)
            car.speed = 7.0
            car.steer_input = 1.0
            car.motion_velocity = pygame.Vector2(-7.0, 0)
            car.update(_keys(w=True, a=True), None, True, weather_grip=grip)
            results.append(car.is_drifting)
        self.assertFalse(results[0])
        self.assertTrue(results[1])

    def test_low_grip_preserves_more_lateral_momentum(self):
        dry = engine.Car(0, 0)
        wet = engine.Car(0, 0)
        for car in (dry, wet):
            car.speed = 1.0
            car.motion_velocity = pygame.Vector2(-1.0, 3.0)
        dry.update(self.idle, None, True, weather_grip=1.0)
        wet.update(self.idle, None, True, weather_grip=0.3)
        self.assertGreater(abs(wet.motion_velocity.y), abs(dry.motion_velocity.y))

    def test_collision_damages_once_and_never_tunnels_through_wall(self):
        col_mask = _wall_mask((60, 140, 90, 120))
        car = engine.Car(240, 200)
        car.speed = 6.0
        car.motion_velocity = pygame.Vector2(-6.0, 0)
        hits = 0
        for _ in range(60):
            before = car.health
            car.update(_keys(w=True), col_mask, True)
            if car.health < before:
                hits += 1
        self.assertEqual(hits, 1)
        self.assertTrue(car.just_hit)
        self.assertGreater(car.pos.x, 150)
        self.assertLess(car.motion_velocity.length(), 2.0)

    def test_glancing_impact_slides_along_the_wall(self):
        # Wall occupies x in [60, 180]; the car at x=220 barely clears it.
        col_mask = _wall_mask((60, 0, 120, 600))
        car = engine.Car(220, 300)
        velocity = pygame.Vector2(-6.0, -3.0)
        car.motion_velocity = pygame.Vector2(velocity)
        car._resolve_collision(velocity, pygame.Vector2(-1, 0), None, col_mask)
        self.assertAlmostEqual(car.pos.x, 220.0)
        self.assertAlmostEqual(car.pos.y, 297.0)
        self.assertEqual(car.motion_velocity.x, 0.0)
        self.assertAlmostEqual(car.motion_velocity.y, -3.0)

    def test_zero_frame_scale_is_stable(self):
        car = engine.Car(0, 0)
        car.speed = 5.0
        car.motion_velocity = pygame.Vector2(-5.0, 0)
        position = pygame.Vector2(car.pos)
        car.update(_keys(w=True), None, True, frame_scale=0)
        self.assertEqual(car.speed, 5.0)
        self.assertEqual(car.pos, position)

    def test_broken_car_ignores_controls(self):
        car = engine.Car(0, 0)
        car.is_broken = True
        car.speed = 5.0
        car.motion_velocity = pygame.Vector2(-5.0, 0)
        car.update(_keys(w=True, a=True), None, True)
        self.assertLess(car.speed, 5.0)

    def test_braking_leaves_skid_marks(self):
        car = engine.Car(0, 0)
        car.speed = 5.0
        car.motion_velocity = pygame.Vector2(-5.0, 0)
        car.update(_keys(s=True), None, True)
        self.assertTrue(car.skid_marks)


class CollisionObstacleTests(unittest.TestCase):
    def test_parked_cars_are_solid_obstacles(self):
        current = engine.Car(0, 0)
        parked = engine.Car(200, 0)
        npc = engine.Car(400, 0)
        obstacles = engine.collision_obstacles([npc], [parked], current)
        self.assertIn(parked, obstacles)
        self.assertIn(npc, obstacles)
        self.assertNotIn(current, obstacles)

    def test_dead_and_current_cars_are_excluded(self):
        current = engine.Car(0, 0)
        dead = engine.Car(100, 0)
        dead.is_alive = False
        parked = engine.Car(200, 0)
        obstacles = engine.collision_obstacles([dead], [current, parked], current)
        self.assertEqual(obstacles, [parked])


if __name__ == "__main__":
    unittest.main()
