import json
from pathlib import Path


SETTINGS_PATH = Path(__file__).resolve().parent / "config.json"
DEFAULT_SETTINGS = {
    "music_volume": 20,
    "npc_volume": 100,
    "crash_volume": 100,
    "button_volume": 100,
    "footsteps_volume": 100,
    "lang_idx": 1,
    "keys": {
        "up": 1073741906,
        "down": 1073741905,
        "left": 1073741904,
        "right": 1073741903,
        "map": 9,
    },
}
_VOLUME_KEYS = ("music_volume", "npc_volume", "crash_volume", "button_volume", "footsteps_volume")
_LANGUAGE_COUNT = 3


def _bounded_int(value, default, minimum, maximum):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def _normalize_settings(values):
    settings = dict(DEFAULT_SETTINGS)
    settings["keys"] = dict(DEFAULT_SETTINGS["keys"])

    if isinstance(values, dict):
        settings.update(values)
        if "music_volume" not in values and "volume" in values:
            settings["music_volume"] = values["volume"]
        raw_keys = values.get("keys")
        if isinstance(raw_keys, dict):
            settings["keys"] = {**DEFAULT_SETTINGS["keys"], **raw_keys}
        else:
            settings["keys"] = dict(DEFAULT_SETTINGS["keys"])

    for key in _VOLUME_KEYS:
        settings[key] = _bounded_int(settings.get(key), DEFAULT_SETTINGS[key], 0, 100)
    settings["lang_idx"] = _bounded_int(settings.get("lang_idx"), DEFAULT_SETTINGS["lang_idx"], 0, _LANGUAGE_COUNT - 1)
    settings.pop("volume", None)
    return settings


def load_settings():
    try:
        values = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        values = {}
    return _normalize_settings(values)


def save_settings(settings):
    normalized = _normalize_settings(settings)
    temporary_path = SETTINGS_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(SETTINGS_PATH)
    settings.clear()
    settings.update(normalized)
