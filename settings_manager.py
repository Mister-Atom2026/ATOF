import json
from pathlib import Path


SETTINGS_PATH = Path(__file__).resolve().parent / "config.json"
STATISTICS_PATH = Path(__file__).resolve().parent / "statistics.json"
DEFAULT_KEYS: dict[str, int] = {
    "up": 1073741906,
    "down": 1073741905,
    "left": 1073741904,
    "right": 1073741903,
    "map": 9,
}
DEFAULT_SETTINGS = {
    "music_volume": 20,
    "npc_volume": 100,
    "crash_volume": 100,
    "button_volume": 100,
    "footsteps_volume": 100,
    "lang_idx": 1,
    "video_width": 1280,
    "video_height": 720,
    "fps_limit": 60,
    "keys": DEFAULT_KEYS,
}
_VOLUME_KEYS = ("music_volume", "npc_volume", "crash_volume", "button_volume", "footsteps_volume")
_LANGUAGE_COUNT = 6
_FPS_LIMITS = (0, 30, 60, 75, 90, 120, 144, 165, 240)
_STATISTICS_NUMBER_KEYS = ("money", "earned", "spent", "treasures")
def _bounded_int(value, default, minimum, maximum):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def _normalize_statistics(values: dict) -> dict[str, int | str]:
    statistics: dict[str, int | str] = {
        "money": 0,
        "earned": 0,
        "spent": 0,
        "time": "00:00",
        "treasures": 0,
    }
    if not isinstance(values, dict):
        return statistics

    for key in _STATISTICS_NUMBER_KEYS:
        statistics[key] = _bounded_int(values.get(key), 0, 0, 2**31 - 1)
    game_time = values.get("time")
    statistics["time"] = game_time if isinstance(game_time, str) else "00:00"
    return statistics


def _normalize_settings(values):
    settings = dict(DEFAULT_SETTINGS)
    settings["keys"] = DEFAULT_KEYS.copy()

    if isinstance(values, dict):
        settings.update(values)
        if "music_volume" not in values and "volume" in values:
            settings["music_volume"] = values["volume"]
        raw_keys = values.get("keys")
        if isinstance(raw_keys, dict):
            merged_keys = DEFAULT_KEYS.copy()
            merged_keys.update(raw_keys)
            settings["keys"] = merged_keys
        else:
            settings["keys"] = DEFAULT_KEYS.copy()

    for key in _VOLUME_KEYS:
        settings[key] = _bounded_int(settings.get(key), DEFAULT_SETTINGS[key], 0, 100)
    settings["lang_idx"] = _bounded_int(settings.get("lang_idx"), DEFAULT_SETTINGS["lang_idx"], 0, _LANGUAGE_COUNT - 1)
    settings["video_width"] = _bounded_int(settings.get("video_width"), DEFAULT_SETTINGS["video_width"], 800, 7680)
    settings["video_height"] = _bounded_int(settings.get("video_height"), DEFAULT_SETTINGS["video_height"], 600, 4320)
    fps_limit = _bounded_int(settings.get("fps_limit"), DEFAULT_SETTINGS["fps_limit"], 0, 240)
    settings["fps_limit"] = fps_limit if fps_limit in _FPS_LIMITS else DEFAULT_SETTINGS["fps_limit"]
    settings.pop("fullscreen", None)
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


def load_statistics():
    try:
        values = json.loads(STATISTICS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        values = {}

    return _normalize_statistics(values)


def save_statistics(statistics):
    normalized = _normalize_statistics(statistics)

    temporary_path = STATISTICS_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(STATISTICS_PATH)
