"""Keyboard input that binds movement to physical WASD key positions."""

import pygame


PHYSICAL_SCANCODES = {
    getattr(pygame, f"K_{letter}"): getattr(pygame, f"KSCAN_{letter.upper()}")
    for letter in "abcdefghijklmnopqrstuvwxyz"
    if hasattr(pygame, f"K_{letter}") and hasattr(pygame, f"KSCAN_{letter.upper()}")
}
PHYSICAL_SCANCODES.update({
    getattr(pygame, f"K_{number}"): getattr(pygame, f"KSCAN_{number}")
    for number in "0123456789"
    if hasattr(pygame, f"K_{number}") and hasattr(pygame, f"KSCAN_{number}")
})


class KeyboardState:
    """Drop-in key-state reader with layout-independent WASD movement."""

    def __init__(self):
        self._pressed_scancodes = set()

    def process_event(self, event):
        if event.type == pygame.KEYDOWN:
            scancode = getattr(event, "scancode", None)
            if scancode is not None:
                self._pressed_scancodes.add(scancode)
        elif event.type == pygame.KEYUP:
            scancode = getattr(event, "scancode", None)
            if scancode is not None:
                self._pressed_scancodes.discard(scancode)
        elif event.type == getattr(pygame, "WINDOWFOCUSLOST", -1):
            self._pressed_scancodes.clear()

    def __getitem__(self, key):
        scancode = PHYSICAL_SCANCODES.get(key)
        if scancode is not None and scancode in self._pressed_scancodes:
            return True
        try:
            return bool(pygame.key.get_pressed()[key])
        except (IndexError, TypeError):
            return False

    def matches(self, event, key):
        """Match a KEYDOWN to its US-layout key position or its reported key."""
        if getattr(event, "key", None) == key:
            return True
        scancode = PHYSICAL_SCANCODES.get(key)
        return scancode is not None and getattr(event, "scancode", None) == scancode
