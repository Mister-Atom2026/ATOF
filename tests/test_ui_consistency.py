import os
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

pygame.init()
pygame.display.set_mode((1, 1))

import engine_ui_consistency as ui


class PaletteTokenTests(unittest.TestCase):
    def test_canonical_palette_matches_engine_audit(self):
        self.assertEqual(ui.ACCENT, (212, 91, 18))
        self.assertEqual(ui.ACCENT_GOLD, (238, 164, 47))
        self.assertEqual(ui.MENU_BG, (20, 20, 20))
        self.assertEqual(ui.PANEL_BG, (22, 18, 16, 235))
        self.assertEqual(ui.ROW_ACTIVE, (65, 50, 40))
        self.assertEqual(ui.ROW_IDLE, (38, 38, 38))
        self.assertEqual(ui.BUTTON, (85, 85, 85))
        self.assertEqual(ui.BUTTON_HOVER, ui.ACCENT)
        self.assertEqual(ui.TEXT_PRIMARY, (255, 255, 255))
        self.assertEqual(ui.TEXT_SOFT, (220, 220, 220))
        self.assertEqual(ui.TEXT_MUTED, (150, 150, 150))
        self.assertEqual(ui.BORDER, (70, 52, 38))
        self.assertEqual(ui.OUTLINE, (0, 0, 0))

    def test_default_palette_is_a_namedtuple_with_valid_channels(self):
        self.assertIsInstance(ui.DEFAULT_PALETTE, tuple)
        for value in ui.DEFAULT_PALETTE:
            self.assertIsInstance(value, tuple)
            self.assertTrue(3 <= len(value) <= 4)
            for channel in value:
                self.assertIsInstance(channel, int)
                self.assertTrue(0 <= channel <= 255)

    def test_spacing_tokens_are_sane(self):
        spacing = ui.DEFAULT_SPACING
        self.assertEqual((ui.MARGIN, ui.ROW_HEIGHT, ui.ROW_GAP), (40, 64, 12))
        self.assertEqual(ui.PANEL_RADIUS, spacing.radius)
        self.assertEqual((ui.BUTTON_WIDTH, ui.BUTTON_HEIGHT), (spacing.button_width, spacing.button_height))
        for value in spacing:
            self.assertGreater(value, 0)


class ColorUtilityTests(unittest.TestCase):
    def test_clamp_color_clamps_and_casts(self):
        self.assertEqual(ui.clamp_color((-5, 300, 12.9)), (0, 255, 12))
        self.assertEqual(ui.clamp_color((1, 2, 3, -1)), (1, 2, 3, 0))
        self.assertEqual(ui.clamp_color([255, 0, 128, 999]), (255, 0, 128, 255))

    def test_clamp_color_rejects_bad_channel_count(self):
        with self.assertRaises(ValueError):
            ui.clamp_color((1, 2))
        with self.assertRaises(ValueError):
            ui.clamp_color((1, 2, 3, 4, 5))


class OutlinedTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = pygame.font.Font(None, 48)

    def test_rect_matches_plain_text_and_respects_anchor(self):
        surface = pygame.Surface((320, 160), pygame.SRCALPHA)
        rect = ui.draw_outlined_text(surface, "Hi", (160, 80), self.font, anchor="center")
        self.assertIsInstance(rect, pygame.Rect)
        # pygame-ce rendered surfaces can be taller than font.size() reports,
        # so compare against the actual rendered glyph surface.
        self.assertEqual(rect.size, self.font.render("Hi", True, (255, 255, 255)).get_size())
        self.assertEqual(rect.center, (160, 80))

    def test_outline_increases_visible_bounds(self):
        plain = pygame.Surface((320, 160), pygame.SRCALPHA)
        plain_rect = pygame.Rect(0, 0, *self.font.size("Hi"))
        plain_rect.center = (160, 80)
        plain.blit(_plain_label("Hi", self.font), plain_rect.topleft)

        outlined = pygame.Surface((320, 160), pygame.SRCALPHA)
        ui.draw_outlined_text(outlined, "Hi", (160, 80), self.font, anchor="center", outline_width=3)

        plain_bounds = plain.get_bounding_rect()
        outline_bounds = outlined.get_bounding_rect()
        self.assertGreater(outline_bounds.width, plain_bounds.width)
        self.assertGreater(outline_bounds.height, plain_bounds.height)

    def test_outline_and_fill_colors_are_rendered(self):
        surface = pygame.Surface((320, 160), pygame.SRCALPHA)
        ui.draw_outlined_text(
            surface,
            "OO",
            (160, 80),
            self.font,
            color=(255, 255, 255),
            outline_color=(0, 0, 0),
            outline_width=2,
            anchor="center",
        )
        pixels = {
            tuple(surface.get_at((x, y)))
            for y in range(surface.get_height())
            for x in range(surface.get_width())
        }
        self.assertIn((255, 255, 255, 255), pixels)
        self.assertIn((0, 0, 0, 255), pixels)

    def test_empty_text_is_safe(self):
        surface = pygame.Surface((80, 80), pygame.SRCALPHA)
        rect = ui.draw_outlined_text(surface, "", (10, 10), self.font, outline_width=4)
        self.assertIsInstance(rect, pygame.Rect)

    def test_unknown_anchor_raises(self):
        surface = pygame.Surface((80, 80), pygame.SRCALPHA)
        with self.assertRaises(ValueError):
            ui.draw_outlined_text(surface, "x", (10, 10), self.font, anchor="sideways")


class PanelAndWidgetTests(unittest.TestCase):
    def test_panel_fill_border_and_accent(self):
        surface = pygame.Surface((300, 260))
        surface.fill((255, 0, 255))
        rect = ui.draw_panel(surface, (40, 30, 200, 150), alpha=255, shadow=False)
        self.assertEqual(rect, pygame.Rect(40, 30, 200, 150))
        self.assertEqual(surface.get_at((140, 105))[:3], ui.PANEL_BG[:3])
        self.assertEqual(surface.get_at((41, 105))[:3], ui.ACCENT)
        self.assertNotEqual(surface.get_at((40, 105))[:3], (255, 0, 255))

    def test_panel_flags_and_alpha_clamp(self):
        surface = pygame.Surface((300, 260))
        surface.fill((0, 0, 0))
        ui.draw_panel(surface, (40, 30, 200, 150), alpha=999, accent=False, shadow=False, border=False)
        # alpha clamps to 255: the fill is opaque and no accent stripe is drawn.
        self.assertEqual(surface.get_at((41, 105))[:3], ui.PANEL_BG[:3])
        self.assertNotEqual(surface.get_at((41, 105))[:3], ui.ACCENT)
        self.assertEqual(surface.get_at((140, 105))[:3], ui.PANEL_BG[:3])

    def test_draw_row_selected_vs_idle(self):
        surface = pygame.Surface((300, 200))
        surface.fill((0, 0, 0))
        idle = pygame.Rect(20, 20, 200, 50)
        selected = pygame.Rect(20, 90, 200, 50)
        ui.draw_row(surface, idle, selected=False)
        ui.draw_row(surface, selected, selected=True)
        self.assertEqual(surface.get_at((120, 45))[:3], ui.ROW_IDLE)
        self.assertEqual(surface.get_at((120, 115))[:3], ui.ROW_ACTIVE)

    def test_draw_button_hover_uses_accent(self):
        surface = pygame.Surface((300, 200))
        surface.fill((0, 0, 0))
        font = pygame.font.Font(None, 22)
        normal = pygame.Rect(20, 20, 200, 50)
        hovered = pygame.Rect(20, 90, 200, 50)
        ui.draw_button(surface, normal, "No", font)
        ui.draw_button(surface, hovered, "Yes", font, hovered=True)
        # Sample near the corner to avoid the glyph text in the centre.
        self.assertEqual(surface.get_at((25, 25))[:3], ui.BUTTON)
        self.assertEqual(surface.get_at((25, 95))[:3], ui.BUTTON_HOVER)

    def test_centered_panel_rect(self):
        rect = ui.centered_panel_rect((1280, 720), (620, 400))
        self.assertEqual(rect.center, (640, 360))
        self.assertEqual(rect.size, (620, 400))

    def test_stacked_row_rects_layout(self):
        rows = ui.stacked_row_rects((800, 600), 3)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row.width == 800 - 2 * ui.MARGIN for row in rows))
        self.assertTrue(all(row.height == ui.ROW_HEIGHT for row in rows))
        self.assertTrue(all(row.x == ui.MARGIN for row in rows))
        for first, second in zip(rows, rows[1:]):
            self.assertEqual(second.y - first.y, ui.ROW_HEIGHT + ui.ROW_GAP)
        self.assertLessEqual(rows[0].y, rows[-1].y)
        self.assertLessEqual(rows[-1].bottom, 600)

    def test_stacked_row_rects_explicit_top_and_zero(self):
        rows = ui.stacked_row_rects((800, 600), 2, top=10)
        self.assertEqual(rows[0].y, 10)
        self.assertEqual(ui.stacked_row_rects((800, 600), 0), ())


class ModuleBoundaryTests(unittest.TestCase):
    def test_module_does_not_import_engine(self):
        source = (Path(ui.__file__).parent / "engine_ui_consistency.py").read_text(encoding="utf-8")
        self.assertNotIn("import engine\n", source)
        self.assertNotIn("from engine import", source)


def _plain_label(text, font):
    return font.render(text, True, (255, 255, 255))


if __name__ == "__main__":
    unittest.main()
