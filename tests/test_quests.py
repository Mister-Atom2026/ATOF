import unittest
from unittest.mock import patch

import quests
from quests import (
    ObjectiveDef,
    ObjectiveProgress,
    QuestContext,
    QuestDef,
    QuestManager,
    QuestProgress,
    QuestState,
    create_default_manager,
)


def _always_true(ctx, obj, quest):
    return True


def _always_false(ctx, obj, quest):
    return False


def _event_is(evt):
    def cond(ctx, obj, quest):
        return ctx.event == evt
    return cond


class QuestFrameworkTests(unittest.TestCase):
    def _make_manager(self):
        calls = {"start": 0, "complete": 0, "fail": 0, "reward": 0, "obj_complete": 0}

        def on_start(ctx, obj, quest):
            calls["start"] += 1

        def on_complete(ctx, obj, quest):
            calls["complete"] += 1

        def on_fail(ctx, obj, quest):
            calls["fail"] += 1

        def on_reward(ctx, obj, quest):
            calls["reward"] += 1
            ctx.flags["rewarded"] = True

        def on_obj_complete(ctx, obj, quest):
            calls["obj_complete"] += 1

        quest = QuestDef(
            quest_id="q1",
            title="Quest 1",
            description="desc",
            objectives=(
                ObjectiveDef(
                    objective_id="o1",
                    description="step 1",
                    required=2,
                    on_complete=on_obj_complete,
                ),
                ObjectiveDef(
                    objective_id="o2",
                    description="step 2",
                    required=1,
                    optional=True,
                ),
            ),
            on_start=on_start,
            on_complete=on_complete,
            on_fail=on_fail,
            rewards=(on_reward,),
        )
        manager = QuestManager([quest])
        return manager, calls

    def test_state_transitions_and_hooks(self):
        manager, calls = self._make_manager()
        self.assertEqual(manager.get_progress("q1").state, QuestState.INACTIVE)
        self.assertTrue(manager.start_quest("q1", QuestContext(flags={})))
        self.assertEqual(manager.get_progress("q1").state, QuestState.ACTIVE)
        self.assertEqual(calls["start"], 1)
        # cannot start again while active
        self.assertFalse(manager.start_quest("q1"))
        self.assertEqual(calls["start"], 1)

        # required objective incomplete -> no auto-complete from optional alone
        self.assertTrue(manager.set_objective_completed("q1", "o2"))
        self.assertEqual(manager.get_progress("q1").state, QuestState.ACTIVE)

        self.assertTrue(manager.add_progress("q1", "o1", 1))
        self.assertEqual(manager.get_progress("q1").state, QuestState.ACTIVE)
        self.assertTrue(manager.add_progress("q1", "o1", 1))
        progress = manager.get_progress("q1")
        self.assertEqual(progress.state, QuestState.COMPLETED)
        self.assertTrue(progress.objectives["o1"].completed)
        self.assertTrue(progress.objectives["o2"].completed)
        self.assertEqual(calls["obj_complete"], 1)
        self.assertEqual(calls["complete"], 1)
        self.assertEqual(calls["reward"], 1)

    def test_fail_transition(self):
        manager, calls = self._make_manager()
        manager.start_quest("q1")
        self.assertTrue(manager.fail_quest("q1"))
        self.assertEqual(manager.get_progress("q1").state, QuestState.FAILED)
        self.assertEqual(calls["fail"], 1)
        self.assertFalse(manager.fail_quest("q1"))
        self.assertFalse(manager.complete_quest("q1"))

    def test_objective_progress_conditions_and_auto_completion(self):
        calls = {"obj": 0, "done": 0}

        def cond(ctx, obj, quest):
            return ctx.payload.get("hit")

        def on_obj(ctx, obj, quest):
            calls["obj"] += 1

        def on_done(ctx, obj, quest):
            calls["done"] += 1

        q = QuestDef(
            quest_id="qc",
            title="Cond",
            objectives=(
                ObjectiveDef("a", required=2, condition=cond, progress_step=1, on_complete=on_obj),
            ),
            on_complete=on_done,
        )
        manager = QuestManager([q])
        manager.start_quest("qc")
        manager.update(QuestContext(payload={"hit": False}))
        self.assertEqual(manager.get_progress("qc").objectives["a"].progress, 0)
        manager.update(QuestContext(payload={"hit": True}))
        self.assertEqual(manager.get_progress("qc").state, QuestState.ACTIVE)
        manager.update(QuestContext(payload={"hit": True}))
        prog = manager.get_progress("qc")
        self.assertEqual(prog.state, QuestState.COMPLETED)
        self.assertEqual(prog.objectives["a"].progress, 2)
        self.assertTrue(prog.objectives["a"].completed)
        self.assertEqual(calls["obj"], 1)
        self.assertEqual(calls["done"], 1)

    def test_start_and_fail_conditions_via_update(self):
        q = QuestDef(
            quest_id="qs",
            title="Start/Fail",
            objectives=(ObjectiveDef("o", required=1),),
            start_condition=lambda ctx, obj, quest: bool(ctx.flags.get("go")),
            fail_condition=lambda ctx, obj, quest: bool(ctx.flags.get("boom")),
        )
        manager = QuestManager([q])
        manager.update(QuestContext(flags={}))
        self.assertEqual(manager.get_progress("qs").state, QuestState.INACTIVE)
        manager.update(QuestContext(flags={"go": True}))
        self.assertEqual(manager.get_progress("qs").state, QuestState.ACTIVE)
        manager.update(QuestContext(flags={"go": True, "boom": True}))
        self.assertEqual(manager.get_progress("qs").state, QuestState.FAILED)

    def test_auto_start_and_triggers_emit(self):
        events = []

        def trig(manager, ctx):
            events.append((ctx.event, ctx.payload.get("x")))
            if ctx.event == "ping":
                manager.start_quest("qe", ctx)

        q_auto = QuestDef("qa", "Auto", objectives=(ObjectiveDef("o", required=1),), auto_start=True)
        q_evt = QuestDef("qe", "Evt", objectives=(ObjectiveDef("o", required=1),))
        manager = QuestManager([q_auto, q_evt])
        manager.register_trigger("ping", trig)
        manager.register_trigger("*", trig)
        manager.update(QuestContext())
        self.assertEqual(manager.get_progress("qa").state, QuestState.ACTIVE)
        manager.emit("ping", QuestContext(payload={"x": 7}))
        self.assertIn(("ping", 7), events)
        self.assertGreaterEqual(len([e for e in events if e[0] == "ping"]), 2)  # specific + wildcard
        self.assertEqual(manager.get_progress("qe").state, QuestState.ACTIVE)

    def test_event_condition_objective(self):
        q = QuestDef(
            quest_id="ev",
            title="Event",
            objectives=(ObjectiveDef("talk", required=1, condition=_event_is("talked")),),
        )
        manager = QuestManager([q])
        manager.start_quest("ev")
        manager.emit("moved")
        self.assertEqual(manager.get_progress("ev").state, QuestState.ACTIVE)
        manager.emit("talked")
        self.assertEqual(manager.get_progress("ev").state, QuestState.COMPLETED)

    def test_serialization_round_trip(self):
        q = QuestDef(
            quest_id="s",
            title="Save",
            objectives=(ObjectiveDef("a", required=3), ObjectiveDef("b", required=1)),
            metadata={"chapter": 1},
        )
        manager = QuestManager([q])
        manager.start_quest("s")
        manager.add_progress("s", "a", 2)
        manager.get_progress("s").data["custom"] = {"x": 1}
        saved = manager.to_save_data()
        self.assertEqual(saved["version"], 1)
        self.assertIn("s", saved["quests"])

        manager2 = QuestManager([q])
        manager2.load_save_data(saved)
        prog = manager2.get_progress("s")
        self.assertEqual(prog.state, QuestState.ACTIVE)
        self.assertEqual(prog.objectives["a"].progress, 2)
        self.assertFalse(prog.objectives["a"].completed)
        self.assertEqual(prog.data["custom"], {"x": 1})

        # load accepts plain quests mapping form too
        manager3 = QuestManager([q])
        manager3.load_save_data(saved["quests"])
        self.assertEqual(manager3.get_progress("s").objectives["a"].progress, 2)

    def test_unknown_quest_preservation_and_merge(self):
        q_known = QuestDef("known", "Known", objectives=(ObjectiveDef("o", required=2),))
        manager = QuestManager([q_known])
        payload = {
            "version": 1,
            "quests": {
                "known": {
                    "quest_id": "known",
                    "state": "active",
                    "objectives": {
                        "o": {"objective_id": "o", "progress": 1, "completed": False},
                        "removed": {"objective_id": "removed", "progress": 5, "completed": True},
                    },
                    "data": {"k": "v"},
                },
                "future": {
                    "quest_id": "future",
                    "state": "completed",
                    "objectives": {"x": {"objective_id": "x", "progress": 1, "completed": True}},
                    "data": {"mystery": True},
                },
            },
        }
        manager.load_save_data(payload)
        known = manager.get_progress("known")
        self.assertEqual(known.state, QuestState.ACTIVE)
        self.assertEqual(known.objectives["o"].progress, 1)
        self.assertNotIn("removed", known.objectives)  # only defined objectives kept/ensured
        self.assertEqual(known.data["k"], "v")

        future = manager.get_progress("future")
        self.assertIsNotNone(future)
        self.assertEqual(future.state, QuestState.COMPLETED)
        self.assertEqual(future.objectives["x"].progress, 1)
        self.assertEqual(future.data["mystery"], True)

    def test_invalid_saved_state_and_bad_inputs_are_safe(self):
        q = QuestDef("q", "Q", objectives=(ObjectiveDef("o", required=1),))
        manager = QuestManager([q])
        manager.load_save_data(None)
        manager.load_save_data({"quests": "bad"})
        manager.load_save_data({"quests": {1: {}, "q": "bad", "q2": {"state": "bogus"}}})
        self.assertEqual(manager.get_progress("q").state, QuestState.INACTIVE)
        self.assertEqual(manager.get_progress("q2").state, QuestState.INACTIVE)

        self.assertFalse(manager.start_quest("missing"))
        self.assertFalse(manager.add_progress("missing", "o", 1))
        self.assertFalse(manager.set_objective_completed("q", "missing"))
        self.assertFalse(manager.complete_quest("q"))  # inactive

    def test_defensive_hooks_and_conditions(self):
        def bad_cond(ctx, obj, quest):
            raise RuntimeError("boom")

        def bad_hook(ctx, obj, quest):
            raise RuntimeError("boom")

        q = QuestDef(
            quest_id="bad",
            title="Bad",
            objectives=(ObjectiveDef("o", required=1, condition=bad_cond, on_complete=bad_hook),),
            on_start=bad_hook,
            on_complete=bad_hook,
            rewards=(bad_hook,),
        )
        manager = QuestManager([q])
        self.assertTrue(manager.start_quest("bad"))
        manager.update(QuestContext())
        self.assertEqual(manager.get_progress("bad").state, QuestState.ACTIVE)
        self.assertTrue(manager.set_objective_completed("bad", "o"))
        self.assertEqual(manager.get_progress("bad").state, QuestState.COMPLETED)

    def test_create_default_manager_empty_definitions(self):
        with patch("open_world.iter_quest_definitions", return_value=(), create=True):
            manager = create_default_manager()
        self.assertIsInstance(manager, QuestManager)
        self.assertEqual(manager.definitions, {})

    def test_create_default_manager_faulty_definitions(self):
        with patch("open_world.iter_quest_definitions", side_effect=RuntimeError("bad"), create=True):
            manager = create_default_manager()
        self.assertIsInstance(manager, QuestManager)
        self.assertEqual(manager.definitions, {})

        # Faulty yielded items should not crash manager creation.
        with patch("open_world.iter_quest_definitions", return_value=[None], create=True):
            manager = create_default_manager()
        self.assertIsInstance(manager, QuestManager)
        self.assertEqual(manager.definitions, {})

    def test_quests_by_state_and_progress_helpers(self):
        q = QuestDef("q", "Q", objectives=(ObjectiveDef("o", required=1),))
        manager = QuestManager([q])
        self.assertEqual([d.quest_id for d in manager.quests_by_state(QuestState.INACTIVE)], ["q"])
        manager.start_quest("q")
        self.assertEqual([d.quest_id for d in manager.quests_by_state(QuestState.ACTIVE)], ["q"])
        self.assertIsNotNone(manager.get_definition("q"))
        self.assertIsNone(manager.get_definition("nope"))


class QuestDataclassTests(unittest.TestCase):
    def test_objective_and_quest_progress_dicts(self):
        obj = ObjectiveProgress.from_dict({"progress": -3, "completed": 1}, "o")
        self.assertEqual(obj.progress, 0)
        self.assertTrue(obj.completed)
        qp = QuestProgress.from_dict(
            {
                "state": "not-a-state",
                "objectives": {"o": {"progress": 2, "completed": False}, "bad": "x", 1: {}},
                "data": {"a": 1},
            },
            "q",
        )
        self.assertEqual(qp.state, QuestState.INACTIVE)
        self.assertIn("o", qp.objectives)
        self.assertEqual(qp.data, {"a": 1})
        d = qp.to_dict()
        self.assertEqual(d["quest_id"], "q")
        self.assertEqual(d["state"], "inactive")


class QuestSaveMigrationTests(unittest.TestCase):
    def test_legacy_bare_payload_is_normalized(self):
        payload = {"old": {"state": "active", "data": {"x": 1}}}
        migrated = quests.migrate_quest_save_data(payload)
        self.assertEqual(migrated["version"], quests.SAVE_VERSION)
        self.assertEqual(migrated["quests"]["old"]["data"], {"x": 1})

    def test_aliases_apply_and_cycles_are_safe(self):
        aliases = {"old": "current", "current": "newer", "loop_a": "loop_b", "loop_b": "loop_a"}
        payload = {
            "version": 0,
            "quests": {
                "old": {"state": "active"},
                "loop_a": {"state": "completed"},
                "unknown": {"state": "active"},
            },
        }
        migrated = quests.migrate_quest_save_data(payload, aliases)
        self.assertIn("newer", migrated["quests"])
        self.assertNotIn("old", migrated["quests"])
        self.assertIn("loop_a", migrated["quests"])
        self.assertIn("unknown", migrated["quests"])
        self.assertEqual(migrated["version"], quests.SAVE_VERSION)

    def test_explicit_current_id_wins_over_legacy_alias(self):
        migrated = quests.migrate_quest_save_data(
            {"old": {"state": "active"}, "current": {"state": "completed"}},
            {"old": "current"},
        )
        self.assertEqual(migrated["quests"]["current"]["state"], "completed")

    def test_register_alias_applies_on_manager_load(self):
        original = dict(quests.QUEST_ID_ALIASES)
        try:
            quests.register_quest_id_alias("intro.talk", "story.intro_talk")
            q = QuestDef("story.intro_talk", "Talk", objectives=(ObjectiveDef("talk", required=1),))
            manager = QuestManager([q])
            manager.load_save_data(
                {"version": 1, "quests": {"intro.talk": {"state": "active", "data": {"legacy": True}}}}
            )
            self.assertEqual(manager.get_progress("story.intro_talk").state, QuestState.ACTIVE)
            self.assertTrue(manager.get_progress("story.intro_talk").data["legacy"])
        finally:
            quests.QUEST_ID_ALIASES.clear()
            quests.QUEST_ID_ALIASES.update(original)

    def test_invalid_payloads_are_safe(self):
        for payload in (None, [], "bad", {"quests": "bad"}, {"quests": {1: "x"}}):
            migrated = quests.migrate_quest_save_data(payload)
            self.assertEqual(migrated["version"], quests.SAVE_VERSION)
            self.assertEqual(migrated["quests"], {})


if __name__ == "__main__":
    unittest.main()
