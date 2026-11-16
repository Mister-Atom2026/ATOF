"""Regression coverage for the vehicle-hijack disappearance bug.

The tests execute the real nested ``hijack_traffic_car`` / ``nearby_traffic_car``
functions from ``engine.run_open_world`` in an isolated harness, so a future
edit that reverts to the destructive behaviour fails here.
"""

import ast
import inspect
import os
import textwrap
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1, 1))

import engine
import traffic
import vehicle_preservation as vp


_RUN_SOURCE = "".join(inspect.getsourcelines(engine.run_open_world)[0])
_RUN_TREE = ast.parse(textwrap.dedent(_RUN_SOURCE))


def _nested_function_source(name):
    for node in ast.walk(_RUN_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return textwrap.dedent(ast.get_source_segment(_RUN_SOURCE, node))
    raise AssertionError(f"{name} not found in run_open_world")


def _hijack_harness():
    """Compile the engine's hijack function with an injected local scope."""
    setup = (
        "car = state['car']\n"
        "in_car = state['in_car']\n"
        "parked_cars = state['parked_cars']\n"
        "atom = state['atom']\n"
        "tutorial = state['tutorial']\n"
        "fleeing_drivers = state['fleeing_drivers']\n"
        "hostile_officers = state['hostile_officers']\n"
        "wanted = state['wanted']\n"
        "honor_and_respect = state['honor_and_respect']\n"
    )
    wrapper = "def _hijack(state):\n" + textwrap.indent(
        setup + _nested_function_source("hijack_traffic_car")
        + "\nhijack_traffic_car(state['npc'])\n"
        + "state['car'] = car\n"
        + "state['in_car'] = in_car\n",
        "    ",
    )
    namespace = dict(engine.__dict__)
    namespace["HostileOfficer"] = lambda pos: SimpleNamespace(pos=pos)
    namespace["FleeingDriver"] = lambda pos, target: SimpleNamespace(pos=pos)
    exec(compile(wrapper, "<hijack-harness>", "exec"), namespace)
    return namespace["_hijack"]


def _nearby_harness():
    """Compile the engine's nearby-car selector with an injected local scope."""
    setup = (
        "npc_cars = state['npc_cars']\n"
        "car = state['car']\n"
    )
    wrapper = "def _nearby(state, position):\n" + textwrap.indent(
        setup + _nested_function_source("nearby_traffic_car")
        + "\nstate['result'] = nearby_traffic_car(position)\n",
        "    ",
    )
    namespace = dict(engine.__dict__)
    exec(compile(wrapper, "<nearby-harness>", "exec"), namespace)
    return namespace["_nearby"]


def _traffic_car(x, y, *, police=False, alive=True, arrested=False):
    npc = traffic.TrafficCar("A", 900 + int(x))
    npc.pos.update(x, y)
    npc.is_police = police
    npc.is_alive = alive
    npc.is_arrested = arrested
    return npc


def _hijack_state(npc, previous=None, neighbors=()):
    if previous is None:
        previous = engine.Car(10, 20)
    return dict(
        car=previous,
        in_car=False,
        npc=npc,
        parked_cars=[],
        atom=SimpleNamespace(pos=pygame.Vector2(npc.pos)),
        tutorial=None,
        fleeing_drivers=[],
        hostile_officers=[],
        wanted=Mock(),
        honor_and_respect=Mock(),
        neighbors=list(neighbors),
    )


class HijackPreservationTests(unittest.TestCase):
    def setUp(self):
        self.hijack = _hijack_harness()

    def test_previous_player_car_is_always_parked_even_when_police(self):
        previous = engine.Car(120, 340)
        previous.is_police = True
        previous.vehicle_class = "stolen-police"
        npc = _traffic_car(600, 700)
        state = _hijack_state(npc, previous)

        self.hijack(state)

        self.assertEqual(len(state["parked_cars"]), 1)
        self.assertIs(state["parked_cars"][0], previous)
        self.assertEqual(tuple(previous.pos), (120, 340))

    def test_previous_player_car_is_parked_only_once(self):
        previous = engine.Car(120, 340)
        npc = _traffic_car(600, 700)
        state = _hijack_state(npc, previous)
        state["parked_cars"].append(previous)

        self.hijack(state)

        self.assertEqual(state["parked_cars"], [previous])

    def test_hijack_still_replaces_car_and_keeps_its_properties(self):
        npc = _traffic_car(600, 700, police=True)
        state = _hijack_state(npc)

        self.hijack(state)

        new_car = state["car"]
        self.assertIsNot(new_car, state["parked_cars"][0])
        self.assertEqual(tuple(new_car.pos), (600, 700))
        self.assertTrue(new_car.is_police)
        self.assertEqual(new_car.vehicle_class, "stolen-police")
        self.assertTrue(state["in_car"])
        self.assertEqual(tuple(state["atom"].pos), (600, 700))
        state["wanted"].raise_level.assert_called_once()
        self.assertEqual(state["wanted"].raise_level.call_args.args[0], 3)

    def test_only_target_npc_is_retired_neighbors_stay_intact(self):
        target = _traffic_car(600, 700)
        neighbors = [
            _traffic_car(640, 700),
            _traffic_car(600, 750),
            _traffic_car(660, 740),
        ]
        state = _hijack_state(target, neighbors=neighbors)

        self.hijack(state)

        self.assertFalse(target.is_alive)
        for neighbour in neighbors:
            self.assertTrue(neighbour.is_alive)
            self.assertGreater(neighbour.health, 0)
            self.assertEqual(neighbour.death_timer, 0.0)
        self.assertNotIn(target, state["parked_cars"])

    def test_dead_or_arrested_car_cannot_be_hijacked(self):
        for flags in (dict(alive=False), dict(arrested=True)):
            with self.subTest(flags=flags):
                npc = _traffic_car(600, 700, **flags)
                state = _hijack_state(npc)

                self.hijack(state)

                self.assertEqual(state["parked_cars"], [])
                self.assertFalse(state["in_car"])
                self.assertEqual(tuple(state["car"].pos), (10, 20))


class NearbyCarSelectionTests(unittest.TestCase):
    def setUp(self):
        self.nearby = _nearby_harness()

    def test_wrecks_and_arrested_cars_are_not_stealable(self):
        wreck = _traffic_car(610, 700, alive=False)
        arrested = _traffic_car(620, 700, arrested=True)
        usable = _traffic_car(640, 700)
        state = dict(
            npc_cars=[wreck, arrested, usable],
            car=engine.Car(0, 0),
            result=None,
        )
        self.nearby(state, (600, 700))
        self.assertIs(state["result"], usable)

    def test_neighbors_outside_100px_are_ignored(self):
        close = _traffic_car(680, 700)
        far = _traffic_car(710, 700)
        state = dict(npc_cars=[far, close], car=engine.Car(0, 0), result=None)
        self.nearby(state, (600, 700))
        self.assertIs(state["result"], close)

    def test_own_car_is_never_replaced_by_a_more_distant_npc(self):
        npc = _traffic_car(500, 700)
        own = engine.Car(620, 700)
        state = dict(npc_cars=[npc], car=own, result=None)
        self.nearby(state, (600, 700))
        self.assertIsNone(state["result"])


class TrafficCleanupTests(unittest.TestCase):
    def test_fading_wreck_survives_the_respawn_sweep(self):
        live = _traffic_car(100, 100)
        fading = _traffic_car(200, 200)
        fading.take_damage(fading.health + 1)
        expired = _traffic_car(300, 300)
        expired.take_damage(expired.health + 1)
        expired.death_timer = 0.0

        kept = vp.alive_or_fading([live, fading, expired])

        self.assertEqual(kept, [live, fading])
        self.assertGreater(fading.death_timer, 0)

    def test_police_wreck_death_timer_ticks_down(self):
        police = traffic.PoliceTrafficCar("A", 1234)
        police.take_damage(police.health + 1)
        self.assertFalse(police.is_alive)
        initial = police.death_timer
        self.assertGreater(initial, 0)

        police.update(None, engine.Car(0, 0), [], None, 1.0)

        self.assertEqual(police.death_timer, initial - 1.0)

    def test_engine_respawn_sweep_uses_fading_wreck_helper(self):
        source = inspect.getsource(engine.run_open_world)
        self.assertIn(
            "_vehicle_preservation.alive_or_fading(npc_cars)",
            source,
            "respawn sweep must keep fading wrecks instead of purging every dead NPC",
        )
        self.assertIn(
            "_vehicle_preservation.preserve_previous_car(car, parked_cars)",
            source,
            "hijack must always park the previous player car",
        )


if __name__ == "__main__":
    unittest.main()
