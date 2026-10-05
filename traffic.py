"""Runtime road traffic and police AI. Training lives outside the game loop."""

import math
import os
import pickle
import random

import pygame


ROOT = os.path.dirname(os.path.abspath(__file__))
image_cache = {}
base_traffic_img = None
base_police_img = None
beep_sound = None
bot_brain = None
brain_load_attempted = False


TRAFFIC_NODES = {
    "A": {"pos": (7713, 6680), "next": ["B"]},
    "B": {"pos": (11835, 6680), "next": ["C", "G"]},
    "C": {"pos": (11835, 7526), "next": ["D", "E"]},
    "D": {"pos": (7713, 7526), "next": ["A"]},
    "E": {"pos": (11835, 8791), "next": ["F"]},
    "F": {"pos": (7713, 8791), "next": ["D"]},
    "G": {"pos": (12001, 5332), "next": ["H"]},
    "H": {"pos": (15116, 5342), "next": ["I"]},
    "I": {"pos": (15087, 6722), "next": ["K"]},
    "K": {"pos": (13417, 6737), "next": ["L"]},
    "L": {"pos": (13391, 10383), "next": ["M"]},
    "M": {"pos": (7333, 10381), "next": ["N"]},
    "N": {"pos": (7334, 6891), "next": ["A"]},
    "A1": {"pos": (7660, 6464), "next": ["B1"]},
    "B1": {"pos": (7568, 7742), "next": ["C1", "E1"]},
    "C1": {"pos": (12011, 7717), "next": ["D1"]},
    "D1": {"pos": (11975, 6454), "next": ["A1"]},
    "E1": {"pos": (7584, 8999), "next": ["F1"]},
    "F1": {"pos": (11962, 8990), "next": ["C1"]},
}


def _load_car_image(path, fallback_color):
    try:
        return pygame.transform.scale(
            pygame.image.load(os.path.join(ROOT, path)).convert_alpha(), (96, 39)
        )
    except (pygame.error, FileNotFoundError):
        surface = pygame.Surface((96, 39), pygame.SRCALPHA)
        surface.fill(fallback_color)
        return surface


def get_rotated_resources(angle):
    global base_traffic_img
    angle_int = int(angle % 360)
    key = ("traffic", angle_int)
    if key not in image_cache:
        if base_traffic_img is None:
            base_traffic_img = _load_car_image(
                os.path.join("cars", "ntk", "ntk-2107_classic.png"), (200, 50, 50)
            )
        image_cache[key] = pygame.transform.rotate(base_traffic_img, -angle_int)
    return image_cache[key]


def get_rotated_police_resources(angle):
    global base_police_img
    angle_int = int(angle % 360)
    key = ("police", angle_int)
    if key not in image_cache:
        if base_police_img is None:
            base_police_img = _load_car_image(
                os.path.join("cars", "tornado", "tornado_2025_police.png"), (255, 140, 0)
            )
        image_cache[key] = pygame.transform.rotate(base_police_img, -angle_int)
    return image_cache[key]


def try_load_brain():
    """Load the supplied NEAT brain once; continue with route-following if absent."""
    global bot_brain, brain_load_attempted
    if brain_load_attempted:
        return bot_brain
    brain_load_attempted = True

    brain_path = os.path.join(ROOT, "best_brain.pkl")
    config_path = os.path.join(ROOT, "config-feedforward.txt")
    if not (os.path.isfile(brain_path) and os.path.isfile(config_path)):
        return None

    try:
        import neat

        config = neat.config.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            config_path,
        )
        with open(brain_path, "rb") as brain_file:
            genome = pickle.load(brain_file)
        bot_brain = neat.nn.FeedForwardNetwork.create(genome, config)
        print("Traffic brain loaded.")
    except Exception as exc:
        print(f"Traffic brain could not be loaded: {exc}")
        bot_brain = None
    return bot_brain


def _rotated_car_rect(car, center):
    if getattr(car, "is_police", False):
        image = get_rotated_police_resources(car.angle)
    elif hasattr(car, "target_node"):
        image = get_rotated_resources(car.angle)
    else:
        image = getattr(car, "image", None)
        if image is None:
            image = pygame.Surface((96, 48), pygame.SRCALPHA)
        else:
            image = pygame.transform.rotate(image, -getattr(car, "angle", 0))
    return image.get_rect(center=(round(center.x), round(center.y)))


def _safe_stopping_distance(first_car, second_car):
    first_rect = _rotated_car_rect(first_car, first_car.pos)
    second_rect = _rotated_car_rect(second_car, second_car.pos)
    first_radius = math.hypot(first_rect.width, first_rect.height) / 2
    second_radius = math.hypot(second_rect.width, second_rect.height) / 2
    return first_radius + second_radius + 4


def can_move_to(car, position, other_cars, col_mask=None):
    """Prevent sprite overlap with every live vehicle and stop at map obstacles."""
    candidate_rect = _rotated_car_rect(car, position)
    for other in other_cars:
        if other is car or not getattr(other, "is_alive", True):
            continue
        if candidate_rect.colliderect(_rotated_car_rect(other, other.pos)):
            return False

    if col_mask is not None:
        mask_w, mask_h = col_mask.get_size()
        # Test center and inset corners so the full vehicle stays on the road.
        points = [
            candidate_rect.center,
            (candidate_rect.left + 5, candidate_rect.top + 5),
            (candidate_rect.right - 6, candidate_rect.top + 5),
            (candidate_rect.left + 5, candidate_rect.bottom - 6),
            (candidate_rect.right - 6, candidate_rect.bottom - 6),
        ]
        for x, y in points:
            if not (0 <= x < mask_w and 0 <= y < mask_h):
                return False
            color = col_mask.get_at((x, y))
            if color[0] < 50 and color[1] < 50 and color[2] < 50:
                return False
    return True


def _forward(angle):
    return pygame.Vector2(1, 0).rotate(angle + 180)


def _route_heading(car):
    target = pygame.Vector2(TRAFFIC_NODES[car.target_node]["pos"])
    vector = target - car.pos
    desired_angle = math.degrees(math.atan2(vector.y, vector.x)) + 180
    diff = (desired_angle - car.angle + 180) % 360 - 180
    return vector.length(), diff


class TrafficCar:
    def __init__(self, start_node_id, bot_id):
        self.id = bot_id
        self.is_police = False
        self.is_alive = True
        self.pos = pygame.Vector2(TRAFFIC_NODES[start_node_id]["pos"])
        self.target_node = random.choice(TRAFFIC_NODES[start_node_id]["next"])
        target = pygame.Vector2(TRAFFIC_NODES[self.target_node]["pos"])
        direction = target - self.pos
        self.angle = math.degrees(math.atan2(direction.y, direction.x)) + 180
        self.max_speed = random.uniform(3.5, 4.2)
        self.current_speed = 0.0
        self.speed = 0.0  # Kept in sync for compatibility with the copied police logic.
        self.rotation_speed = 4.0
        self.stuck_timer = 0
        self.is_arrested = False
        self.arrest_timer = 0
        self.is_stopped_by_police = False
        self.image = get_rotated_resources(self.angle)
        _load_horn()

    def get_sensors(self, other_traffic, player_car):
        sensors = [200.0] * 5
        for index, offset in enumerate((0, -30, 30, -60, 60)):
            ray = pygame.Vector2(1, 0).rotate(self.angle + 180 + offset)
            for other in [*other_traffic, player_car]:
                if other is self or not getattr(other, "is_alive", True):
                    continue
                vector = other.pos - self.pos
                distance = vector.length()
                if 0 < distance < 200 and ray.dot(vector.normalize()) > 0.9:
                    sensors[index] = min(sensors[index], distance)
        return sensors

    def _has_vehicle_ahead(self, other_traffic, player_car):
        forward = _forward(self.angle)
        for other in [*other_traffic, player_car]:
            if other is self or not getattr(other, "is_alive", True):
                continue
            distance = self.pos.distance_to(other.pos)
            if distance < 165 and (distance == 0 or forward.dot((other.pos - self.pos).normalize()) > 0.8):
                return True
        return False

    def update(self, col_mask, player_car, other_traffic, _traffic_state):
        if not self.is_alive:
            return
        if self.is_arrested:
            self.current_speed = self.speed = 0
            self.arrest_timer -= 1
            if self.arrest_timer <= 0:
                self.is_arrested = False
            return

        brain = try_load_brain()
        distance_to_node, angle_diff = _route_heading(self)
        blocked_ahead = self._has_vehicle_ahead(other_traffic, player_car)
        steering = 0.0
        desired_speed = self.max_speed

        if brain is not None and not blocked_ahead:
            try:
                outputs = brain.activate(self.get_sensors(other_traffic, player_car))
                if outputs:
                    steering = float(outputs[0]) * 3.0
                if len(outputs) > 1 and outputs[1] <= 0:
                    desired_speed *= 0.5
            except (ValueError, IndexError, TypeError):
                pass

        self.angle += max(-self.rotation_speed, min(self.rotation_speed, angle_diff + steering))
        next_speed = 0.0 if blocked_ahead else desired_speed
        if blocked_ahead:
            self.stuck_timer += 1
            if self.stuck_timer > 40 and random.random() < 0.02:
                self.play_horn(player_car)
        else:
            self.stuck_timer = 0

        forward = _forward(self.angle)
        candidate = self.pos + forward * next_speed
        obstacles = [*other_traffic, player_car]
        if next_speed > 0 and can_move_to(self, candidate, obstacles, col_mask):
            self.pos = candidate
            self.current_speed = self.speed = next_speed
        elif next_speed > 0:
            self.current_speed *= 0.6
            self.speed = self.current_speed
            self.stuck_timer += 1
        else:
            self.current_speed = self.speed = 0

        self.image = get_rotated_resources(self.angle)
        if distance_to_node < 45:
            self.target_node = random.choice(TRAFFIC_NODES[self.target_node]["next"])

    def play_horn(self, player_car):
        if beep_sound is None:
            return
        distance = self.pos.distance_to(player_car.pos)
        if distance < 1500:
            beep_sound.set_volume(max(0.01, (1.0 - distance / 1500) ** 2 * 0.4))
            beep_sound.play()

    def draw(self, screen, off_x, off_y):
        draw_pos = (self.pos.x + off_x, self.pos.y + off_y)
        screen.blit(self.image, self.image.get_rect(center=draw_pos))


def _load_horn():
    global beep_sound
    if beep_sound is None:
        try:
            beep_sound = pygame.mixer.Sound(os.path.join(ROOT, "sounds", "beep.wav"))
        except (pygame.error, FileNotFoundError):
            beep_sound = None


class PoliceTrafficCar(TrafficCar):
    def __init__(self, start_node_id, bot_id):
        super().__init__(start_node_id, bot_id)
        self.is_police = True
        self.target_car = None
        self.state = "patrol"
        self.max_speed = random.uniform(4.0, 4.5)
        self.image = get_rotated_police_resources(self.angle)

    def _find_target(self, other_traffic):
        candidates = [
            car for car in other_traffic
            if car is not self
            and not getattr(car, "is_police", False)
            and getattr(car, "is_alive", True)
            and not getattr(car, "is_arrested", False)
        ]
        if not candidates:
            return None
        target = min(candidates, key=lambda car: self.pos.distance_squared_to(car.pos))
        return target if self.pos.distance_to(target.pos) < 260 else None

    def _move_toward(self, target_pos, speed, obstacles, col_mask, turn_rate, steering=0.0):
        vector = target_pos - self.pos
        if vector.length_squared() == 0:
            return False
        desired_angle = math.degrees(math.atan2(vector.y, vector.x)) + 180
        difference = (desired_angle - self.angle + 180) % 360 - 180
        self.angle += max(-turn_rate, min(turn_rate, difference + steering))
        candidate = self.pos + _forward(self.angle) * speed
        if can_move_to(self, candidate, obstacles, col_mask):
            self.pos = candidate
            return True
        return False

    def update(self, col_mask, player_car, other_traffic, _traffic_state):
        if self.is_arrested:
            self.current_speed = self.speed = 0
            self.arrest_timer -= 1
            if self.arrest_timer <= 0:
                self.is_arrested = False
            return

        brain_steering = 0.0
        brain = try_load_brain()
        if brain is not None:
            try:
                outputs = brain.activate(self.get_sensors(other_traffic, player_car))
                if outputs:
                    brain_steering = float(outputs[0]) * 2.0
            except (ValueError, IndexError, TypeError):
                pass

        obstacles = [*other_traffic, player_car]
        if self.state == "patrol":
            distance, _ = _route_heading(self)
            if distance < 45:
                self.target_node = random.choice(TRAFFIC_NODES[self.target_node]["next"])
            else:
                self._move_toward(
                    pygame.Vector2(TRAFFIC_NODES[self.target_node]["pos"]),
                    self.max_speed,
                    obstacles,
                    col_mask,
                    3.0,
                    brain_steering,
                )
            self.target_car = self._find_target(other_traffic)
            if self.target_car is not None:
                self.state = "chasing"

        elif self.state == "chasing":
            target = self.target_car
            if target is None or not getattr(target, "is_alive", True) or getattr(target, "is_arrested", False):
                self.target_car = None
                self.state = "patrol"
            else:
                distance = self.pos.distance_to(target.pos)
                # Stop just before the vehicles' rotated sprite bounds can touch.
                if distance <= _safe_stopping_distance(self, target):
                    self.state = "stopping"
                else:
                    self._move_toward(
                        target.pos, self.max_speed + 0.5, obstacles, col_mask, 4.5, brain_steering
                    )

        elif self.state == "stopping":
            target = self.target_car
            if target is not None and getattr(target, "is_alive", True):
                target.current_speed = 0
                if hasattr(target, "speed"):
                    target.speed = 0
                target.is_stopped_by_police = True
                # Preserve the copy's 50% detention behavior while the patrol continues.
                if random.random() < 0.5:
                    target.is_arrested = True
                    target.arrest_timer = 300
            self.target_car = None
            self.state = "patrol"

        self.current_speed = self.speed = self.max_speed if self.state != "stopping" else 0
        self.image = get_rotated_police_resources(self.angle)

    def draw(self, screen, off_x, off_y):
        draw_pos = (self.pos.x + off_x, self.pos.y + off_y)
        screen.blit(self.image, self.image.get_rect(center=draw_pos))


def analyze_traffic_jams(_cars):
    return []


def init_traffic(count, police_chance=0.25):
    """Create normal traffic and cops at game start, including outside training mode."""
    if count <= 0:
        return []
    node_ids = list(TRAFFIC_NODES)
    starts = random.sample(node_ids, min(count, len(node_ids)))
    while len(starts) < count:
        starts.append(random.choice(node_ids))

    chance = min(0.30, max(0.20, police_chance))
    police_count = max(1, min(count, round(count * random.uniform(chance - 0.05, chance + 0.05))))
    police_indices = set(random.sample(range(count), police_count))

    cars = []
    for car_id, start_node in enumerate(starts):
        is_police = car_id in police_indices
        car_type = PoliceTrafficCar if is_police else TrafficCar
        car = car_type(start_node, car_id)
        cars.append(car)
    return cars
