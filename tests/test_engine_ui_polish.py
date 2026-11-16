"""Tests for the shared UI-polish layer (objective chip, map legend, glyphs)."""

import os
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import engine
import engine_ui_polish as polish
import story_runtime
import ui_story


SCREEN_SIZE = (800, 600)


class TokenAndGlyphTests(unittest.TestCase):
    def setUp(self):
        self.screen = pygame.Surface(SCREEN_SIZE)

    def test_tokens_have_expected_semantic_values(self):
        self.assertEqual(polish.color('accent'), (212, 91, 18))
        self.assertIn('pulse_seconds', polish.UI_TOKENS)
        self.assertIn('row_height', polish.UI_TOKENS)

    def test_legend_kinds_have_shape_and_color(self):
        for kind in polish.MAP_LEGEND_KINDS:
            style = polish.MARKER_STYLES[kind]
            self.assertIn('shape', style, kind)
            self.assertIn('color', style, kind)
            self.assertIn('label_key', style, kind)
        shapes = {polish.MARKER_STYLES[k]['shape'] for k in polish.MAP_LEGEND_KINDS}
        self.assertEqual(len(shapes), len(polish.MAP_LEGEND_KINDS))

    def test_glyphs_are_shape_coded_not_only_colored(self):
        def pixels(kind):
            surf = pygame.Surface((40, 40))
            surf.fill((0, 0, 0))
            polish.draw_marker_glyph(surf, (20, 20), kind, radius=9)
            return pygame.image.tobytes(surf, 'RGBA')

        self.assertNotEqual(pixels('objective'), pixels('destination'))
        self.assertNotEqual(pixels('player'), pixels('home'))
        self.assertNotEqual(pixels('gunshop'), pixels('garage'))

    def test_unknown_kind_falls_back_without_crash(self):
        polish.draw_marker_glyph(self.screen, (100, 100), 'not-a-kind', radius=7)

    def test_ui_story_marker_icon_uses_shared_vocabulary(self):
        a = pygame.Surface((40, 40)); a.fill((0, 0, 0))
        b = pygame.Surface((40, 40)); b.fill((0, 0, 0))
        ui_story.draw_marker_icon(a, (20, 20), kind='objective')
        ui_story.draw_marker_icon(b, (20, 20), kind='home')
        self.assertNotEqual(
            pygame.image.tobytes(a, 'RGBA'),
            pygame.image.tobytes(b, 'RGBA'),
        )


class ObjectiveChipTests(unittest.TestCase):
    def setUp(self):
        self.screen = pygame.Surface(SCREEN_SIZE)

    def test_observe_detects_only_real_changes(self):
        chip = polish.ObjectiveChip(pulse_seconds=0.0)
        self.assertTrue(chip.observe('q1:o1'))
        self.assertFalse(chip.observe('q1:o1'))
        self.assertFalse(chip.observe(None))
        self.assertTrue(chip.observe('q1:o2'))
        self.assertEqual(chip.pulse, 0.0)

    def test_reduced_motion_disables_pulse(self):
        chip = polish.ObjectiveChip(pulse_seconds=10.0, reduced_motion=True)
        chip.observe('x')
        self.assertEqual(chip.pulse, 0.0)

    def test_draw_returns_bounded_rect(self):
        chip = polish.ObjectiveChip(margin=20, top=90)
        chip.observe('q:o')
        rect = chip.draw(self.screen, 'Знайти вихід', '350 m', labels={'story_objective_now': 'Ціль'})
        self.assertIsInstance(rect, pygame.Rect)
        self.assertGreaterEqual(rect.x, 0)
        self.assertGreaterEqual(rect.y, 0)
        self.assertLessEqual(rect.right, SCREEN_SIZE[0])
        self.assertLessEqual(rect.bottom, SCREEN_SIZE[1])

    def test_draw_handles_long_and_empty_text(self):
        chip = polish.ObjectiveChip()
        self.assertIsNone(chip.draw(self.screen, ''))
        rect = chip.draw(self.screen, 'Дуже довга назва завдання ' * 20, None)
        self.assertLessEqual(rect.width, 420)


class MapLegendAndMenuTests(unittest.TestCase):
    def setUp(self):
        self.screen = pygame.Surface(SCREEN_SIZE)

    def test_legend_uses_localized_captions_and_stays_on_screen(self):
        rect = polish.draw_map_legend(self.screen, {
            'map_legend': 'Легенда мапи',
            'map_marker_player': 'Ви',
        })
        self.assertIsInstance(rect, pygame.Rect)
        self.assertLessEqual(rect.right, SCREEN_SIZE[0])
        self.assertLessEqual(rect.bottom, SCREEN_SIZE[1])
        self.assertGreaterEqual(rect.x, 0)

    def test_legend_can_be_hidden_and_limited(self):
        self.assertIsNone(polish.draw_map_legend(self.screen, visible=False))
        rect = polish.draw_map_legend(self.screen, kinds=('player', 'home'))
        self.assertIsInstance(rect, pygame.Rect)

    def test_glass_panel_keeps_text_contrast(self):
        panel = pygame.Rect(10, 10, 200, 80)
        polish.draw_glass_panel(self.screen, panel)
        # The cached sheen must stay subtle (BLEND_RGBA_ADD adds raw RGB).
        for point in ((20, 20), (60, 25), (100, 40)):
            r, g, b, _a = self.screen.get_at(point)
            self.assertLess(max(r, g, b), 120, point)

    def test_panel_header_and_rule_are_reusable(self):
        panel = pygame.Rect(10, 10, 200, 80)
        polish.draw_glass_panel(self.screen, panel)
        rule = polish.draw_accent_rule(self.screen, 10, 100, 120)
        header = polish.draw_menu_header(self.screen, (10, 120), 'Garage', font=None)
        self.assertEqual(rule.width, 120)
        self.assertGreaterEqual(header.bottom, header.top)


class EngineIntegrationTests(unittest.TestCase):
    def test_engine_imports_polish_layer(self):
        self.assertIs(engine._ui_polish, polish)

    def test_all_languages_have_new_ui_keys(self):
        keys = ('story_objective_now', 'story_objective_updated', 'map_legend',
                'map_marker_player', 'map_marker_home', 'map_marker_gunshop',
                'map_marker_garage', 'map_marker_objective', 'map_marker_destination')
        for language in engine.SUPPORTED_LANGUAGES:
            for key in keys:
                self.assertIn(key, engine._UI_POLISH_TRANSLATIONS[language], (language, key))
                self.assertIn(key, engine._STORY_UI_TRANSLATIONS[language], (language, key))
                self.assertTrue(engine._UI_POLISH_TRANSLATIONS[language][key])

    def test_full_map_supports_legend_and_garage_marker(self):
        import inspect

        params = inspect.signature(engine.full_screen_map).parameters
        self.assertIn('garage_pos', params)
        self.assertIn('show_legend', params)

    def test_story_runtime_draws_chip_and_announces_changes(self):
        quest = ui_story.QuestState(
            quest_id='q',
            title_key='quest.q.title',
            title_default='Quest',
            objectives=[ui_story.Objective(
                id='o1', title_key='quest.q.o1.title', title_default='Go',
                target_position=(100, 100),
            )],
        )
        runtime = story_runtime.StoryRuntime(tracker_state=quest,
                                             objective_chip=polish.ObjectiveChip())
        screen = pygame.Surface(SCREEN_SIZE)
        runtime.toasts.clear()
        runtime.draw_hud(screen, {'quest.q.o1.title': 'Go'}, player_pos=(0, 0),
                         distance_formatter=lambda v: f'{v:.0f} m')
        self.assertEqual(len(runtime.toasts.toasts), 1)
        runtime.draw_hud(screen, {}, player_pos=(0, 0))
        self.assertEqual(len(runtime.toasts.toasts), 1)

    def test_story_runtime_falls_back_without_primary_objective(self):
        quest = ui_story.QuestState(quest_id='q', objectives=[])
        runtime = story_runtime.StoryRuntime(tracker_state=quest)
        runtime.draw_hud(pygame.Surface(SCREEN_SIZE), {})


if __name__ == '__main__':
    unittest.main()
