"""Story and mission content for ATOF's open world.

Keep narrative definitions here. World simulation, rendering, input, saves, and
mission execution belong to :mod:`engine`.
"""

from dataclasses import dataclass


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


def run(screen, settings, *, continue_game=True):
    """Start the open-world session through the engine-owned runtime."""
    from engine import run_open_world

    return run_open_world(screen, settings, continue_game=continue_game)
