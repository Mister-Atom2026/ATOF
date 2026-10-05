import pygame
import math
import random

# --- КЕШУВАННЯ ---
image_cache = {}
base_traffic_img = None
beep_sound = None


def get_rotated_resources(angle):
    global base_traffic_img
    angle_int = int(angle % 360)
    if angle_int not in image_cache:
        if base_traffic_img is None:
            try:
                img = pygame.image.load("cars/ntk/ntk-2107_classic.png").convert_alpha()
                base_traffic_img = pygame.transform.scale(img, (96, 39))
            except (pygame.error, FileNotFoundError):
                base_traffic_img = pygame.Surface((96, 39), pygame.SRCALPHA)
                base_traffic_img.fill((200, 50, 50))
        image_cache[angle_int] = pygame.transform.rotate(base_traffic_img, -angle_int)
    return image_cache[angle_int]


# --- КООРДИНАТИ (Вузли) ---
TRAFFIC_NODES = {
    "A": {"pos": (7713, 6680), "next": ["B"]}, "B": {"pos": (11835, 6680), "next": ["C", "G"]},
    "C": {"pos": (11835, 7526), "next": ["D", "E"]}, "D": {"pos": (7713, 7526), "next": ["A"]},
    "E": {"pos": (11835, 8791), "next": ["F"]}, "F": {"pos": (7713, 8791), "next": ["D"]},
    "G": {"pos": (12001, 5332), "next": ["H"]}, "H": {"pos": (15116, 5342), "next": ["I"]},
    "I": {"pos": (15087, 6722), "next": ["K"]}, "K": {"pos": (13417, 6737), "next": ["L"]},
    "L": {"pos": (13391, 10383), "next": ["M"]}, "M": {"pos": (7333, 10381), "next": ["N"]},
    "N": {"pos": (7334, 6891), "next": ["A"]}, "A1": {"pos": (7660, 6464), "next": ["B1"]},
    "B1": {"pos": (7568, 7742), "next": ["C1", "E1"]}, "C1": {"pos": (12011, 7717), "next": ["D1"]},
    "D1": {"pos": (11975, 6454), "next": ["A1"]}, "E1": {"pos": (7584, 8999), "next": ["F1"]},
    "F1": {"pos": (11962, 8990), "next": ["C1"]}
}


class TrafficCar:
    def __init__(self, start_node_id, bot_id):
        self.id = bot_id
        node_data = TRAFFIC_NODES[start_node_id]
        self.pos = pygame.Vector2(node_data["pos"])
        self.target_node = random.choice(node_data["next"])

        target_pos = pygame.Vector2(TRAFFIC_NODES[self.target_node]["pos"])
        diff_vec = target_pos - self.pos
        self.angle = math.degrees(math.atan2(diff_vec.y, diff_vec.x)) + 180

        self.max_speed = random.uniform(3.5, 4.2)
        self.current_speed = 0
        self.rotation_speed = 4.0
        self.stuck_timer = 0
        self.image = get_rotated_resources(self.angle)

        global beep_sound
        if beep_sound is None:
            try:
                beep_sound = pygame.mixer.Sound("sounds/beep.wav")
            except:
                pass

    def play_horn(self, player_car):
        if beep_sound:
            dist = self.pos.distance_to(player_car.pos)
            if dist < 1500:
                vol = (1.0 - (dist / 1500)) ** 2 * 0.4
                beep_sound.set_volume(max(0.01, vol))
                beep_sound.play()

    def update(self, _mask, player_car, other_traffic, traffic_state):
        # 1. ЦІЛЬ
        target_pos = pygame.Vector2(TRAFFIC_NODES[self.target_node]["pos"])
        vec_to_target = target_pos - self.pos
        dist_to_node = vec_to_target.length()

        # 2. ПЕРЕВІРКА ПЕРЕШКОД
        too_close = False
        forward_vec = pygame.Vector2(1, 0).rotate(self.angle + 180)

        # Перевірка на інших ботів
        for other in other_traffic:
            if other.id == self.id: continue
            dist = self.pos.distance_to(other.pos)
            if dist < 165:
                if dist == 0 or forward_vec.dot((other.pos - self.pos).normalize()) > 0.8:
                    too_close = True
                    break

        # Перевірка на гравця
        if not too_close:
            dist_p = self.pos.distance_to(player_car.pos)
            if dist_p < 220:
                if dist_p == 0 or forward_vec.dot((player_car.pos - self.pos).normalize()) > 0.6:
                    too_close = True

        # 3. ЛОГІКА РУХУ (Без світлофорів)
        if too_close:
            self.current_speed *= 0.8
            self.stuck_timer += 1
            if self.stuck_timer > 40 and random.random() < 0.02:
                self.play_horn(player_car)
        else:
            self.current_speed = self.max_speed
            self.stuck_timer = 0

        # 4. ФІЗИКА РУХУ
        if self.current_speed > 0.1:
            desired_angle = math.degrees(math.atan2(vec_to_target.y, vec_to_target.x)) + 180
            diff = (desired_angle - self.angle + 180) % 360 - 180

            # Плавно повертаємо
            self.angle += max(-self.rotation_speed, min(self.rotation_speed, diff))
            self.image = get_rotated_resources(self.angle)

            # Їдемо вперед
            self.pos += forward_vec * self.current_speed

        # Перемикання точки
        if dist_to_node < 45:
            self.target_node = random.choice(TRAFFIC_NODES[self.target_node]["next"])

    def draw(self, screen, off_x, off_y):
        draw_pos = (self.pos.x + off_x, self.pos.y + off_y)
        screen.blit(self.image, self.image.get_rect(center=draw_pos))


def analyze_traffic_jams(cars): return []


def init_traffic(count):
    node_ids = list(TRAFFIC_NODES.keys())
    return [TrafficCar(random.choice(node_ids), i) for i in range(count)]