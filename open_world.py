"""Story and mission content for ATOF's open world.

Keep narrative definitions here. World simulation, rendering, input, saves, and
mission execution belong to :mod:`engine`.

This module is the primary content registry/entrypoint for future story:
- register runtime ``quests.QuestDef`` definitions via
  :func:`iter_quest_definitions` (or by registering them in
  :func:`register_story_runtime`),
- provide localized label tables / marker providers / UI hooks through
  :func:`register_story_runtime` without adding story content yet.

No active story content is shipped by default.
"""

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class StoryMission:
    """Data for a future main-story mission; gameplay behavior lives in engine."""

    mission_id: str
    title: str
    summary: str = ""
    objectives: tuple[str, ...] = ()


@dataclass(frozen=True)
class SideQuest:
    """Data for a future optional open-world task."""

    quest_id: str
    title: str
    summary: str = ""
    objectives: tuple[str, ...] = ()


# Main plot missions will be added here.
STORY_MISSIONS: tuple[StoryMission, ...] = ()

# Optional tasks and discoveries will be added here.
SIDE_QUESTS: tuple[SideQuest, ...] = ()


def iter_quest_definitions() -> Iterable[Any]:
    """Yield runtime quest definitions (``quests.QuestDef``).

    Story/content code can convert STORY_MISSIONS/SIDE_QUESTS into QuestDef
    instances here, import definitions from dedicated ``story`` modules, or
    aggregate multiple registries. Returning an empty iterator is safe and means
    "no active story content yet".
    """
    return ()


def iter_story_marker_providers() -> Iterable[Any]:
    """Yield optional marker-provider callables for ``story_runtime.StoryRuntime``.

    Providers receive ``(runtime, snapshot)`` and return an iterable of
    ``ui_story.MissionMarker`` objects.
    """
    return ()


def register_story_runtime(runtime: Any) -> None:
    """Hook for future content packages to register quests, markers, and labels.

    Called by :func:`story_runtime.bootstrap_story_runtime`. Keep side effects
    content-only (registration), not gameplay execution.
    """
    # Merge content-provided localized labels when available.
    labels = getattr(runtime, "labels", None)
    story_labels = globals().get("STORY_UI_LABELS")
    if isinstance(labels, dict) and isinstance(story_labels, dict):
        for key, value in story_labels.items():
            if isinstance(key, str) and isinstance(value, str):
                labels.setdefault(key, value)

    providers = getattr(runtime, "marker_providers", None)
    if isinstance(providers, list):
        for provider in iter_story_marker_providers():
            if callable(provider):
                providers.append(provider)


def run(screen, settings, *, continue_game=True):
    """Start the open-world session through the engine-owned runtime."""
    from engine import run_open_world

    return run_open_world(screen, settings, continue_game=continue_game)
