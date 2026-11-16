# Quest/Mission Framework (Foundation)

This document describes the **groundwork** added for future story/mission content in ATOF. No story, missions, characters, or narrative content are included yet.

## Goals

- Keep story/content definitions separate from engine simulation.
- Provide a lightweight runtime for quest state, objective progress, hooks, and save/load.
- Allow incremental integration with minimal changes to `engine.py` / existing systems.

## Module boundaries: `quests.py` vs `ui_story.py` vs `story_runtime.py`

- **`quests.py`** — engine-agnostic quest/mission **runtime framework**: definitions (`QuestDef`, `ObjectiveDef`), runtime progress/state machine (`QuestManager`, `QuestProgress`, `QuestState`), conditions/hooks/triggers, and save/load serialization. It does **not** render UI.
- **`ui_story.py`** — reusable **UI/presentation scaffolding** (tracker HUD, journal overlay, markers, toasts, dialogue/subtitles helpers). It consumes display-oriented quest/objective data (e.g. `QuestState`/`Objective` in `ui_story`) and label dictionaries; it does not own quest logic or persistence.
- **`story_runtime.py`** — **adapter/integration layer** that builds runtime snapshots for `QuestContext`, emits/updates quests, and bridges `quests.QuestManager` state into `ui_story` presentation/marker state for engine/UI callers. Content registration hooks live with content modules (e.g. `open_world`) and are wired through runtime/bootstrap helpers.

This separation lets content and quest logic evolve independently from rendering, while keeping engine integration thin.

## Core module: `quests.py`

`quests.py` is engine-agnostic and defines:

- **`QuestState`**: `inactive`, `active`, `completed`, `failed`.
- **`ObjectiveDef`**: static objective/step definition (`objective_id`, description, `required` count, optional/hidden flags, `condition`, `progress_step`, `on_complete` hook).
- **`QuestDef`**: static quest/mission definition (id/title/description, objectives, `auto_start`/`start_condition`, `fail_condition`, lifecycle hooks `on_start`/`on_complete`/`on_fail`, `rewards` hooks, metadata).
- **`QuestProgress` / `ObjectiveProgress`**: runtime state with `to_dict()` / `from_dict()` for serialization.
- **`QuestContext`**: runtime context passed to hooks/conditions (`game`, `event`, `payload`, `dt`, `flags`).
- **`QuestManager`**: registry + runtime tracker.

### `QuestManager` API

- `register(definition)` — register a `QuestDef` and initialize progress entries.
- `start_quest(quest_id, context=None)` / `complete_quest(...)` / `fail_quest(...)`
- `add_progress(quest_id, objective_id, amount=1, context=None)` — increment objective progress.
- `set_objective_completed(quest_id, objective_id, context=None)`
- `update(context=None)` — evaluate start/fail/objective conditions for active/eligible quests (polling hook).
- `emit(event, context=None)` — run registered triggers for an event, then `update()` (event-driven hook).
- `register_trigger(event, trigger)` — trigger signature: `(manager, context) -> None` (`"*"` receives all events).
- `quests_by_state(state)` / `get_progress(quest_id)` / `get_definition(quest_id)`
- `to_save_data()` / `load_save_data(data)` — serialize and restore runtime progress (JSON-safe).

Conditions/hooks are executed defensively (exceptions are ignored) so bad content logic does not crash the game loop.

## Defining and wiring content later (no content added now)

### 1. Create definitions

Define `QuestDef` / `ObjectiveDef` instances in a content module (e.g. future `story/` package or data-only modules). Keep behavior hooks small and pure where possible.

```python
from quests import ObjectiveDef, QuestDef, QuestState

def has_spoken_to_npc(ctx, obj, quest):
    return bool(ctx.game and ctx.game.get("flags", {}).get("met_npc_x"))

example = QuestDef(
    quest_id="example.intro",
    title="Example",
    description="Placeholder definition example (do not ship as story content).",
    objectives=(
        ObjectiveDef(
            objective_id="talk",
            description="Talk to NPC",
            required=1,
            condition=has_spoken_to_npc,
        ),
    ),
    auto_start=True,  # or use start_condition/register_trigger
)
```

> Note: The snippet above is documentation-only; actual narrative/content definitions should be added only when implementing story.

### 2. Register definitions

- **Preferred (foundation hook):** implement `iter_quest_definitions()` in `open_world.py` to yield `QuestDef` objects. `quests.create_default_manager()` lazily imports and registers them. This keeps content registration out of the engine.
- **Alternative:** register from a dedicated bootstrap called by engine/startup code: `manager.register(...)`.
- **Triggers:** register with `manager.register_trigger("event_name", trigger_fn)` during bootstrap for event-driven activation/progress.

### 3. Call runtime hooks from gameplay

Engine/world code should provide context and emit updates/events without embedding story logic:

- **Per-frame polling:** `manager.update(QuestContext(game=..., dt=frame_scale))` for condition-based objectives/start/fail checks.
- **Discrete events:** `manager.emit("entered_area", QuestContext(game=..., payload={...}))` or `manager.emit("item_collected", ...)` for trigger/objective reactions.
- **Direct progress:** `manager.add_progress(quest_id, objective_id, amount, context)` when gameplay code already knows a step advanced.

`QuestContext.game` can be a dict or object exposing the state hooks need (player/car/world flags, inventories, location, etc.). Keep this contract stable/documented as content grows.

### 4. Rewards and side effects

Use `rewards` hooks and lifecycle hooks (`on_complete`, `on_fail`, objective `on_complete`) to apply side effects (money/items/unlocks/flags) via the provided context. Prefer routing side effects through engine-owned helpers/APIs when they exist.

## Serialization / save integration

- Runtime progress is serialized via `QuestManager.to_save_data()` and restored via `QuestManager.load_save_data(...)`.
- Save payload shape: `{"version": 1, "quests": {<quest_id>: <QuestProgress dict>, ...}}`.
- `settings_manager.load_game_save()` preserves the top-level `quests` field as a dict (default `{}`) for forward compatibility.
- Engine save builders accept optional quest state and include `quests` when provided.
- Unknown quest IDs in save data are preserved in manager progress; only registered definitions are actively evaluated. This supports adding/removing future content safely.

## Current integration points (minimal, foundation-only)

- `quests.py`: framework and `create_default_manager()` bootstrap hook.
- `open_world.py`: `iter_quest_definitions()` placeholder (returns no content) and story-content home.
- `settings_manager.py`: load normalization preserves `quests`.
- `engine.py`:
  - `build_game_state_data(..., quest_state=None)` / `save_game_state(..., quest_state=None)` include quest state in saves.
  - `run_open_world(...)` initializes a default manager, loads saved quest progress, and performs a per-frame `update(...)` with a basic `QuestContext.game` snapshot (no story content or event emitters added yet).

## Next steps for adding actual story content

1. Create a `story/` package or content modules with `QuestDef` data/conditions/hooks (still separate from engine loop logic).
2. Yield/register those definitions from `open_world.iter_quest_definitions()` or a bootstrap function.
3. Add focused `manager.emit(...)` calls at meaningful gameplay events (dialog, pickups, area enter/exit, mission triggers, combat outcomes) and/or enrich `QuestContext.game`.
4. Add UI/journal presentation for `active/completed/failed` quests and objective progress.
5. Implement reward hooks that call stable engine APIs (inventory, money, unlocks) and add tests for quest state transitions and save/load round-trips.
6. Version/migrate quest save data if objective/quest IDs change in future content updates.