import json
import math
from pathlib import Path


SETTINGS_PATH = Path(__file__).resolve().parent / "config.json"
STATISTICS_PATH = Path(__file__).resolve().parent / "statistics.json"
GAME_SAVE_PATH = Path(__file__).resolve().parent / "savegame.json"
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
_STATISTICS_RECORD_KEYS = (
    "max_speed_kmh",
    "longest_drift_m",
    "distance_without_crash_m",
)


def _bounded_int(value, default, minimum, maximum):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def _finite_number(value, default=0.0, minimum=0.0, maximum=1_000_000_000.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    number = float(value)
    if not math.isfinite(number):
        return default
    return max(minimum, min(maximum, number))


def _normalize_statistics(values: dict) -> dict[str, int | float | str]:
    statistics: dict[str, int | float | str] = {
        "money": 0,
        "earned": 0,
        "spent": 0,
        "time": "00:00",
        "treasures": 0,
        "max_speed_kmh": 0.0,
        "longest_drift_m": 0.0,
        "distance_without_crash_m": 0.0,
    }
    if not isinstance(values, dict):
        return statistics

    for key in _STATISTICS_NUMBER_KEYS:
        statistics[key] = _bounded_int(values.get(key), 0, 0, 2**31 - 1)
    for key in _STATISTICS_RECORD_KEYS:
        statistics[key] = _finite_number(values.get(key))
    game_time = values.get("time")
    statistics["time"] = game_time if isinstance(game_time, str) else "00:00"
    return statistics


def load_game_save():
    try:
        values = json.loads(GAME_SAVE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(values, dict):
        return None

    player = values.get("player")
    car = values.get("car")
    if not isinstance(player, dict) or not isinstance(car, dict):
        return None

    house_player = values.get("house_player", {})
    if not isinstance(house_player, dict):
        house_player = {}
    house_x = _finite_number(house_player.get("x"), default=147.0, maximum=750.0)
    house_y = _finite_number(house_player.get("y"), default=156.0, maximum=300.0)
    if "x" not in house_player or "y" not in house_player or (
        abs(house_x - 723) < 40 and abs(house_y - 128) < 40
    ):
        house_x, house_y = 147.0, 156.0
    required_positions = (player.get("x"), player.get("y"), car.get("x"), car.get("y"))
    if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in required_positions):
        return None

    treasures = values.get("collected_treasures", [])
    if not isinstance(treasures, list) or any(not isinstance(item, str) for item in treasures):
        treasures = []

    return {
        "chapter_id": values.get("chapter_id")
        if isinstance(values.get("chapter_id"), str) and values.get("chapter_id")
        else "ch1",
        "game_state": values.get("game_state")
        if values.get("game_state") in ("CITY", "HOUSE")
        else "CITY",
        "player": {
            "x": _finite_number(player["x"], minimum=-1_000_000_000.0),
            "y": _finite_number(player["y"], minimum=-1_000_000_000.0),
            "angle": _finite_number(player.get("angle"), minimum=-360_000.0, maximum=360_000.0),
        },
        "car": {
            "x": _finite_number(car["x"], minimum=-1_000_000_000.0),
            "y": _finite_number(car["y"], minimum=-1_000_000_000.0),
            "angle": _finite_number(car.get("angle"), minimum=-360_000.0, maximum=360_000.0),
            "speed": _finite_number(car.get("speed"), minimum=-15.0, maximum=15.0),
            "health": _finite_number(car.get("health"), default=200.0, maximum=200.0),
            "is_broken": bool(car.get("is_broken", False)),
        },
        "house_player": {
            "x": house_x,
            "y": house_y,
            "angle": _finite_number(
                house_player.get("angle"),
                minimum=-360_000.0,
                maximum=360_000.0,
            ),
        },
        "money": _bounded_int(values.get("money"), 100, 0, 2**31 - 1),
        "earned": _bounded_int(values.get("earned"), 0, 0, 2**31 - 1),
        "spent": _bounded_int(values.get("spent"), 0, 0, 2**31 - 1),
        "game_time": _finite_number(values.get("game_time"), maximum=1439.999),
        "collected_treasures": treasures,
        "distance_streak": _finite_number(values.get("distance_streak")),
        "drift_streak": _finite_number(values.get("drift_streak")),
    }


def save_game_save(game_state):
    temporary_path = GAME_SAVE_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(game_state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(GAME_SAVE_PATH)


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
