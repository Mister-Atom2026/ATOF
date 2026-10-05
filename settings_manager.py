import json
import os

DEFAULT_SETTINGS = {
    "volume": 20,
    "lang_idx": 1,
    "keys": {
        "up": 1073741906,    # pygame.K_UP
        "down": 1073741905,  # pygame.K_DOWN
        "left": 1073741904,  # pygame.K_LEFT
        "right": 1073741903, # pygame.K_RIGHT
        "map": 9             # pygame.K_TAB
    }
}

def load_settings():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            return json.load(f)
    return DEFAULT_SETTINGS

def save_settings(settings):
    with open("config.json", "w") as f:
        json.dump(settings, f)