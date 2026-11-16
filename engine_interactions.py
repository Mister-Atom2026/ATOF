"""Interaction eligibility and geometry helpers for engine gameplay flows."""

from __future__ import annotations

import pygame


TRUNK_INTERACTION_RADIUS = 55


def trunk_accessible_vehicle_class(vehicle_class) -> bool:
    """Only the player's main car and cars stolen by the player expose a trunk."""
    vehicle_class = str(vehicle_class or "")
    return vehicle_class == "sport" or vehicle_class.startswith("stolen-")


def car_trunk_point(vehicle):
    """World-space point behind a vehicle used for trunk interaction checks."""
    return vehicle.pos + pygame.Vector2(-70, 0).rotate(-vehicle.angle + 180)


def find_nearby_car_trunk(atom, car, parked_cars=None, *, in_car=False, radius=TRUNK_INTERACTION_RADIUS):
    """Return `(storage_key, vehicle)` for an eligible nearby trunk, else `(None, None)`.

    `storage_key` matches the keys used by `WeaponWheel.car_storage` in engine
    runtime: `"player_car"` for the active/main car and `"parked_{i}"` for parked
    vehicles from the runtime parked list.
    """
    if in_car or atom is None or car is None:
        return None, None

    candidates = [("player_car", car)]
    for index, vehicle in enumerate(parked_cars or []):
        candidates.append((f"parked_{index}", vehicle))

    for key, vehicle in candidates:
        try:
            if not trunk_accessible_vehicle_class(getattr(vehicle, "vehicle_class", "")):
                continue
            if atom.pos.distance_to(car_trunk_point(vehicle)) < radius:
                return key, vehicle
        except Exception:
            continue
    return None, None
