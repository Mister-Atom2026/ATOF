"""Straight-line GPS marker and distance calculations."""

from __future__ import annotations

import math


class GPS:
    def __init__(self) -> None:
        self.destination: tuple[float, float] | None = None

    @staticmethod
    def get_dist(
        first: tuple[float, float],
        second: tuple[float, float],
    ) -> float:
        return math.hypot(first[0] - second[0], first[1] - second[1])

    def set_destination(self, target_pos: tuple[float, float]) -> None:
        self.destination = (float(target_pos[0]), float(target_pos[1]))

    def clear_destination(self) -> None:
        self.destination = None

    def distance_to(self, position: tuple[float, float]) -> float | None:
        if self.destination is None:
            return None
        return self.get_dist(position, self.destination)
