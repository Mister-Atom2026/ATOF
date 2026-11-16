"""Regression tests for the readability of the contextual interaction prompt."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

pygame.init()
pygame.display.set_mode((800, 600))

import engine


def _luminance(rgb):
    """Relative luminance (WCAG) of an RGB triple."""

    def channel(value):
        value = value / 255.0
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    r, g, b = rgb[:3]
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast(first, second):
    high, low = max(_luminance(first), _luminance(second)), min(
        _luminance(first), _luminance(second)
    )
    return (high + 0.05) / (low + 0.05)


def _blank_screen(fill=(0, 0, 0)):
    screen = pygame.Surface((800, 600))
    screen.fill(fill)
    return screen


class InteractionPromptContrastTests(unittest.TestCase):
    def test_backing_plate_does_not_bleed_with_background(self):
        points = []
        for background in ((255, 255, 255), (0, 0, 0)):
            screen = _blank_screen(background)
            panel, _key, _label = engine.draw_interaction_prompt(screen, "E", "Enter car")
            # Well inside the plate, away from the keycap, accent and text.
            points.append(screen.get_at((panel.right - 8, panel.centery))[:3])

        self.assertLess(_luminance(points[0]), 0.05, points[0])
        self.assertLess(_luminance(points[1]), 0.05, points[1])
        # The background colour must not show through the plate: the pixel is
        # virtually identical over white and over black terrain.
        self.assertLess(
            max(abs(a - b) for a, b in zip(points[0], points[1])), 25, points
        )

    def test_label_text_has_strong_contrast_against_plate(self):
        screen = _blank_screen((255, 255, 255))
        panel, _key, label = engine.draw_interaction_prompt(screen, "E", "Enter car")
        plate = screen.get_at((panel.right - 8, panel.centery))[:3]
        brightest = max(
            (
                screen.get_at((x, y))[:3]
                for y in range(label.top, label.bottom)
                for x in range(label.left, label.right)
            ),
            key=_luminance,
        )

        self.assertGreater(_luminance(brightest), 0.8, brightest)
        self.assertLess(_luminance(plate), 0.05, plate)
        self.assertGreaterEqual(_contrast(brightest, plate), 4.5)

    def test_stroked_text_helper_adds_a_dark_outline(self):
        font = engine._cached_ui_font(None, 23, weight="medium")
        plain = font.render("Enter car", True, (245, 248, 252))
        stroked, pad = engine._render_stroked_text(
            font, "Enter car", (245, 248, 252)
        )

        self.assertGreater(pad, 0)
        self.assertGreater(stroked.get_width(), plain.get_width())
        self.assertGreater(stroked.get_height(), plain.get_height())
        pixels = [
            stroked.get_at((x, y))[:3]
            for y in range(stroked.get_height())
            for x in range(stroked.get_width())
        ]
        self.assertTrue(any(_luminance(pixel) < 0.05 for pixel in pixels))
        self.assertTrue(any(_luminance(pixel) > 0.8 for pixel in pixels))

    def test_keycap_is_distinct_from_the_plate(self):
        screen = _blank_screen((255, 255, 255))
        panel, key, _label = engine.draw_interaction_prompt(screen, "E", "Enter car")
        plate = screen.get_at((panel.right - 8, panel.centery))[:3]
        keycap = screen.get_at((key.centerx, key.centery))[:3]
        dark_glyph_pixels = sum(
            1
            for y in range(key.top + 4, key.bottom - 4)
            for x in range(key.left + 4, key.right - 4)
            if _luminance(screen.get_at((x, y))) < 0.05
        )

        self.assertEqual(keycap, engine._PROMPT_KEYCAP_COLOR)
        self.assertGreater(_contrast(keycap, plate), 4.5)
        self.assertGreater(dark_glyph_pixels, 5)

    def test_no_bare_light_strip_under_the_label(self):
        screen = _blank_screen((255, 255, 255))
        panel, key, _label = engine.draw_interaction_prompt(screen, "E", "Enter car")
        # Scan below the keycap and the text: a white/black strip would show up
        # as a run of bright pixels across the bottom of the prompt.
        scan_y = panel.bottom - 6
        bright = sum(
            1
            # Skip the rounded corners, where the cool rim is expected.
            for x in range(panel.left + 40, panel.right - 40)
            if _luminance(screen.get_at((x, scan_y))) > 0.6
        )
        self.assertEqual(bright, 0)
        self.assertLess(key.bottom, scan_y)

    def test_alpha_fade_preserves_geometry_and_api(self):
        full_screen = _blank_screen()
        full = engine.draw_interaction_prompt(full_screen, "E", "Enter car", alpha=255)
        faded_screen = _blank_screen()
        faded = engine.draw_interaction_prompt(faded_screen, "E", "Enter car", alpha=110)

        self.assertIsNotNone(full)
        self.assertIsNotNone(faded)
        self.assertEqual(full, faded)
        panel = full[0]
        self.assertNotEqual(
            full_screen.get_at((panel.right - 8, panel.centery)),
            faded_screen.get_at((panel.right - 8, panel.centery)),
        )
        self.assertIsNone(
            engine.draw_interaction_prompt(_blank_screen(), "E", "Test", alpha=-10)
        )
        self.assertIsNotNone(
            engine.draw_interaction_prompt(_blank_screen(), "E", "Test", alpha=400)
        )


if __name__ == "__main__":
    unittest.main()
