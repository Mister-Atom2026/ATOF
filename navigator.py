"""Grid-based pathfinding over the navigation map."""

from __future__ import annotations

import heapq
import math
from pathlib import Path
from typing import Optional

import pygame


class GPS:
    def __init__(
        self,
        filename: str = "world/мона їздити.png",
        road_color: tuple[int, int, int] = (255, 242, 0),
        step: int = 10,
    ) -> None:
        self.step = max(1, step)
        self.road_color = road_color
        map_path = Path(filename)
        if not map_path.is_absolute():
            map_path = Path(__file__).resolve().parent / map_path

        try:
            self.mask_img: Optional[pygame.Surface] = pygame.image.load(str(map_path)).convert()
        except (pygame.error, OSError) as exc:
            print(f"[GPS] Не вдалося завантажити карту {map_path}: {exc}")
            self.mask_img = None

        self.width, self.height = self.mask_img.get_size() if self.mask_img else (0, 0)
        self.path: list[tuple[int, int]] = []

    @staticmethod
    def get_dist(p1: tuple[int, int], p2: tuple[int, int]) -> float:
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def set_destination(
        self, start_pos: tuple[float, float], target_pos: tuple[float, float]
    ) -> None:
        """Find and store a route between two world positions."""
        if self.mask_img is None:
            self.path = []
            return

        start = (int(start_pos[0] // self.step) * self.step, int(start_pos[1] // self.step) * self.step)
        goal = (int(target_pos[0] // self.step) * self.step, int(target_pos[1] // self.step) * self.step)

        queue: list[tuple[float, tuple[int, int]]] = [(0.0, start)]
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        cost_so_far: dict[tuple[int, int], float] = {start: 0.0}
        directions = (
            (0, self.step), (0, -self.step), (self.step, 0), (-self.step, 0),
            (self.step, self.step), (-self.step, -self.step),
            (self.step, -self.step), (-self.step, self.step),
        )

        while queue:
            _, current = heapq.heappop(queue)
            if self.get_dist(current, goal) < self.step * 2:
                goal = current
                break

            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)
                if not (0 <= neighbor[0] < self.width and 0 <= neighbor[1] < self.height):
                    continue
                if self.mask_img.get_at(neighbor)[:3] != self.road_color:
                    continue

                new_cost = cost_so_far[current] + self.get_dist(current, neighbor)
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + self.get_dist(neighbor, goal)
                    heapq.heappush(queue, (priority, neighbor))
                    came_from[neighbor] = current

        if goal not in came_from:
            print("[GPS] Маршрут не знайдено!")
            self.path = []
            return

        route: list[tuple[int, int]] = []
        current: tuple[int, int] | None = goal
        while current is not None:
            route.append(current)
            current = came_from[current]
        self.path = list(reversed(route))

    def draw(
        self,
        screen: pygame.Surface,
        offset: tuple[float, float] = (0, 0),
        scale: float = 1.0,
        _is_map_open: bool = False,
    ) -> None:
        """Draw the stored route using the current camera offset and map scale."""
        if len(self.path) <= 1:
            return
        points = [
            (round((x + offset[0]) * scale), round((y + offset[1]) * scale))
            for x, y in self.path
        ]
        pygame.draw.lines(screen, (0, 120, 255), False, points, 5)
