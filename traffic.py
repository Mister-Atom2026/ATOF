"""Runtime road traffic and police behavior.

The traffic module keeps its own light-weight vehicle physics: every NPC car
accelerates, brakes and steers towards its next route node while respecting the
visible car silhouette and the world collision mask.  The module intentionally
depends only on pygame vectors so it can be exercised head-less in tests.
"""

import math
import os
import random
from typing import Optional

import pygame


ROOT = os.path.dirname(os.path.abspath(__file__))
image_cache: dict[tuple[object, ...], pygame.Surface] = {}
mask_cache: dict[tuple[object, ...], pygame.Mask] = {}
world_collision_cache: dict[int, tuple[pygame.Surface, pygame.Mask]] = {}
base_traffic_img: Optional[pygame.Surface] = None
base_police_img: Optional[pygame.Surface] = None
beep_sound: Optional[pygame.mixer.Sound] = None
_npc_volume = 1.0

# The player HUD renders ``speed * 8`` as km/h, so use the same scale for the
# NPC speed limits.  Keeping one conversion factor makes traffic speeds
# comparable with the player's (max ~130 km/h) instead of being magic numbers.
KMH_PER_PX_PER_FRAME = 8.0

# Traction is shared by all traffic cars.  The game loop may lower it through
# ``set_weather_grip``; individual vehicles may also expose a ``grip``
# attribute.  The most restrictive value always wins.
_weather_grip = 1.0
MIN_GRIP = 0.15

# Acceleration bands, expressed in km/h gained per frame.  A loaded sedan
# accelerates briskly in town and keeps pulling, but noticeably less, at
# motorway speeds.  Police cars use the same bands with a higher top speed.
_ACCEL_BANDS = ((40.0, 0.90), (80.0, 0.45), (float("inf"), 0.22))
_BRAKE_KMH_PER_FRAME = 1.8
_EMERGENCY_BRAKE_KMH_PER_FRAME = 3.4

# Steering and obstacle-probe tuning.
_MIN_TURN_RATE = 0.8
_PROBE_STEP = 16.0
_AVOID_ANGLE = 28.0
_NODE_APPROACH_RADIUS = 140.0
_TURN_START_DEGREES = 22.0


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


# ---------------------------------------------------------------------------
# Small numeric helpers
# ---------------------------------------------------------------------------


def _clamp(value, low, high):
    return max(low, min(high, value))


def _approach(current, target, max_delta):
    """Move ``current`` toward ``target`` by at most ``max_delta``."""
    if current < target:
        return min(current + max_delta, target)
    if current > target:
        return max(current - max_delta, target)
    return current


def _angle_delta(target_angle, angle):
    """Shortest signed rotation from ``angle`` to ``target_angle``."""
    return (target_angle - angle + 180) % 360 - 180


def _blend_angles(first, second, weight):
    return first + _angle_delta(second, first) * _clamp(weight, 0.0, 1.0)


def _kmh_to_speed(kmh):
    return float(kmh) / KMH_PER_PX_PER_FRAME


def _speed_to_kmh(speed):
    return abs(float(speed)) * KMH_PER_PX_PER_FRAME


def set_weather_grip(value):
    """Scale acceleration, braking and steering for rain/ice/snow (0..1)."""
    global _weather_grip
    _weather_grip = _clamp(float(value), MIN_GRIP, 1.0)


def get_weather_grip():
    return _weather_grip


def _resolve_grip(car, weather_grip=None, traffic_state=None):
    """Combine the global, per-frame and per-car grip limits."""
    grip = get_weather_grip()
    # ``traffic_state`` used to be a plain "RED"/"GREEN" string from the game;
    # accept a mapping too so callers can forward weather information directly.
    if isinstance(traffic_state, dict):
        candidate = traffic_state.get("weather_grip", traffic_state.get("grip"))
        if candidate is not None:
            grip = min(grip, float(candidate))
    if weather_grip is not None:
        grip = min(grip, float(weather_grip))
    car_grip = getattr(car, "grip", 1.0)
    try:
        grip = min(grip, float(car_grip))
    except (TypeError, ValueError):
        pass
    return _clamp(grip, MIN_GRIP, 1.0)


def _accel_rate(speed, grip):
    kmh = _speed_to_kmh(speed)
    for limit, rate in _ACCEL_BANDS:
        if kmh < limit:
            break
    traction = 0.30 + 0.70 * grip
    return _kmh_to_speed(rate) * traction


def _brake_rate(speed, grip, emergency=False):
    rate = _EMERGENCY_BRAKE_KMH_PER_FRAME if emergency else _BRAKE_KMH_PER_FRAME
    traction = 0.35 + 0.65 * grip
    return _kmh_to_speed(rate) * traction


def _control_speed(current, target, grip, frame_scale, emergency=False):
    """Smoothly accelerate/brake ``current`` toward ``target``.

    ``frame_scale`` is the number of simulated frames for this tick (the game
    passes ~1.0 normally).  Integrating with it keeps behaviour stable when the
    frame rate fluctuates.
    """
    target = max(0.0, float(target))
    if current < target:
        return min(target, current + _accel_rate(current, grip) * frame_scale)
    rate = _brake_rate(current, grip, emergency)
    return max(target, current - rate * frame_scale)


def _effective_turn_rate(car, grip, base=None):
    """Steering authority falls with speed and with low road grip."""
    if base is None:
        base = getattr(car, "rotation_speed", 4.0)
    speed_factor = 1.0 / (1.0 + _speed_to_kmh(getattr(car, "current_speed", 0.0)) / 90.0)
    return max(_MIN_TURN_RATE, float(base) * speed_factor * (0.45 + 0.55 * grip))


def _lookahead_distance(speed, grip):
    """How far ahead an NPC watches the road (longer when slippery)."""
    return _clamp(28.0 + _speed_to_kmh(speed) + (1.0 - grip) * 35.0, 34.0, 150.0)


# ---------------------------------------------------------------------------
# Assets and collision silhouettes
# ---------------------------------------------------------------------------


def _load_car_image(path, fallback_color):
    try:
        return pygame.transform.scale(
            pygame.image.load(os.path.join(ROOT, path)).convert_alpha(), (96, 39)
        )
    except (pygame.error, FileNotFoundError):
        surface = pygame.Surface((96, 39), pygame.SRCALPHA)
        surface.fill(fallback_color)
        return surface


def get_rotated_resources(angle: float) -> pygame.Surface:
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


def get_traffic_car_image() -> Optional[pygame.Surface]:
    global base_traffic_img
    if base_traffic_img is None:
        base_traffic_img = _load_car_image(
            os.path.join("cars", "ntk", "ntk-2107_classic.png"), (200, 50, 50)
        )
    return base_traffic_img


def get_rotated_police_resources(angle: float) -> pygame.Surface:
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


def get_police_car_image() -> Optional[pygame.Surface]:
    global base_police_img
    if base_police_img is None:
        base_police_img = _load_car_image(
            os.path.join("cars", "tornado", "tornado_2025_police.png"),
            (255, 140, 0),
        )
    return base_police_img


def configure_audio(settings):
    global _npc_volume
    try:
        volume = int(settings.get("npc_volume", 100))
    except (TypeError, ValueError):
        volume = 100
    _npc_volume = max(0, min(100, volume)) / 100


def _car_image(car):
    if hasattr(car, "target_node") and getattr(car, "is_police", False):
        return get_rotated_police_resources(car.angle), ("police", int(car.angle % 360))
    elif hasattr(car, "target_node"):
        return get_rotated_resources(car.angle), ("traffic", int(car.angle % 360))
    else:
        image = getattr(car, "image", None)
        if not isinstance(image, pygame.Surface):
            image = pygame.Surface((96, 48), pygame.SRCALPHA)
        angle = int(getattr(car, "angle", 0) % 360)
        vehicle_class = getattr(car, "vehicle_class", "sport")
        key = ("player", id(image), vehicle_class, angle)
        if key not in image_cache:
            # The player car's draw method rotates by +angle; use that exact
            # transform so the collision mask follows the visible texture.
            image_cache[key] = pygame.transform.rotate(image, angle)
        return image_cache[key], key


def _rotated_car_rect(car, center):
    image, _ = _car_image(car)
    return image.get_rect(center=(round(center.x), round(center.y)))


def _vehicle_mask(car):
    image, key = _car_image(car)
    mask = mask_cache.get(key)
    if mask is None:
        mask = pygame.mask.from_surface(image)
        mask_cache[key] = mask
    return mask


def _build_obstacle_mask(col_mask):
    # The collision map uses red for walls and near-black for solid blocks.
    dark_blocks = pygame.mask.from_threshold(
        col_mask, (0, 0, 0), (49, 49, 49, 255)
    )
    red_walls = pygame.mask.from_threshold(
        col_mask, (228, 24, 24), (27, 25, 25, 255)
    )
    dark_blocks.draw(red_walls, (0, 0))
    return dark_blocks


def _world_obstacle_mask(col_mask):
    """Build a reusable obstacle mask from the map's red walls and dark blocks."""
    cache_key = id(col_mask)
    cached = world_collision_cache.get(cache_key)
    if cached is not None and cached[0] is col_mask:
        return cached[1]
    obstacle_mask = _build_obstacle_mask(col_mask)
    world_collision_cache[cache_key] = (col_mask, obstacle_mask)
    return obstacle_mask


def prepare_collision_mask(col_mask, source_mask=None):
    """Warm the world silhouette mask during asset loading."""
    cache_key = id(col_mask)
    source = source_mask if source_mask is not None else col_mask
    obstacle_mask = _build_obstacle_mask(source)
    if obstacle_mask.get_size() != col_mask.get_size():
        obstacle_mask = obstacle_mask.scale(col_mask.get_size())
    world_collision_cache[cache_key] = (col_mask, obstacle_mask)


def _base_vehicle_size(car):
    if getattr(car, "is_police", False) or hasattr(car, "target_node"):
        return 96, 39
    image = getattr(car, "image", None)
    return image.get_size() if isinstance(image, pygame.Surface) else (96, 48)


def _safe_stopping_distance(first_car, second_car):
    first_radius = math.hypot(*_base_vehicle_size(first_car)) / 2
    second_radius = math.hypot(*_base_vehicle_size(second_car)) / 2
    return first_radius + second_radius + 4


def can_move_to(car, position, other_cars, col_mask=None):
    """Move only when the visible vehicle silhouette clears cars and map walls."""
    start = pygame.Vector2(car.pos)
    destination = pygame.Vector2(position)
    movement = destination - start
    steps = max(1, math.ceil(movement.length() / 6.0))
    candidate_mask = _vehicle_mask(car)
    collision_area_limit = max(12, round(candidate_mask.count() * 0.10))
    obstacle_mask = _world_obstacle_mask(col_mask) if col_mask is not None else None
    other_cars = other_cars or ()

    for step in range(1, steps + 1):
        candidate_position = start + movement * (step / steps)
        candidate_rect = _rotated_car_rect(car, candidate_position)

        for other in other_cars:
            if other is car or not getattr(other, "is_alive", True):
                continue
            other_pos = getattr(other, "pos", None)
            if other_pos is None:
                continue
            safe_distance = _safe_stopping_distance(car, other)
            if candidate_position.distance_squared_to(other_pos) > safe_distance**2:
                continue
            other_rect = _rotated_car_rect(other, other_pos)
            if not candidate_rect.colliderect(other_rect):
                continue
            offset = (
                other_rect.left - candidate_rect.left,
                other_rect.top - candidate_rect.top,
            )
            if candidate_mask.overlap(_vehicle_mask(other), offset) is not None:
                return False

        if obstacle_mask is not None:
            mask_w, mask_h = obstacle_mask.get_size()
            if (
                candidate_rect.left < 0
                or candidate_rect.top < 0
                or candidate_rect.right > mask_w
                or candidate_rect.bottom > mask_h
            ):
                return False
            # Ignore narrow painted lane dashes, but block when a meaningful
            # portion of the actual textured car body overlaps a wall.
            overlap = candidate_mask.overlap_area(
                obstacle_mask, (-candidate_rect.left, -candidate_rect.top)
            )
            if overlap >= collision_area_limit:
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


# ---------------------------------------------------------------------------
# Traffic physics helpers
# ---------------------------------------------------------------------------


def _collect_obstacles(player_car, other_traffic):
    obstacles = []
    for car in other_traffic or ():
        if car is not None:
            obstacles.append(car)
    if player_car is not None and player_car not in obstacles:
        obstacles.append(player_car)
    return obstacles


def _probe_wall_distance(car, angle, max_distance, col_mask):
    """Distance from ``car`` to the first wall in direction ``angle``.

    Only the world silhouette is tested here; nearby vehicles are handled by
    the (cheaper) forward-gap check, which keeps the per-frame cost bounded.
    """
    if col_mask is None or max_distance <= 0:
        return max_distance
    original_angle = car.angle
    origin = pygame.Vector2(car.pos)
    direction = _forward(angle)
    car.angle = angle
    try:
        distance = _PROBE_STEP
        while distance <= max_distance:
            if not can_move_to(car, origin + direction * distance, (), col_mask):
                return max(0.0, distance - _PROBE_STEP)
            distance += _PROBE_STEP
        return max_distance
    finally:
        car.angle = original_angle


def _vehicle_ahead_gap(car, obstacles):
    """Signed free space to the nearest car in front (``inf`` if none)."""
    forward = _forward(car.angle)
    side = pygame.Vector2(-forward.y, forward.x)
    best_gap = float("inf")
    for other in obstacles:
        if other is car or not getattr(other, "is_alive", True):
            continue
        other_pos = getattr(other, "pos", None)
        if other_pos is None:
            continue
        delta = other_pos - car.pos
        distance = delta.length()
        if distance > 420:
            continue
        projected = delta.dot(forward)
        lateral = abs(delta.dot(side))
        width = _safe_stopping_distance(car, other) + 18.0
        if projected > -12.0 and lateral < width:
            best_gap = min(best_gap, projected - _safe_stopping_distance(car, other))
    return best_gap


def _wall_avoidance_angle(car, route_angle, wall_clear, lookahead, col_mask):
    """Bias steering toward the side of a wall that offers more room.

    Both the probes and the resulting side angle are anchored to the *route*
    heading rather than the current orientation, so a car pinned against a
    wall can never ratchet itself sideways frame after frame.
    """
    left = _probe_wall_distance(car, route_angle - _AVOID_ANGLE, lookahead, col_mask)
    right = _probe_wall_distance(car, route_angle + _AVOID_ANGLE, lookahead, col_mask)
    clearer_distance = max(left, right)
    if clearer_distance <= wall_clear + 12.0:
        return route_angle
    side_angle = route_angle + (-_AVOID_ANGLE if left > right else _AVOID_ANGLE)
    weight = _clamp((lookahead - wall_clear) / max(lookahead, 1.0), 0.25, 0.9)
    return _blend_angles(route_angle, side_angle, weight)


class TrafficCar:
    def __init__(self, start_node_id, bot_id):
        self.id = bot_id
        self.is_police = False
        self.vehicle_class = "sedan"
        self.is_alive = True
        self.health = 300.0
        self.max_health = 300.0
        self.death_timer = 0.0
        self.pos = pygame.Vector2(TRAFFIC_NODES[start_node_id]["pos"])
        self.target_node = random.choice(TRAFFIC_NODES[start_node_id]["next"])
        target = pygame.Vector2(TRAFFIC_NODES[self.target_node]["pos"])
        direction = target - self.pos
        self.angle = math.degrees(math.atan2(direction.y, direction.x)) + 180
        # 42-58 km/h inside the city, noticeably below the player's top speed.
        self.max_speed = _kmh_to_speed(random.uniform(42.0, 58.0))
        self.current_speed = 0.0
        self.speed = 0.0  # Kept in sync for compatibility with the copied police logic.
        self.rotation_speed = 4.0
        self.grip = 1.0
        self.cruise_factor = random.uniform(0.92, 1.0)
        self.collision_recoil = 0.0
        self.just_hit = False
        self.stuck_timer = 0
        self.horn_pause_timer = 0.0
        self.fire_cooldown = 0.0
        self.is_arrested = False
        self.arrest_timer = 0
        self.is_stopped_by_police = False
        self.image = get_rotated_resources(self.angle)
        _load_horn()

    # -- reaction helpers ---------------------------------------------------

    def register_collision(self, impact_speed=0.0, frame_scale=1.0):
        """Apply a recoil impulse after hitting a car or a wall.

        Public so the engine (or tests) can notify a car about an external
        impact without having to reimplement the damage reaction.
        """
        if not self.is_alive:
            return
        impact = max(0.0, float(impact_speed))
        self.just_hit = True
        self.collision_recoil = max(self.collision_recoil, 8.0 * max(frame_scale, 1.0))
        self.current_speed = -min(impact * 0.18, _kmh_to_speed(10.0))
        self.speed = self.current_speed
        self.stuck_timer += frame_scale * 1.5
        # A tiny jitter breaks symmetrical stand-offs; keep it small and only
        # apply it to genuinely new impacts so a car pinned against a wall does
        # not slowly spin in place.
        self.angle = (self.angle + random.uniform(-1.0, 1.0)) % 360
        self.image = get_rotated_resources(self.angle)

    def _clear_collision_state(self, frame_scale):
        self.just_hit = False
        self.collision_recoil = max(0.0, self.collision_recoil - frame_scale)

    def _advance(self, obstacles, col_mask, frame_scale, heading=None):
        """Integrate the current speed, probing sideways when blocked.

        ``heading`` is the preferred steering direction; detour angles are
        measured from it so repeated contact with a wall cannot ratchet the
        car's orientation away from its route.
        """
        speed = self.current_speed
        if abs(speed) <= 0.01:
            self._clear_collision_state(frame_scale)
            return False

        forward = _forward(self.angle)
        candidate = self.pos + forward * speed * frame_scale
        if can_move_to(self, candidate, obstacles, col_mask):
            self.pos = candidate
            self._clear_collision_state(frame_scale)
            return True

        # Blocked: absorb the impact, then try a shallow detour using the same
        # silhouette test.  Only small heading changes are attempted so cars
        # never teleport across walls.  While still recoiling from a recent
        # impact we merely bleed off speed instead of re-triggering the whole
        # reaction (and its steering jitter) every frame.
        if self.collision_recoil <= 0.0:
            self.register_collision(speed, frame_scale)
        else:
            self.current_speed *= 0.45 ** frame_scale
            self.speed = self.current_speed
            self.collision_recoil = max(0.0, self.collision_recoil - frame_scale)
        original_angle = self.angle
        base_heading = original_angle if heading is None else heading
        for offset, scale in ((10.0, 0.60), (-10.0, 0.60), (20.0, 0.35), (-20.0, 0.35)):
            self.angle = (base_heading + offset) % 360
            alt_forward = _forward(self.angle)
            alt = self.pos + alt_forward * max(abs(speed) * scale, 0.4) * frame_scale
            if can_move_to(self, alt, obstacles, col_mask):
                self.pos = alt
                self.current_speed = max(0.4, abs(speed) * scale)
                self.speed = self.current_speed
                self._clear_collision_state(frame_scale)
                return True
        self.angle = original_angle
        self.current_speed *= 0.5 ** frame_scale
        self.speed = self.current_speed
        return False

    # -- main update --------------------------------------------------------

    def _has_vehicle_ahead(self, other_traffic, player_car):
        forward = _forward(self.angle)
        for other in [*other_traffic, player_car]:
            if other is None or other is self or not getattr(other, "is_alive", True):
                continue
            distance = self.pos.distance_to(other.pos)
            if distance < 165 and (distance == 0 or forward.dot((other.pos - self.pos).normalize()) > 0.8):
                return True
        return False

    def update(self, col_mask, player_car, other_traffic, _traffic_state, frame_scale=1.0,
               weather_grip=None):
        if not self.is_alive:
            self.death_timer = max(0.0, self.death_timer - frame_scale)
            return
        if self.is_arrested:
            self.current_speed = self.speed = 0
            self.horn_pause_timer = 0
            self.arrest_timer -= frame_scale
            if self.arrest_timer <= 0:
                self.is_arrested = False
            return
        if self._pause_for_horn(frame_scale):
            return

        frame_scale = max(0.0, float(frame_scale))
        if frame_scale <= 0:
            return
        grip = _resolve_grip(self, weather_grip, _traffic_state)
        obstacles = _collect_obstacles(player_car, other_traffic)

        distance_to_node, angle_diff = _route_heading(self)
        lookahead = _lookahead_distance(self.current_speed, grip)
        wall_clear = _probe_wall_distance(self, self.angle, lookahead, col_mask)
        vehicle_gap = _vehicle_ahead_gap(self, obstacles)

        # Cruise, then yield to the vehicle in front and to walls.
        target_speed = self.max_speed * self.cruise_factor
        if math.isfinite(vehicle_gap):
            target_speed = min(target_speed, _clamp(vehicle_gap * 0.20, 0.0, self.max_speed))
        if wall_clear < lookahead:
            target_speed = min(target_speed, _clamp((wall_clear - 12.0) * 0.22, 0.0, self.max_speed))
        # Slow down before a junction so the car can actually make the turn.
        if abs(angle_diff) > _TURN_START_DEGREES:
            target_speed = min(
                target_speed,
                self.max_speed * _clamp(1.0 - abs(angle_diff) / 120.0, 0.22, 1.0),
            )
        if distance_to_node < _NODE_APPROACH_RADIUS and abs(angle_diff) > 40.0:
            target_speed = min(target_speed, max(_kmh_to_speed(14.0), distance_to_node * 0.05))
        if self.collision_recoil > 0:
            target_speed = min(target_speed, _kmh_to_speed(18.0))

        emergency = (
            (wall_clear < 30.0 and _speed_to_kmh(self.current_speed) > 30.0)
            or (math.isfinite(vehicle_gap) and vehicle_gap < 18.0
                and _speed_to_kmh(self.current_speed) > 25.0)
        )
        self.current_speed = _control_speed(
            self.current_speed, target_speed, grip, frame_scale, emergency
        )

        # Steer toward the route, avoiding a wall when one side is clearly open.
        route_angle = self.angle + angle_diff
        desired_angle = route_angle
        if wall_clear < lookahead:
            desired_angle = _wall_avoidance_angle(
                self, route_angle, wall_clear, lookahead, col_mask
            )
        turn_rate = _effective_turn_rate(self, grip) * frame_scale
        self.angle = (self.angle + _clamp(_angle_delta(desired_angle, self.angle),
                                          -turn_rate, turn_rate)) % 360

        self._advance(obstacles, col_mask, frame_scale, heading=desired_angle)

        blocked = (
            (math.isfinite(vehicle_gap) and vehicle_gap < 24.0)
            or wall_clear < 26.0
        )
        if blocked:
            self.stuck_timer += frame_scale
            if self.stuck_timer > 40 and random.random() < 1 - (1 - 0.02) ** frame_scale:
                self.play_horn(player_car)
        else:
            self.stuck_timer = 0

        self.speed = self.current_speed
        self.image = get_rotated_resources(self.angle)
        if distance_to_node < 45:
            self.target_node = random.choice(TRAFFIC_NODES[self.target_node]["next"])

    def _pause_for_horn(self, frame_scale):
        if self.horn_pause_timer <= 0:
            return False
        self.horn_pause_timer = max(0.0, self.horn_pause_timer - frame_scale)
        self.current_speed = self.speed = 0
        return True

    def play_horn(self, player_car):
        if beep_sound is None or player_car is None:
            return
        distance = self.pos.distance_to(player_car.pos)
        if distance < 1500 and _npc_volume > 0:
            volume = (1.0 - distance / 1500) ** 2 * 0.4 * _npc_volume
            beep_sound.set_volume(volume)
            beep_sound.play()

    def draw(self, screen, off_x, off_y):
        if not self.is_alive and self.death_timer <= 0:
            return
        draw_pos = (self.pos.x + off_x, self.pos.y + off_y)
        if not self.is_alive:
            pygame.draw.ellipse(
                screen,
                (105, 18, 22),
                pygame.Rect(round(draw_pos[0] - 22), round(draw_pos[1] - 10), 44, 20),
            )
            pygame.draw.circle(screen, (150, 25, 28), (round(draw_pos[0]), round(draw_pos[1])), 7)
            return
        screen.blit(self.image, self.image.get_rect(center=draw_pos))

    def take_damage(self, amount: float) -> None:
        if not self.is_alive:
            return
        self.health = max(0.0, self.health - max(0.0, amount))
        if self.health <= 0:
            self.is_alive = False
            self.death_timer = 600.0
            self.current_speed = self.speed = 0.0
            self.just_hit = False


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
        self.vehicle_class = "pursuit"
        self.target_car = None
        self.state = "patrol"
        # 72-92 km/h: fast enough to close a chase, still below the tuned car.
        self.max_speed = _kmh_to_speed(random.uniform(72.0, 92.0))
        self.rotation_speed = 5.0
        self.image = get_rotated_police_resources(self.angle)

    def _find_target(self, other_traffic):
        candidates = [
            car for car in other_traffic
            if car is not None
            and car is not self
            and not getattr(car, "is_police", False)
            and getattr(car, "is_alive", True)
            and not getattr(car, "is_arrested", False)
        ]
        if not candidates:
            return None
        target = min(candidates, key=lambda car: self.pos.distance_squared_to(car.pos))
        return target if self.pos.distance_to(target.pos) < 260 else None

    def _move_toward(self, target_pos, speed, obstacles, col_mask, turn_rate, frame_scale=1.0,
                     weather_grip=None):
        vector = target_pos - self.pos
        if vector.length_squared() == 0:
            return False
        grip = _resolve_grip(self, weather_grip)
        desired_angle = math.degrees(math.atan2(vector.y, vector.x)) + 180
        difference = _angle_delta(desired_angle, self.angle)
        turn = max(_MIN_TURN_RATE, turn_rate * (0.45 + 0.55 * grip)) * frame_scale
        self.angle = (self.angle + _clamp(difference, -turn, turn)) % 360
        self.current_speed = _control_speed(
            self.current_speed, max(0.0, speed), grip, frame_scale
        )
        self.speed = self.current_speed
        return self._advance(obstacles, col_mask, frame_scale, heading=desired_angle)

    def update(self, col_mask, player_car, other_traffic, _traffic_state, frame_scale=1.0,
               weather_grip=None):
        if not self.is_alive:
            # Match TrafficCar: run the wreck's death animation down so the
            # respawn sweep can retire it at the right time.
            self.death_timer = max(0.0, self.death_timer - frame_scale)
            return
        if self.is_arrested:
            self.current_speed = self.speed = 0
            self.horn_pause_timer = 0
            self.arrest_timer -= frame_scale
            if self.arrest_timer <= 0:
                self.is_arrested = False
            return
        if self.state != "stopping" and self._pause_for_horn(frame_scale):
            return

        grip = _resolve_grip(self, weather_grip, _traffic_state)
        obstacles = _collect_obstacles(player_car, other_traffic)

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
                    frame_scale,
                    weather_grip=grip,
                )
            self.target_car = self._find_target(other_traffic or ())
            if self.target_car is not None:
                self.state = "chasing"

        elif self.state == "chasing":
            target = self.target_car
            if target is None or not getattr(target, "is_alive", True) or getattr(target, "is_arrested", False):
                self.target_car = None
                self.state = "patrol"
            else:
                distance = self.pos.distance_to(target.pos)
                # Stop just before the visible vehicle sprites can touch.
                if distance <= _safe_stopping_distance(self, target):
                    self.state = "stopping"
                else:
                    self._move_toward(
                        target.pos, self.max_speed + 0.5, obstacles, col_mask,
                        4.5, frame_scale, weather_grip=grip,
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
            self.current_speed = 0.0
            self.target_car = None
            self.state = "patrol"

        self.speed = self.current_speed
        self.image = get_rotated_police_resources(self.angle)


def analyze_traffic_jams(_cars):
    return []


def respond_to_horn(cars, position, radius=500, pause_frames=45):
    """Briefly yield nearby traffic without changing its route or police state."""
    position = pygame.Vector2(position)
    radius_squared = radius * radius
    for car in cars:
        if (
            not getattr(car, "is_alive", True)
            or getattr(car, "is_arrested", False)
            or getattr(car, "state", None) == "stopping"
            or car.pos.distance_squared_to(position) > radius_squared
        ):
            continue
        car.horn_pause_timer = max(car.horn_pause_timer, pause_frames)


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
