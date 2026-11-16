"""Helpers that keep vehicles visible and stable across hijacks and traffic churn.

The hijack flow in ``engine.py`` swaps the player's current car for a fresh
``Car`` built from a traffic NPC.  Two things can make a vehicle vanish during
that swap:

* the old player car is only parked when it is *not* a police car, so a stolen
  police car is silently dropped;
* a hijacked NPC is flagged ``is_alive = False`` and is later removed from the
  traffic list, even while its death animation (``death_timer``) should still
  be showing.

The functions below are small, dependency-free building blocks (duck typing,
no pygame import) that capture the safe behaviour.  ``engine.py`` (agent 7's
zone) can call them directly without introducing import cycles.
"""

from typing import Iterable, Optional

# Radius used to decide whether a hijacked car's spawn spot is crowded.
DEFAULT_NEARBY_RADIUS = 100.0


def _position(source):
    """Return an ``(x, y)`` tuple from a vector-like object or a sequence.

    Accepts a car (uses ``car.pos``), a ``pygame.Vector2`` or a plain
    ``(x, y)`` pair.  Returns ``None`` when no usable coordinates exist.
    """
    candidate = getattr(source, "pos", source)
    try:
        return float(candidate.x), float(candidate.y)
    except AttributeError:
        try:
            return float(candidate[0]), float(candidate[1])
        except (TypeError, IndexError, KeyError, ValueError):
            return None
    except (TypeError, ValueError):
        return None


def is_car_alive(car) -> bool:
    """An object with no ``is_alive`` attribute is treated as alive."""
    if car is None:
        return False
    return bool(getattr(car, "is_alive", True))


def is_hijackable(car) -> bool:
    """A car can be hijacked when it is alive and not currently arrested."""
    return is_car_alive(car) and not bool(getattr(car, "is_arrested", False))


def _same_car(first, second) -> bool:
    """Identity comparison that also tolerates unhashable car objects."""
    return first is second


def contains_car(cars: Iterable, car) -> bool:
    """Membership test by identity (car classes do not define ``__eq__``)."""
    return any(_same_car(existing, car) for existing in cars)


def preserve_previous_car(previous_car, parked_cars, *, include_police=True) -> bool:
    """Keep the player's previous car on the map before swapping vehicles.

    Returns ``True`` when the car was actually appended.  Nothing is appended
    for ``None``, for a car already parked, or (when ``include_police`` is
    false) for a police car.  The default ``include_police=True`` deliberately
    fixes the old behaviour that dropped stolen police cars.
    """
    if previous_car is None:
        return False
    if not include_police and bool(getattr(previous_car, "is_police", False)):
        return False
    if contains_car(parked_cars, previous_car):
        return False
    parked_cars.append(previous_car)
    return True


def filter_nearby_cars(
    cars: Iterable,
    position,
    radius: float = DEFAULT_NEARBY_RADIUS,
    *,
    exclude=None,
    include_dead: bool = False,
):
    """Return the cars whose centre lies within ``radius`` of ``position``.

    Dead cars (``is_alive is False``) are skipped by default, as are the
    object passed as ``exclude`` (usually the car being hijacked).
    """
    origin = _position(position)
    if origin is None or radius < 0:
        return []
    radius_squared = radius * radius
    nearby = []
    for car in cars:
        if car is None or _same_car(car, exclude):
            continue
        if not include_dead and not is_car_alive(car):
            continue
        car_position = _position(car)
        if car_position is None:
            continue
        dx = car_position[0] - origin[0]
        dy = car_position[1] - origin[1]
        if dx * dx + dy * dy <= radius_squared:
            nearby.append(car)
    return nearby


def nearest_car(
    cars: Iterable,
    position,
    radius: float = DEFAULT_NEARBY_RADIUS,
    *,
    exclude=None,
    include_dead: bool = False,
):
    """Closest car within ``radius`` of ``position`` (or ``None``)."""
    origin = _position(position)
    nearby = filter_nearby_cars(
        cars,
        position,
        radius,
        exclude=exclude,
        include_dead=include_dead,
    )
    if not nearby or origin is None:
        return None

    def distance_squared(car):
        car_position = _position(car)
        dx = car_position[0] - origin[0]
        dy = car_position[1] - origin[1]
        return dx * dx + dy * dy

    return min(nearby, key=distance_squared)


def is_spawn_crowded(
    position,
    cars: Iterable,
    radius: float = DEFAULT_NEARBY_RADIUS,
    *,
    exclude=None,
) -> bool:
    """Whether another live car already sits within ``radius`` of a spawn."""
    return bool(filter_nearby_cars(cars, position, radius, exclude=exclude))


def alive_or_fading(cars: Iterable):
    """Cars that should remain in the traffic list.

    A wreck with ``is_alive = False`` is kept while its ``death_timer`` is
    still positive so its death animation can finish, instead of popping out
    of existence at the next respawn sweep.
    """
    kept = []
    for car in cars:
        if car is None:
            continue
        if is_car_alive(car) or float(getattr(car, "death_timer", 0.0)) > 0.0:
            kept.append(car)
    return kept
