import pygame
import heapq


class GPS:
    def __init__(self, filename="мона їздити.png", road_color=(255, 242, 0), step=10):
        self.step = step
        self.road_color = road_color

        # Автоматичне завантаження при створенні об'єкта
        try:
            self.mask_img = pygame.image.load(filename).convert()
            self.width, self.height = self.mask_img.get_size()
            print(f"[GPS] Карта {filename} завантажена успішно.")
        except:
            print(f"[GPS] Помилка: Файл {filename} не знайдено!")
            self.mask_img = None

        self.path = []

    def get_dist(self, p1, p2):
        return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5

    def set_destination(self, start_pos, target_pos):
        """Прокладає маршрут. Викликати один раз при кліку на карту."""
        if not self.mask_img: return

        # Округляємо до сітки
        start = (int(start_pos[0] // self.step) * self.step, int(start_pos[1] // self.step) * self.step)
        goal = (int(target_pos[0] // self.step) * self.step, int(target_pos[1] // self.step) * self.step)

        queue = [(0, start)]
        came_from = {start: None}
        cost_so_far = {start: 0}

        while queue:
            current = heapq.heappop(queue)[1]

            if self.get_dist(current, goal) < self.step * 2:
                goal = current
                break

            for dx, dy in [(0, self.step), (0, -self.step), (self.step, 0), (-self.step, 0),
                           (self.step, self.step), (-self.step, -self.step), (self.step, -self.step),
                           (-self.step, self.step)]:
                neighbor = (current[0] + dx, current[1] + dy)

                if 0 <= neighbor[0] < self.width and 0 <= neighbor[1] < self.height:
                    pixel = self.mask_img.get_at(neighbor)[:3]
                    if pixel == self.road_color:
                        new_cost = cost_so_far[current] + self.get_dist(current, neighbor)
                        if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                            cost_so_far[neighbor] = new_cost
                            priority = new_cost + self.get_dist(neighbor, goal)
                            heapq.heappush(queue, (priority, neighbor))
                            came_from[neighbor] = current

        # Зберігаємо шлях
        if goal in came_from:
            self.path = []
            curr = goal
            while curr is not None:
                self.path.append(curr)
                curr = came_from[curr]
            self.path = self.path[::-1]
        else:
            print("[GPS] Маршрут не знайдено!")
            self.path = []

    def draw(self, screen, offset=(0, 0), scale=1.0, is_map_open=False):
        """Малює лінію навігатора."""
        if len(self.path) > 1:
            # Перераховуємо точки під камеру або під розмір карти TAB
            points = []
            for p in self.path:
                px = (p[0] + offset[0]) * scale
                py = (p[1] + offset[1]) * scale
                points.append((px, py))

            # Малюємо синю лінію
            pygame.draw.lines(screen, (0, 120, 255), False, points, 5)