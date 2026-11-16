"""Quest runtime integration helpers.

These helpers keep quest context construction and update calls consistent and
defensive so future content hooks can rely on a stable snapshot shape without
per-frame fragility in the engine loop.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping


def build_quest_game_snapshot(
    *,
    game_state,
    atom,
    car,
    atom_h,
    in_car,
    money,
    wanted,
    honor_and_respect,
    weapons,
    survival,
    game_time,
    collected_treasures,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable game snapshot for quest conditions/hooks.

    Values are live references where appropriate (engine objects), but the key
    set is centralized to avoid ad-hoc drift between call sites.
    """
    snapshot: dict[str, Any] = {
        "game_state": game_state,
        "atom": atom,
        "car": car,
        "atom_h": atom_h,
        "in_car": bool(in_car),
        "money": money,
        "wanted": wanted,
        "honor_and_respect": honor_and_respect,
        "weapons": weapons,
        "survival": survival,
        "game_time": game_time,
        "collected_treasures": collected_treasures,
    }
    if extra:
        for key, value in extra.items():
            if isinstance(key, str):
                snapshot[key] = value
    return snapshot


def update_quest_manager(quest_manager, quest_context_cls, snapshot: Mapping[str, Any], *, dt: float) -> bool:
    """Run one quest-manager update tick defensively.

    Returns True if update executed, False if skipped/failed. Failures are logged
    at debug level so quest hook issues remain observable without breaking runtime.
    """
    if quest_manager is None or quest_context_cls is None:
        return False
    try:
        quest_manager.update(quest_context_cls(game=dict(snapshot), dt=float(dt)))
    except Exception:
        logging.getLogger(__name__).debug("quest_manager.update failed", exc_info=True)
        return False
    return True
