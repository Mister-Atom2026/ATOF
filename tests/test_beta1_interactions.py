import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1, 1))

import engine
import traffic


class BetaOneInteractionTests(unittest.TestCase):
    @staticmethod
    def make_vehicle(image, position, angle=0):
        return SimpleNamespace(
            pos=pygame.Vector2(position),
            image=image,
            angle=angle,
            vehicle_class="test-vehicle",
            is_alive=True,
        )

    @staticmethod
    def clear_collision_map(size=(100, 100)):
        surface = pygame.Surface(size).convert()
        surface.fill((127, 127, 127))
        return surface

    @staticmethod
    def car_texture():
        texture = pygame.Surface((20, 12), pygame.SRCALPHA)
        pygame.draw.rect(texture, (40, 150, 220), (3, 2, 14, 8), border_radius=3)
        return texture

    def test_vehicle_masks_follow_the_same_rotation_as_player_car_art(self):
        texture = self.car_texture()
        car = self.make_vehicle(texture, (40, 40), angle=37.4)

        actual, _key = traffic._car_image(car)
        expected = pygame.transform.rotate(texture, int(car.angle))

        self.assertEqual(actual.get_size(), expected.get_size())
        self.assertEqual(
            pygame.image.tostring(actual, "RGBA"),
            pygame.image.tostring(expected, "RGBA"),
        )

    def test_player_draw_uses_the_exact_sprite_used_to_build_its_mask(self):
        car = engine.Car(40, 40)
        car.angle = 37.4
        screen = pygame.Surface((160, 120), pygame.SRCALPHA)

        with patch.object(engine.traffic, "_car_image", wraps=traffic._car_image) as sprite:
            car.draw(screen, 0, 0)

        sprite.assert_called_once_with(car)

    def test_normal_and_police_traffic_masks_use_their_drawn_sprites(self):
        cars = (traffic.TrafficCar("A", "test-normal"), traffic.PoliceTrafficCar("A", "test-police"))

        for car in cars:
            with self.subTest(car=type(car).__name__):
                visible_sprite, _key = traffic._car_image(car)
                self.assertIs(visible_sprite, car.image)
                self.assertEqual(
                    traffic._vehicle_mask(car).count(),
                    pygame.mask.from_surface(visible_sprite).count(),
                )

    def test_transparent_texture_edges_do_not_create_vehicle_collisions(self):
        texture = self.car_texture()
        car = self.make_vehicle(texture, (40, 40))
        other = self.make_vehicle(texture, (54, 40))

        self.assertTrue(
            traffic.can_move_to(car, car.pos, [other], self.clear_collision_map())
        )
        other.pos.update(52, 40)
        self.assertFalse(
            traffic.can_move_to(car, car.pos, [other], self.clear_collision_map())
        )

    def test_vehicle_texture_mask_blocks_broad_walls_but_ignores_thin_dashes(self):
        texture = self.car_texture()
        car = self.make_vehicle(texture, (40, 40))

        dashed_map = self.clear_collision_map()
        for y in range(34, 46):
            dashed_map.set_at((40, y), (237, 28, 36))
        self.assertTrue(traffic.can_move_to(car, car.pos, [], dashed_map))

        wall_map = self.clear_collision_map()
        for x in range(39, 43):
            for y in range(36, 40):
                wall_map.set_at((x, y), (237, 28, 36))
        self.assertFalse(traffic.can_move_to(car, car.pos, [], wall_map))

    def test_fridge_food_restores_satiety_and_uses_limited_stock(self):
        survival = engine.SurvivalNeeds(hunger=72)
        stock = list(engine.FRIDGE_STARTING_STOCK)

        self.assertEqual(engine.consume_fridge_food(survival, stock, 1), 28)
        self.assertEqual(survival.hunger, 100)
        self.assertEqual(stock, [3, 1, 1])
        self.assertEqual(engine.consume_fridge_food(survival, stock, 1), 0)
        self.assertEqual(stock, [3, 1, 1])

    def test_fridge_menu_opens_left_of_center_in_the_warm_game_palette(self):
        panel, rows, close_button = engine.fridge_menu_layout((1280, 720))
        screen = pygame.Surface((1280, 720))

        self.assertEqual(panel.topleft, (230, 380))
        self.assertEqual(panel.right, 590)
        self.assertEqual(close_button.left, panel.left + 12)
        self.assertEqual(len(rows), 3)
        engine.draw_fridge_menu(screen, "Українська", 72, [3, 2, 1], selected=1)
        self.assertEqual(screen.get_at((panel.x + 8, panel.y + 70))[:3], (28, 20, 14))
        self.assertEqual(screen.get_at((rows[1].right - 12, rows[1].bottom - 12))[:3], (93, 51, 25))

    def test_fridge_interaction_coordinate_is_walkable_in_the_house_collision_map(self):
        source = pygame.image.load(os.path.join(engine._ASSET_ROOT, "ch_home/hkm.png"))
        scaled = pygame.transform.scale(source, (source.get_width() * 3, source.get_height() * 3))
        x, y = map(round, engine.HOUSE_FRIDGE_POS)

        self.assertTrue(scaled.get_rect().collidepoint(x, y))
        self.assertNotEqual(scaled.get_at((x, y))[:3], (0, 0, 0))

    def test_contextual_prompt_places_warm_keycap_before_the_action(self):
        screen = pygame.Surface((800, 600))

        panel, key_rect, label_rect = engine.draw_interaction_prompt(screen, "E", "Enter car")

        self.assertEqual(panel.left, 20)
        self.assertLess(panel.right, screen.get_width() // 2)
        self.assertLess(key_rect.right, label_rect.left)
        self.assertEqual(screen.get_at((key_rect.centerx, key_rect.centery))[:3], (228, 119, 31))

    def test_phone_and_speedometer_are_drawn_left_of_the_radar(self):
        screen = pygame.Surface((800, 600))
        font = pygame.font.Font(None, 18)
        engine.draw_mobile_phone(
            screen,
            100,
            720,
            font,
            0,
            {"bg_idx": 0, "case_idx": 0},
            0,
            [],
        )
        self.assertEqual(screen.get_at((25, 350))[:3], engine.CASE_PALETTE[0])

        speedometer = SimpleNamespace(
            ui_radius=75,
            ui_font=font,
            health=100,
            max_health=100,
            speed=0,
        )
        screen.fill((0, 0, 0))
        engine.Car.draw_speedometer(speedometer, screen)
        self.assertEqual(screen.get_at((468, 470))[:3], (150, 0, 0))
        self.assertEqual(screen.get_at((200, 145))[:3], (0, 0, 0))

    def test_ui_font_cache_reuses_phone_fonts(self):
        first = engine._cached_ui_font("Arial", 13, bold=True)
        second = engine._cached_ui_font("Arial", 13, bold=True)

        self.assertIs(first, second)


if __name__ == "__main__":
    unittest.main()
