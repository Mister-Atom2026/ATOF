"""Lightweight quest/mission framework for ATOF.

This module is engine-agnostic: it tracks quest/objective state, evaluates
condition hooks, fires trigger/reward hooks, and serializes runtime progress.
Game code (engine/open_world/content modules) owns definitions and when to
emit events or run per-frame updates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Sequence


class QuestState(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


Condition = Callable[["QuestContext", "ObjectiveProgress", "QuestProgress"], bool]
Hook = Callable[["QuestContext", "ObjectiveProgress", "QuestProgress"], None]
Trigger = Callable[["QuestManager", "QuestContext"], None]


@dataclass(frozen=True)
class ObjectiveDef:
    """Single objective/step inside a quest."""

    objective_id: str
    description: str = ""
    required: int = 1
    hidden: bool = False
    optional: bool = False
    # Condition evaluated during updates/events; if omitted, progress advances only
    # via explicit manager.add_progress/objective completion calls.
    condition: Condition | None = None
    # How much progress to add when condition returns True on an update/event.
    progress_step: int = 1
    on_complete: Hook | None = None


@dataclass(frozen=True)
class QuestDef:
    """Static quest/mission definition registered with the manager."""

    quest_id: str
    title: str
    description: str = ""
    objectives: tuple[ObjectiveDef, ...] = ()
    # Optional gates/hooks. auto_start/start_condition let engine/world code keep
    # integration minimal by polling manager.update() with a context.
    auto_start: bool = False
    start_condition: Condition | None = None
    fail_condition: Condition | None = None
    on_start: Hook | None = None
    on_complete: Hook | None = None
    on_fail: Hook | None = None
    rewards: tuple[Hook, ...] = ()
    # Arbitrary content metadata (chapter, giver, location ids, etc.).
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class ObjectiveProgress:
    objective_id: str
    progress: int = 0
    completed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "progress": int(self.progress),
            "completed": bool(self.completed),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], objective_id: str) -> "ObjectiveProgress":
        return cls(
            objective_id=objective_id,
            progress=max(0, int(data.get("progress", 0) or 0)),
            completed=bool(data.get("completed", False)),
        )


@dataclass
class QuestProgress:
    quest_id: str
    state: QuestState = QuestState.INACTIVE
    objectives: dict[str, ObjectiveProgress] = field(default_factory=dict)
    # Extension point for custom per-quest runtime data.
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "quest_id": self.quest_id,
            "state": self.state.value,
            "objectives": {oid: obj.to_dict() for oid, obj in self.objectives.items()},
            "data": dict(self.data),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], quest_id: str) -> "QuestProgress":
        raw_state = str(data.get("state", QuestState.INACTIVE.value))
        try:
            state = QuestState(raw_state)
        except ValueError:
            state = QuestState.INACTIVE
        raw_objectives = data.get("objectives")
        objectives: dict[str, ObjectiveProgress] = {}
        if isinstance(raw_objectives, Mapping):
            for oid, value in raw_objectives.items():
                if isinstance(oid, str) and isinstance(value, Mapping):
                    objectives[oid] = ObjectiveProgress.from_dict(value, oid)
        raw_data = data.get("data")
        extra = dict(raw_data) if isinstance(raw_data, Mapping) else {}
        return cls(quest_id=quest_id, state=state, objectives=objectives, data=extra)


@dataclass
class QuestContext:
    """Runtime context passed to conditions/hooks/triggers.

    `game` can hold an engine-specific object/dict (player, car, world state,
    inventories, etc.). `event` names a discrete gameplay event when applicable.
    """

    game: Any = None
    event: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)
    dt: float = 0.0
    flags: MutableMapping[str, Any] = field(default_factory=dict)


class QuestManager:
    """Registry + runtime tracker for quest definitions."""

    def __init__(self, definitions: Iterable[QuestDef] | None = None):
        self.definitions: dict[str, QuestDef] = {}
        self.progress: dict[str, QuestProgress] = {}
        # Triggers run on matching events; "*" receives all events.
        self._triggers: dict[str, list[Trigger]] = {}
        if definitions:
            for definition in definitions:
                self.register(definition)

    # --- Registration / lookup ---

    def register(self, definition: QuestDef) -> None:
        self.definitions[definition.quest_id] = definition
        progress = self.progress.setdefault(
            definition.quest_id, QuestProgress(quest_id=definition.quest_id)
        )
        for objective in definition.objectives:
            progress.objectives.setdefault(
                objective.objective_id,
                ObjectiveProgress(objective_id=objective.objective_id),
            )

    def get_definition(self, quest_id: str) -> QuestDef | None:
        return self.definitions.get(quest_id)

    def get_progress(self, quest_id: str) -> QuestProgress | None:
        return self.progress.get(quest_id)

    def quests_by_state(self, state: QuestState) -> list[QuestDef]:
        return [
            definition
            for qid, definition in self.definitions.items()
            if self.progress.get(qid, QuestProgress(qid)).state == state
        ]

    # --- Triggers ---

    def register_trigger(self, event: str, trigger: Trigger) -> None:
        self._triggers.setdefault(event, []).append(trigger)

    def emit(self, event: str, context: QuestContext | None = None) -> None:
        """Emit a gameplay event, run triggers, then evaluate quest conditions."""
        ctx = context or QuestContext()
        ctx.event = event
        for trigger in list(self._triggers.get(event, [])):
            trigger(self, ctx)
        for trigger in list(self._triggers.get("*", [])):
            trigger(self, ctx)
        self.update(ctx)

    # --- State transitions ---

    def start_quest(self, quest_id: str, context: QuestContext | None = None) -> bool:
        definition = self.definitions.get(quest_id)
        progress = self.progress.get(quest_id)
        if definition is None or progress is None:
            return False
        if progress.state not in (QuestState.INACTIVE, QuestState.FAILED):
            return False
        progress.state = QuestState.ACTIVE
        for objective in definition.objectives:
            obj = progress.objectives.setdefault(
                objective.objective_id,
                ObjectiveProgress(objective_id=objective.objective_id),
            )
            obj.progress = 0
            obj.completed = False
        ctx = context or QuestContext()
        if definition.on_start:
            self._safe_call(definition.on_start, ctx, None, progress)
        self._evaluate_quest(definition, progress, ctx)
        return True

    def complete_quest(self, quest_id: str, context: QuestContext | None = None) -> bool:
        definition = self.definitions.get(quest_id)
        progress = self.progress.get(quest_id)
        if definition is None or progress is None or progress.state != QuestState.ACTIVE:
            return False
        progress.state = QuestState.COMPLETED
        for objective in definition.objectives:
            obj = progress.objectives.setdefault(
                objective.objective_id,
                ObjectiveProgress(objective_id=objective.objective_id),
            )
            obj.completed = True
            obj.progress = max(obj.progress, max(1, int(objective.required)))
        ctx = context or QuestContext()
        if definition.on_complete:
            self._safe_call(definition.on_complete, ctx, None, progress)
        for reward in definition.rewards:
            self._safe_call(reward, ctx, None, progress)
        return True

    def fail_quest(self, quest_id: str, context: QuestContext | None = None) -> bool:
        definition = self.definitions.get(quest_id)
        progress = self.progress.get(quest_id)
        if definition is None or progress is None or progress.state != QuestState.ACTIVE:
            return False
        progress.state = QuestState.FAILED
        ctx = context or QuestContext()
        if definition.on_fail:
            self._safe_call(definition.on_fail, ctx, None, progress)
        return True

    # --- Objective progress ---

    def add_progress(
        self,
        quest_id: str,
        objective_id: str,
        amount: int = 1,
        context: QuestContext | None = None,
    ) -> bool:
        definition = self.definitions.get(quest_id)
        progress = self.progress.get(quest_id)
        if definition is None or progress is None or progress.state != QuestState.ACTIVE:
            return False
        objective = self._find_objective(definition, objective_id)
        if objective is None:
            return False
        obj_progress = progress.objectives.setdefault(
            objective_id, ObjectiveProgress(objective_id=objective_id)
        )
        if obj_progress.completed:
            return False
        obj_progress.progress = max(0, obj_progress.progress + int(amount))
        if obj_progress.progress >= max(1, int(objective.required)):
            obj_progress.completed = True
            obj_progress.progress = max(1, int(objective.required))
            ctx = context or QuestContext()
            if objective.on_complete:
                self._safe_call(objective.on_complete, ctx, obj_progress, progress)
        self._maybe_complete(definition, progress, context or QuestContext())
        return True

    def set_objective_completed(
        self,
        quest_id: str,
        objective_id: str,
        context: QuestContext | None = None,
    ) -> bool:
        definition = self.definitions.get(quest_id)
        progress = self.progress.get(quest_id)
        if definition is None or progress is None or progress.state != QuestState.ACTIVE:
            return False
        objective = self._find_objective(definition, objective_id)
        if objective is None:
            return False
        obj_progress = progress.objectives.setdefault(
            objective_id, ObjectiveProgress(objective_id=objective_id)
        )
        if not obj_progress.completed:
            obj_progress.progress = max(1, int(objective.required))
            obj_progress.completed = True
            ctx = context or QuestContext()
            if objective.on_complete:
                self._safe_call(objective.on_complete, ctx, obj_progress, progress)
        self._maybe_complete(definition, progress, context or QuestContext())
        return True

    # --- Update loop ---

    def update(self, context: QuestContext | None = None) -> None:
        """Evaluate start/fail/condition hooks for all registered quests."""
        ctx = context or QuestContext()
        for quest_id, definition in self.definitions.items():
            progress = self.progress.setdefault(
                quest_id, QuestProgress(quest_id=quest_id)
            )
            self._ensure_objectives(definition, progress)
            if progress.state == QuestState.INACTIVE and (
                definition.auto_start
                or self._safe_condition(definition.start_condition, ctx, None, progress)
            ):
                self.start_quest(quest_id, ctx)
                progress = self.progress[quest_id]
            if progress.state == QuestState.ACTIVE:
                self._evaluate_quest(definition, progress, ctx)

    # --- Serialization ---

    def to_save_data(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of runtime quest progress."""
        return {
            "version": 1,
            "quests": {qid: prog.to_dict() for qid, prog in self.progress.items()},
        }

    def load_save_data(self, data: Any) -> None:
        """Merge saved progress into current definitions.

        Unknown quest ids are preserved in progress for forward compatibility, but
        only registered definitions are actively evaluated.
        """
        if not isinstance(data, Mapping):
            return
        quests = data.get("quests", data)
        if not isinstance(quests, Mapping):
            return
        for quest_id, raw in quests.items():
            if not isinstance(quest_id, str) or not isinstance(raw, Mapping):
                continue
            loaded = QuestProgress.from_dict(raw, quest_id)
            current = self.progress.setdefault(quest_id, QuestProgress(quest_id=quest_id))
            current.state = loaded.state
            current.data.update(loaded.data)
            definition = self.definitions.get(quest_id)
            if definition is not None:
                self._ensure_objectives(definition, current)
                for oid, obj in loaded.objectives.items():
                    if oid in current.objectives:
                        target = current.objectives[oid]
                        target.progress = max(0, int(obj.progress))
                        target.completed = bool(obj.completed)
            else:
                current.objectives.update(loaded.objectives)

    # --- Internals ---

    @staticmethod
    def _find_objective(definition: QuestDef, objective_id: str) -> ObjectiveDef | None:
        for objective in definition.objectives:
            if objective.objective_id == objective_id:
                return objective
        return None

    @staticmethod
    def _ensure_objectives(definition: QuestDef, progress: QuestProgress) -> None:
        for objective in definition.objectives:
            progress.objectives.setdefault(
                objective.objective_id,
                ObjectiveProgress(objective_id=objective.objective_id),
            )

    def _evaluate_quest(
        self, definition: QuestDef, progress: QuestProgress, context: QuestContext
    ) -> None:
        if progress.state != QuestState.ACTIVE:
            return
        if self._safe_condition(definition.fail_condition, context, None, progress):
            self.fail_quest(definition.quest_id, context)
            return
        changed = False
        for objective in definition.objectives:
            obj_progress = progress.objectives.setdefault(
                objective.objective_id,
                ObjectiveProgress(objective_id=objective.objective_id),
            )
            if obj_progress.completed or objective.condition is None:
                continue
            if self._safe_condition(objective.condition, context, obj_progress, progress):
                step = max(1, int(objective.progress_step))
                obj_progress.progress += step
                if obj_progress.progress >= max(1, int(objective.required)):
                    obj_progress.completed = True
                    obj_progress.progress = max(1, int(objective.required))
                    if objective.on_complete:
                        self._safe_call(objective.on_complete, context, obj_progress, progress)
                changed = True
        if changed or progress.state == QuestState.ACTIVE:
            self._maybe_complete(definition, progress, context)

    def _maybe_complete(
        self, definition: QuestDef, progress: QuestProgress, context: QuestContext
    ) -> None:
        if progress.state != QuestState.ACTIVE:
            return
        required_objectives = [o for o in definition.objectives if not o.optional]
        if not required_objectives:
            return
        if all(progress.objectives[o.objective_id].completed for o in required_objectives):
            self.complete_quest(definition.quest_id, context)

    @staticmethod
    def _safe_condition(
        condition: Condition | None,
        context: QuestContext,
        objective: ObjectiveProgress | None,
        quest: QuestProgress,
    ) -> bool:
        if condition is None:
            return False
        try:
            return bool(condition(context, objective, quest))
        except Exception:
            return False

    @staticmethod
    def _safe_call(
        hook: Hook | None,
        context: QuestContext,
        objective: ObjectiveProgress | None,
        quest: QuestProgress,
    ) -> None:
        if hook is None:
            return
        try:
            hook(context, objective, quest)
        except Exception:
            return


def create_default_manager() -> QuestManager:
    """Create a manager and register definitions from open_world/story modules.

    Import is lazy so quests.py stays usable without engine/story side effects.
    """
    manager = QuestManager()
    try:
        from open_world import iter_quest_definitions

        for definition in iter_quest_definitions():
            manager.register(definition)
    except Exception:
        pass
    return manager
