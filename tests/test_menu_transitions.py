import inspect
import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
pygame.init()
pygame.display.set_mode((800, 600))

import engine


class MenuTransitionTests(unittest.TestCase):
    def test_transition_helpers_exist(self):
        self.assertTrue(callable(engine.fade_menu_in))
        self.assertTrue(callable(engine.fade_menu_out))
        self.assertEqual(engine.MENU_TRANSITION_DURATION, 0.2)

    def test_menu_functions_accept_fade_in_parameter(self):
        for name in ('settings_sub_menu', '_audio_settings_menu', '_video_settings_menu', 'stats_dialog', 'save_slot_menu'):
            fn = getattr(engine, name)
            sig = inspect.signature(fn)
            self.assertIn('fade_in', sig.parameters, name)
            self.assertFalse(sig.parameters['fade_in'].default, name)

    def test_pause_menu_uses_fade_transitions_for_submenus(self):
        # simulate selecting Stats then Settings paths by patching dialogs
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 36)
        settings = {'lang_idx': 0, 'music_volume': 50, 'npc_volume': 50, 'crash_volume': 50, 'button_volume': 50, 'footsteps_volume': 50, 'video_width': 800, 'video_height': 600, 'fps_limit': 60}
        translations = {lang: {'resume':'Resume','stats':'Stats','settings':'Settings','menu':'Menu','back':'Back','volume':'Volume','lang':'Language','video':'Video','yes':'YES','no':'NO','confirm_q':'?','confirm_w':'','audio_hint':'','music_vol':'Music','npc_vol':'NPC','crash_vol':'Crash','button_vol':'Button','footsteps_vol':'Foot','window_mode':'Window','window_mode_value':'Resizable','resolution':'Res','fps_limit':'FPS','fps_unlimited':'Unlimited'} for lang in engine.SUPPORTED_LANGUAGES}
        with patch.object(engine, 'fade_menu_out') as fout, \
             patch.object(engine, 'fade_menu_in') as fin, \
             patch.object(engine, 'stats_dialog', return_value='BACK') as stats, \
             patch.object(engine, 'settings_sub_menu', return_value='BACK') as settings_menu, \
             patch.object(engine, 'confirm_dialog', return_value=False):
            # drive pause menu with synthetic events: down to stats, enter, then down to settings, enter, then esc
            events = [
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE),
            ]
            with patch('pygame.event.get', side_effect=[events[:2], events[2:4], events[4:]]):
                result = engine.pause_menu(screen, font, font, settings, translations, engine.SUPPORTED_LANGUAGES)
            self.assertEqual(result, 'CONTINUE')
            self.assertGreaterEqual(fout.call_count, 1)
            stats.assert_called()
            settings_menu.assert_called()

    def test_fade_helpers_call_fade_screen(self):
        screen = pygame.Surface((100, 100))
        with patch.object(engine, 'fade_screen') as fs:
            engine.fade_menu_in(screen, duration=0.3)
            engine.fade_menu_out(screen, duration=0.4)
        self.assertEqual(fs.call_count, 2)


if __name__ == '__main__':
    unittest.main()
