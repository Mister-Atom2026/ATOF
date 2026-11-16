"""Foundation runtime helpers for future story/quest integration.

This module keeps engine wiring thin by owning:
- quest context snapshot construction (stable contract for conditions/hooks),
- discrete gameplay event emission into the quest manager,
- optional UI state (tracker/journal/toasts/dialogue) backed by ``ui_story``,
- mission marker collection + GPS objective sync plumbing.

No story content is defined here. Content/registries should live in separate
modules (for example ``open_world`` or dedicated ``story`` packages) and plug in
through the registry hooks below.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Sequence

import ui_story
from quests import QuestContext, QuestManager, QuestState, create_default_manager


# Stable keys exposed to quest conditions/hooks via ``QuestContext.game``.
# Future story code should treat this as the supported snapshot contract.
STORY_SNAPSHOT_CONTRACT = (
    "state",
    "in_car",
    "player_pos",
    "car_pos",
    "money",
    "wanted_level",
    "honor",
    "respect",
    "ammo",
    "reserve_ammo",
    "selected_weapon",
    "health",
    "hunger",
    "time_minutes",
    "collected_treasures",
    "distance_since_crash",
    "current_drift_distance",
    "phone_open",
    "dialogue_active",
    "flags",
)


def build_story_snapshot(
    *,
    game_state: str,
    atom: Any = None,
    car: Any = None,
    atom_h: Any = None,
    in_car: bool = False,
    money: int = 0,
    wanted: Any = None,
    honor_and_respect: Any = None,
    weapons: Any = None,
    survival: Any = None,
    game_time: float = 0.0,
    collected_treasures: Any = None,
    distance_since_crash: float = 0.0,
    current_drift_distance: float = 0.0,
    phone_open: bool = False,
    dialogue_active: bool = False,
    flags: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the engine-side snapshot consumed by quest conditions/hooks.

    The snapshot is intentionally plain-data (dict/scalars/tuples) where possible
    so conditions remain easy to test and decoupled from engine internals.
    """

    target = car if in_car and car is not None else atom
    pos = getattr(target, "pos", None)
    player_pos = (float(pos.x), float(pos.y)) if pos is not None else None
    car_pos_attr = getattr(car, "pos", None)
    car_pos = (float(car_pos_attr.x), float(car_pos_attr.y)) if car_pos_attr is not None else None

    snapshot: dict[str, Any] = {
        "state": str(game_state),
        "in_car": bool(in_car),
        "player_pos": player_pos,
        "car_pos": car_pos,
        "money": int(money),
        "wanted_level": int(getattr(wanted, "level", 0) or 0),
        "honor": float(getattr(honor_and_respect, "honor", 0.0) or 0.0),
        "respect": float(getattr(honor_and_respect, "respect", 0.0) or 0.0),
        "ammo": int(getattr(weapons, "ammo", 0) or 0),
        "reserve_ammo": int(getattr(weapons, "reserve_ammo", 0) or 0),
        "selected_weapon": getattr(weapons, "selected", "none"),
        "health": float(getattr(atom, "health", 100.0) if atom is not None else 100.0),
        "hunger": float(getattr(survival, "hunger", 100.0) if survival is not None else 100.0),
        "time_minutes": float(game_time),
        "collected_treasures": tuple(sorted(collected_treasures)) if collected_treasures else (),
        "distance_since_crash": float(distance_since_crash),
        "current_drift_distance": float(current_drift_distance),
        "phone_open": bool(phone_open),
        "dialogue_active": bool(dialogue_active),
        "flags": dict(flags or {}),
    }
    # Expose live objects for advanced hooks while keeping plain fields stable.
    snapshot["engine"] = {
        "atom": atom,
        "car": car,
        "atom_h": atom_h,
        "wanted": wanted,
        "honor_and_respect": honor_and_respect,
        "weapons": weapons,
        "survival": survival,
    }
    if extra:
        snapshot.update(dict(extra))
    return snapshot


@dataclass
class StoryRuntime:
    """Container for quest manager + optional story UI/markers.

    ``enabled``/UI visibility are content-driven: with no quest content and no
    markers/toasts/dialogue queued, drawing is effectively a no-op.
    """

    quest_manager: QuestManager | None = None
    labels: MutableMapping[str, str] = field(default_factory=dict)
    tracker: ui_story.ObjectiveTrackerHUD = field(default_factory=ui_story.ObjectiveTrackerHUD)
    tracker_state: ui_story.QuestState | None = None
    journal_open: bool = False
    journal_selected: int = 0
    toasts: ui_story.ToastManager = field(default_factory=ui_story.ToastManager)
    dialogue: ui_story.DialogueSubtitlePresenter = field(
        default_factory=ui_story.DialogueSubtitlePresenter
    )
    markers: list[ui_story.MissionMarker] = field(default_factory=list)
    marker_providers: list[Callable[["StoryRuntime", Mapping[str, Any]], Iterable[ui_story.MissionMarker]]] = field(
        default_factory=list
    )
    flags: dict[str, Any] = field(default_factory=dict)
    last_event: str | None = None

    @property
    def has_content(self) -> bool:
        if self.quest_manager is None:
            return False
        return bool(self.quest_manager.definitions)

    def emit(self, event: str, snapshot: Mapping[str, Any] | None = None, **payload: Any) -> None:
        if self.quest_manager is None:
            return
        self.last_event = event
        ctx = QuestContext(game=dict(snapshot or {}), event=event, payload=payload, flags=self.flags)
        try:
            self.quest_manager.emit(event, ctx)
        except Exception:
            return

    def update(
        self,
        snapshot: Mapping[str, Any],
        *,
        dt_seconds: float = 0.0,
        frame_scale: float = 1.0,
    ) -> None:
        # Dialogue/toasts advance independently of quest content.
        try:
            self.dialogue.update(max(0.0, dt_seconds))
        except Exception:
            pass
        try:
            self.toasts.update()
        except Exception:
            pass

        if self.quest_manager is None:
            return
        try:
            ctx = QuestContext(
                game=dict(snapshot),
                event=None,
                payload={},
                dt=float(frame_scale),
                flags=self.flags,
            )
            self.quest_manager.update(ctx)
        except Exception:
            return
        self._refresh_tracker_state()
        self._refresh_markers(snapshot)

    def _refresh_tracker_state(self) -> None:
        if self.quest_manager is None or not self.quest_manager.definitions:
            self.tracker_state = None
            return
        # Present the first active quest, otherwise first non-inactive quest.
        active = self.quest_manager.quests_by_state(QuestState.ACTIVE)
        if not active:
            completed = self.quest_manager.quests_by_state(QuestState.COMPLETED)
            failed = self.quest_manager.quests_by_state(QuestState.FAILED)
            chosen = (completed + failed)[:1]
        else:
            chosen = active[:1]
        if not chosen:
            self.tracker_state = None
            return
        qdef = chosen[0]
        progress = self.quest_manager.get_progress(qdef.quest_id)
        objectives: list[ui_story.Objective] = []
        for obj in qdef.objectives:
            op = progress.objectives.get(obj.objective_id) if progress else None
            required = max(1, int(getattr(obj, "required", 1) or 1))
            cur = int(getattr(op, "progress", 0) or 0) if op else 0
            completed = bool(getattr(op, "completed", False)) if op else False
            failed = bool(progress and progress.state == QuestState.FAILED)
            marker = _objective_marker_from_metadata(qdef, obj)
            objectives.append(
                ui_story.Objective(
                    id=obj.objective_id,
                    title_key=f"quest.{qdef.quest_id}.{obj.objective_id}.title",
                    title_default=getattr(obj, "description", "") or obj.objective_id,
                    description_key=f"quest.{qdef.quest_id}.{obj.objective_id}.desc",
                    description_default=getattr(obj, "description", ""),
                    completed=completed and progress is not None and progress.state != QuestState.FAILED,
                    failed=failed and not completed,
                    optional=bool(getattr(obj, "optional", False)),
                    progress=(min(cur, required) / required) if required else None,
                    target_position=marker,
                    marker_label=getattr(obj, "description", "") or obj.objective_id,
                    hidden=bool(getattr(obj, "hidden", False)),
                )
            )
        self.tracker_state = ui_story.QuestState(
            quest_id=qdef.quest_id,
            title_key=f"quest.{qdef.quest_id}.title",
            title_default=getattr(qdef, "title", qdef.quest_id),
            objectives=objectives,
        )

    def _refresh_markers(self, snapshot: Mapping[str, Any]) -> None:
        markers: list[ui_story.MissionMarker] = []
        # Quest/objective metadata markers: metadata may contain
        # marker_position=(x,y) / position / target_position and label/color/kind.
        if self.quest_manager is not None:
            for qdef in self.quest_manager.quests_by_state(QuestState.ACTIVE):
                progress = self.quest_manager.get_progress(qdef.quest_id)
                for obj in qdef.objectives:
                    op = progress.objectives.get(obj.objective_id) if progress else None
                    if op and op.completed:
                        continue
                    pos = _objective_marker_from_metadata(qdef, obj)
                    if pos is None:
                        continue
                    markers.append(
                        ui_story.MissionMarker(
                            id=f"{qdef.quest_id}:{obj.objective_id}",
                            position=pos,
                            label_key=f"quest.{qdef.quest_id}.{obj.objective_id}.marker",
                            label_default=getattr(obj, "description", "") or obj.objective_id,
                            color=_marker_color(getattr(qdef, "metadata", {}), getattr(obj, "description", "")),
                        )
                    )
        for provider in list(self.marker_providers):
            try:
                for marker in provider(self, snapshot) or ():
                    if marker is not None:
                        markers.append(marker)
            except Exception:
                continue
        self.markers = markers

    def iter_markers(self) -> list[ui_story.MissionMarker]:
        return [m for m in self.markers if getattr(m, "active", True)]

    def sync_gps_to_primary_objective(self, gps: Any) -> bool:
        """Point GPS to the primary active objective marker, if available.

        Returns True when a destination was applied. Does nothing when there is no
        active marker, so existing manual GPS destinations remain intact.
        """
        if gps is None or self.tracker_state is None:
            return False
        primary = self.tracker_state.primary_objective()
        if primary is None or primary.target_position is None:
            return False
        try:
            gps.set_destination(primary.target_position)
            return True
        except Exception:
            return False

    # --- UI drawing hooks (safe no-ops when there is nothing to show) ---

    def draw_hud(self, screen: Any, labels: Mapping[str, str] | None = None) -> None:
        merged = _merge_labels(self.labels, labels)
        try:
            self.toasts.draw(screen, merged)
        except Exception:
            pass
        try:
            self.dialogue.draw(screen, merged)
        except Exception:
            pass
        if self.tracker_state is not None and self.tracker_state.active_objectives():
            try:
                self.tracker.draw(screen, self.tracker_state, merged, anchor="top_left")
            except Exception:
                pass

    def draw_journal(self, screen: Any, labels: Mapping[str, str] | None = None):
        if not self.journal_open:
            return None
        merged = _merge_labels(self.labels, labels)
        try:
            return ui_story.draw_objectives_journal(
                screen, self.tracker_state, merged, selected_index=self.journal_selected
            )
        except Exception:
            return None


def _merge_labels(*sources: Mapping[str, str] | None) -> dict[str, str]:
    merged: dict[str, str] = {}
    for source in sources:
        if not source:
            continue
        try:
            for key, value in source.items():
                if isinstance(key, str) and isinstance(value, str):
                    merged[key] = value
        except Exception:
            continue
    return merged


def _objective_marker_from_metadata(qdef: Any, obj: Any):
    for source in (getattr(obj, "metadata", None), getattr(qdef, "metadata", None)):
        if not isinstance(source, Mapping):
            continue
        for key in ("target_position", "marker_position", "position", "world_pos"):
            value = source.get(key)
            pos = _coerce_pos(value)
            if pos is not None:
                return pos
    return None


def _coerce_pos(value: Any):
    if value is None:
        return None
    try:
        if isinstance(value, Mapping):
            if "x" in value and "y" in value:
                return (float(value["x"]), float(value["y"]))
            return None
        x, y = value[0], value[1]
        return (float(x), float(y))
    except Exception:
        return None


def _marker_color(metadata: Any, _text: str = "") -> tuple[int, int, int]:
    if isinstance(metadata, Mapping):
        color = metadata.get("marker_color")
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            try:
                return (int(color[0]), int(color[1]), int(color[2]))
            except Exception:
                pass
    return (255, 112, 0)


def bootstrap_story_runtime(game_save: Any = None) -> StoryRuntime:
    """Create runtime, load quest definitions, and apply saved progress/content hooks."""
    runtime = StoryRuntime()
    try:
        runtime.quest_manager = create_default_manager()
    except Exception:
        runtime.quest_manager = QuestManager()

    # Optional content-side bootstrap/registration hook.
    try:
        import open_world

        register = getattr(open_world, "register_story_runtime", None)
        if callable(register):
            register(runtime)
    except Exception:
        pass

    if isinstance(game_save, Mapping) and runtime.quest_manager is not None:
        try:
            runtime.quest_manager.load_save_data(game_save.get("quests"))
        except Exception:
            pass
    return runtime
