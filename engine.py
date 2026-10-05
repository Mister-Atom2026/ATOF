import pygame
import math
import os
from constants import WIDTH, HEIGHT
from house import HousePlayer
import random
import traffic

_menu_sounds = {}


def play_menu_sound(kind):
    sound_paths = {
        "hover": "menu_hover.wav",
        "click": "menu_click.wav",
    }
    if kind not in sound_paths:
        return
    if kind not in _menu_sounds:
        path = os.path.join(os.path.dirname(__file__), "sounds", sound_paths[kind])
        try:
            _menu_sounds[kind] = pygame.mixer.Sound(path)
            _menu_sounds[kind].set_volume(0.22 if kind == "hover" else 0.38)
        except pygame.error:
            _menu_sounds[kind] = None
    sound = _menu_sounds[kind]
    if sound is not None:
        sound.play()


class Player:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.speed = 2
        self.angle = 0  # 0 градусів — Південь (вниз) за замовчуванням
        self.is_moving = False

        self.original_image = None
        try:
            path = "characters/atom.png"
            if os.path.exists(path):
                raw = pygame.image.load(path).convert_alpha()
                # Збільшуємо 16x16 до 48x48
                self.original_image = pygame.transform.scale(raw, (48, 48))
                self.image = self.original_image
        except:
            print("Не вдалося завантажити atom.png")

    def update(self, keys, col_mask, car_obj=None, npc_cars=None):
        move = pygame.Vector2(0, 0)

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y = -1
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y = 1

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x = -1
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x = 1

        if move.length() > 0:
            self.is_moving = True

            # РЕЖИМ АНТИ-ДЖЕКСОН
            if move.y == 1:
                if move.x == 1:
                    self.angle = -45
                elif move.x == -1:
                    self.angle = 45
                else:
                    self.angle = 0
            elif move.y == -1:
                if move.x == 1:
                    self.angle = -135
                elif move.x == -1:
                    self.angle = 135
                else:
                    self.angle = 180
            elif move.x == 1:
                self.angle = -90
            elif move.x == -1:
                self.angle = 90

            move = move.normalize() * self.speed
            new_pos = self.pos + move

            can_move = True

            # 1. Перевірка маски (стіни)
            try:
                p = col_mask.get_at((int(new_pos.x), int(new_pos.y)))
                if (p[0] > 200 and p[1] < 50 and p[2] < 50):
                    can_move = False
            except:
                can_move = False

            # 2. НОВА КОЛІЗІЯ З ТРАФІКОМ (ЖИГУЛЯМИ)
            if can_move and npc_cars:
                    for npc in npc_cars:
                        dist = new_pos.distance_to(npc.pos)
                        if dist < 45:  # Радіус Жигуля. Якщо менше — Атом впирається
                            can_move = False
                            break
            if car_obj and can_move:
                # Отримуємо вектор від центру машини до нової позиції Атома
                rel_pos = new_pos - car_obj.pos

                # Повертаємо цей вектор на кут машини (скасовуємо поворот для розрахунку)
                # Використовуємо .rotate(car_obj.angle), щоб перевірити точку в локальних координатах машини
                rotated_rel = rel_pos.rotate(car_obj.angle)

                # Тепер машина для нас "рівна". Перевіряємо межі 96x48
                # Половина ширини (96/2) = 48, половина висоти (48/2) = 24
                # Додаємо мінус 2-3 пікселі запасу (45 і 22), щоб Атом не застрягав у кутах
                if abs(rotated_rel.x) < 46 and abs(rotated_rel.y) < 22:
                    can_move = False

            if can_move:
                self.pos = new_pos
        else:
            self.is_moving = False
    def draw(self, screen, offset_x, offset_y):
        if self.image:
            # ДОДАЄМО МІНУС сюди, щоб синхронізувати Pygame з нашою логікою
            rotated = pygame.transform.rotate(self.image, self.angle)

            # Центруємо, щоб не сіпався
            rect = rotated.get_rect(center=(self.pos.x + offset_x, self.pos.y + offset_y))
            screen.blit(rotated, rect)
        else:
            pygame.draw.circle(screen, (255, 200, 0), (int(self.pos.x + offset_x), int(self.pos.y + offset_y)), 15)

class Car:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.angle = 0
        self.speed = 0
        self.max_speed = 15
        self.accel = 0.08
        self.friction = 0.04
        self.brake_force = 0.3

        self.skid_marks = []
        self.just_hit = False

        # --- СИСТЕМА ПОЛОМОК ---
        self.health = 200.0  # Поточне здоров'я
        self.max_health = 200.0
        self.smoke_particles = []
        self.is_broken = False  # Чи заглохла машина
        self.repair_progress = 0  # Прогрес ремонту (0 - 360 кадрів, тобто 6 сек)
        # -----------------------

        self.ui_x = 950
        self.ui_y = 600
        self.ui_radius = 75

        try:
            self.ui_font = pygame.font.Font(None, 20)
        except:
            self.ui_font = pygame.font.SysFont("Arial", 14)

        try:
            self.image = pygame.image.load("cars/tornado/tornado_special.png").convert_alpha()
            self.image = pygame.transform.scale(self.image, (96, 48))
        except:
            self.image = pygame.Surface((96, 48))
            self.image.fill((0, 0, 255))

    def update(self, keys, col_mask, active, npc_cars=None):
        # Якщо машина зламана, вона не реагує на газ
        if self.is_broken:
            active = False
            if abs(self.speed) < 0.1: self.speed = 0

        if not active:
            if abs(self.speed) > 0.1:
                self.speed *= 0.95
            else:
                self.speed = 0
        else:
            # 1. Логіка швидкості
            current_accel = self.accel
            if abs(self.speed) > 10: current_accel = self.accel / 3

            if keys[pygame.K_w] or keys[pygame.K_UP]:
                if self.speed < 0:
                    self.speed += self.brake_force
                else:
                    self.speed = min(self.speed + current_accel, self.max_speed)
            elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
                if self.speed > 0:
                    self.speed -= self.brake_force
                else:
                    self.speed = max(self.speed - current_accel, -self.max_speed / 2)
            else:
                self.speed *= 0.97

            # 2. Логіка повороту
            if abs(self.speed) > 0.5:
                steer = 5.0 - (min(abs(self.speed) / 2, 1.0))
                direction = 1 if self.speed > 0 else -1
                if keys[pygame.K_a] or keys[pygame.K_LEFT]: self.angle += steer * direction
                if keys[pygame.K_d] or keys[pygame.K_RIGHT]: self.angle -= steer * direction

        # 3. Рух та колізія
        velocity = pygame.Vector2(self.speed, 0).rotate(-self.angle + 180)
        next_pos = self.pos + velocity
        # 1. Оновлюємо існуючі частинки диму (вони мають жити, навіть якщо машина стоїть)
        self.update_smoke_particles()  # <-- Ми створимо цей метод нижче

        # 2. Створюємо НОВІ частинки, якщо машина побита
        # Дим йде, тільки якщо здоров'я менше 50%
        if self.health < self.max_health * 0.5:
            # Чим менше здоров'я, тим частіше з'являється дим
            spawn_chance = 10  # Базовий шанс (кожні 10 кадрів)

            # Якщо здоров'я кримінально мале (<20), дим йде майже постійно
            if self.health < self.max_health * 0.2:
                spawn_chance = 2  # Дуже часто

            # Рандом, щоб дим не виглядав як конвеєр
            if pygame.time.get_ticks() % spawn_chance == 0:
                self.create_smoke_particle()  # <-- Ми створимо цей метод нижче

        def check_at_pos(test_pos):
            if npc_cars:
                for npc in npc_cars:
                    # Якщо Торнадо під'їжджає близько до Жигуля
                    if test_pos.distance_to(npc.pos) < 95:  # Відстань для реакції
                        # Створюємо rect для перевірки зіткнення прямокутників
                        my_rect = self.image.get_rect(center=test_pos)
                        # npc.image.get_rect(center=npc.pos) - це прямокутник Жигуля
                        if my_rect.colliderect(npc.image.get_rect(center=npc.pos)):
                            return True  # Торнадо бачить Жигуль як перешкоду
            w, h = 45, 22
            points = [
                test_pos + pygame.Vector2(w, h).rotate(-self.angle + 180),
                test_pos + pygame.Vector2(w, -h).rotate(-self.angle + 180),
                test_pos + pygame.Vector2(-w, h).rotate(-self.angle + 180),
                test_pos + pygame.Vector2(-w, -h).rotate(-self.angle + 180),
                test_pos + pygame.Vector2(w, 0).rotate(-self.angle + 180),
                test_pos + pygame.Vector2(-w, 0).rotate(-self.angle + 180)
            ]
            for pt in points:
                try:
                    p = col_mask.get_at((int(pt.x), int(pt.y)))
                    if (p[0] > 200 and p[1] < 50 and p[2] < 50) or (p[0] < 50 and p[1] < 50 and p[2] < 50):
                        return True
                except:
                    return True
            return False

        if check_at_pos(next_pos):
            # --- ЛОГІКА ПОШКОДЖЕНЬ ---
            impact_speed = abs(self.speed)
            if impact_speed > 1.5:
                self.just_hit = True
                # Шкода залежить від швидкості: чим швидше, тим болючіше
                damage = impact_speed * 2
                self.health -= damage
                if self.health <= 0:
                    self.health = 0
                    self.is_broken = True
            # -------------------------

            self.speed = -self.speed * 0.6
            if velocity.length() > 0:
                self.pos -= velocity.normalize() * 5
        else:
            old_pos = pygame.Vector2(self.pos.x, self.pos.y)
            self.pos = next_pos

            # Сліди шин
            is_braking = active and ((keys[pygame.K_s] and self.speed > 2) or (keys[pygame.K_w] and self.speed < -2))
            if is_braking:
                forward_vec = pygame.Vector2(1, 0).rotate(-self.angle + 180)
                off_l = pygame.Vector2(0, 16).rotate(-self.angle + 180)
                off_r = pygame.Vector2(0, -16).rotate(-self.angle + 180)
                back_axle = forward_vec * 35
                p1_l, p1_r = (old_pos - back_axle) + off_l, (old_pos - back_axle) + off_r
                p2_l, p2_r = (self.pos - back_axle) + off_l, (self.pos - back_axle) + off_r
                self.skid_marks.append((p1_l, p2_l, p1_r, p2_r))
                if len(self.skid_marks) > 60: self.skid_marks.pop(0)

    def create_smoke_particle(self):
        """Створює одну частинку диму в центрі машини."""
        # Тепер дим йде просто з позиції машини
        spawn_x = self.pos.x + random.randint(-5, 5)
        spawn_y = self.pos.y + random.randint(-5, 5)

        # Решта коду залишається такою ж
        color_val = 150  # Сірий
        if self.health < self.max_health * 0.2:
            color_val = 50  # Чорний

        particle = [
            spawn_x,  # 0: x
            spawn_y,  # 1: y
            random.randint(5, 10),  # 2: радіус
            random.randint(150, 200),  # 3: alpha
            random.uniform(1.0, 2.5),  # 4: швидкість вгору
            random.randint(40, 70)  # 5: життя
        ]
        self.smoke_particles.append(particle)
    def update_smoke_particles(self):
        """Оновлює стан усіх існуючих частинок диму."""
        for p in self.smoke_particles[:]:
            p[1] -= p[4]  # Підіймається вгору (змінюємо y)
            p[2] += 0.3  # Радіус збільшується (розширюється)
            p[3] -= 3  # Прозорість зменшується (alpha)
            p[5] -= 1  # Зменшуємо час життя

            # Якщо прозорість стала <=0 або час життя вийшов, видаляємо
            if p[3] <= 0 or p[5] <= 0:
                self.smoke_particles.remove(p)
    def draw(self, screen, offset_x, offset_y):
        for p1l, p2l, p1r, p2r in self.skid_marks:
            pygame.draw.line(screen, (45, 45, 45), (p1l.x + offset_x, p1l.y + offset_y),
                             (p2l.x + offset_x, p2l.y + offset_y), 5)
            pygame.draw.line(screen, (45, 45, 45), (p1r.x + offset_x, p1r.y + offset_y),
                             (p2r.x + offset_x, p2r.y + offset_y), 5)

        rotated = pygame.transform.rotate(self.image, self.angle)
        rect = rotated.get_rect(center=(self.pos.x + offset_x, self.pos.y + offset_y))

        # Якщо здоров'я менше 30%, можна додати ефект вібрації або легкого диму (опціонально)
        screen.blit(rotated, rect)

    def draw_speedometer(self, screen):
        center = (self.ui_x, self.ui_y)
        r = self.ui_radius

        # Малюємо смужку здоров'я НАД спідометром
        bar_width = 100
        bar_height = 10
        bar_x = center[0] - bar_width // 2
        bar_y = center[1] - r - 30

        # Колір змінюється від зеленого до червоного
        hp_ratio = self.health / self.max_health
        hp_color = (int(255 * (1 - hp_ratio)), int(255 * hp_ratio), 0)

        # Фон смужки (сірий)
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
        # Поточне здоров'я
        pygame.draw.rect(screen, hp_color, (bar_x, bar_y, int(bar_width * hp_ratio), bar_height))
        # Рамка
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, bar_width, bar_height), 1)

        # Решта коду спідометра...
        pygame.draw.circle(screen, (20, 20, 20), center, r + 5)
        pygame.draw.circle(screen, (0, 0, 0), center, r)

        speed_labels = [0, 20, 40, 60, 80, 100, 120]
        for km in speed_labels:
            val_norm = km / 120
            angle_deg = -225 + val_norm * 270
            rad = math.radians(angle_deg)
            p1 = (center[0] + math.cos(rad) * (r * 0.85), center[1] + math.sin(rad) * (r * 0.85))
            p2 = (center[0] + math.cos(rad) * r, center[1] + math.sin(rad) * r)
            pygame.draw.line(screen, (255, 255, 255), p1, p2, 2)
            text_pos = (center[0] + math.cos(rad) * (r * 0.65), center[1] + math.sin(rad) * (r * 0.65))
            txt = self.ui_font.render(str(km), True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=text_pos))

        current_kmh = abs(self.speed) * 8
        val = min(current_kmh / 120, 1.0)
        angle_rad = math.radians(-225 + val * 270)
        target = (center[0] + math.cos(angle_rad) * (r * 0.8), center[1] + math.sin(angle_rad) * (r * 0.8))
        pygame.draw.line(screen, (255, 0, 0), center, target, 4)
        pygame.draw.circle(screen, (150, 0, 0), center, 8)

def draw_atom_character(ctx, x, y, atom_tex, angle):
    """Малює Атома з правильним поворотом текстури."""
    rotated_atom = pygame.transform.rotate(atom_tex, -angle)
    rect = rotated_atom.get_rect(center=(int(x), int(y)))
    ctx.blit(rotated_atom, rect)


def draw_debug_coords(screen, target, map_scale):
    """Виводить технічну інформацію на екран."""
    if not target: return

    debug_f = pygame.font.SysFont("Consolas", 20, bold=True)

    # Визначаємо координати (враховуємо, що у Player це .pos, а у Car теж .pos)
    try:
        curr_x = int(target.pos.x)
        curr_y = int(target.pos.y)
    except AttributeError:
        # Якщо раптом передав об'єкт без pos
        curr_x, curr_y = 0, 0

    coords_text = f"X: {curr_x} Y: {curr_y} | MODE: {map_scale}"

    # Малюємо підкладку для тексту, щоб його було видно на будь-якому фоні
    txt_surf = debug_f.render(coords_text, True, (255, 255, 0))
    bg_rect = pygame.Rect(10, 10, txt_surf.get_width() + 10, 30)

    # Створюємо напівпрозорий фон
    bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
    bg_surf.fill((0, 0, 0, 180))

    screen.blit(bg_surf, (10, 10))
    screen.blit(txt_surf, (15, 15))


def draw_gta_minimap(screen, bg_img, target, world_w, world_h, house_pos=(7738, 2325)):
    """Малює міні-карту, яка зупиняється на межах світу."""

    # Розумне завантаження іконки (тільки один раз)
    if not hasattr(draw_gta_minimap, "haus_icon"):
        try:
            draw_gta_minimap.haus_icon = pygame.image.load("ch_home/haus.png").convert_alpha()
        except:
            draw_gta_minimap.haus_icon = None

    size, margin = 200, 30
    WIDTH, HEIGHT = screen.get_size()
    x, y = WIDTH - size - margin, HEIGHT - size - margin

    # Створюємо прозору поверхню для карти
    mini_surf = pygame.Surface((size, size), pygame.SRCALPHA)

    zoom = 0.1
    # Розраховуємо масштаби один раз
    map_scale_x = bg_img.get_width() * (size / (bg_img.get_width() * zoom))
    map_scale_y = bg_img.get_height() * (size / (bg_img.get_height() * zoom))

    # Коефіцієнти переведення координат
    ratio_x = map_scale_x / world_w
    ratio_y = map_scale_y / world_h

    # --- ГОЛОВНА ЛОГІКА ОБМЕЖЕННЯ ---
    # Скільки "пікселів карти" вміщується від центру до краю мінікарти
    half_size = size // 2

    # Обмежуємо координати центру камери мінікарти (щоб не бачити чорне)
    # Камера не може підійти до краю ближче ніж на half_size
    cam_x = max(half_size, min(target.pos.x * ratio_x, map_scale_x - half_size))
    cam_y = max(half_size, min(target.pos.y * ratio_y, map_scale_y - half_size))

    # Зміщення для малювання фону (відносно зафіксованої камери)
    ox = -cam_x + half_size
    oy = -cam_y + half_size

    # Рендер фону
    temp = pygame.transform.scale(bg_img, (int(map_scale_x), int(map_scale_y)))
    mini_surf.blit(temp, (ox, oy))

    # Позначка будинку
    hx = (house_pos[0] * ratio_x) + ox
    hy = (house_pos[1] * ratio_y) + oy

    if draw_gta_minimap.haus_icon:
        icon_mini = pygame.transform.scale(draw_gta_minimap.haus_icon, (20, 20))
        mini_surf.blit(icon_mini, (int(hx) - 10, int(hy) - 10))
    else:
        pygame.draw.circle(mini_surf, (0, 0, 255), (int(hx), int(hy)), 5)

    # Позначка гравця (тепер вона може відходити від центру, якщо ми біля межі)
    px = (target.pos.x * ratio_x) + ox
    py = (target.pos.y * ratio_y) + oy

    # Малюємо маркер гравця прямо на mini_surf
    pygame.draw.circle(mini_surf, (255, 0, 0), (int(px), int(py)), 6)
    pygame.draw.circle(mini_surf, (255, 255, 255), (int(px), int(py)), 6, 2)

    # Кругла маска (щоб обрізати краї карти в коло)
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (half_size, half_size), half_size)
    mini_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    # Вивід на основний екран
    # Рамка
    pygame.draw.circle(screen, (255, 255, 255), (x + half_size, y + half_size), half_size + 3, 3)
    # Карта
    screen.blit(mini_surf, (x, y))

def stats_dialog(screen, font, small_font, t, stats=None, controls=None):
    stats = stats or {}
    clock = pygame.time.Clock()
    last_hovered = False
    width, height = screen.get_size()
    back_rect = pygame.Rect(width // 2 - 120, height - 150, 240, 56)

    while True:
        screen.fill((14, 14, 20))
        title = font.render(t.get("stats_title", "Stats"), True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(width // 2, 125)))

        lines = [
            t.get("stats_money", "Money: {money}").format(money=stats.get("money", 0)),
            t.get("stats_time", "Time: {time}").format(time=stats.get("time", "00:00")),
            t.get("stats_treasures", "Treasures: {treasures}").format(
                treasures=stats.get("treasures", 0)
            ),
            t.get("stats_traffic", "Traffic: {traffic}").format(
                traffic=stats.get("traffic", 0), police=stats.get("police", 0)
            ),
        ]
        for index, line in enumerate(lines):
            rendered = small_font.render(line, True, (220, 220, 220))
            screen.blit(rendered, rendered.get_rect(center=(width // 2, 230 + index * 54)))

        mouse_pos = pygame.mouse.get_pos()
        hovered = back_rect.collidepoint(mouse_pos)
        if hovered and not last_hovered:
            play_menu_sound("hover")
        last_hovered = hovered
        color = (212, 91, 18) if hovered else (70, 70, 70)
        pygame.draw.rect(screen, color, back_rect, border_radius=8)
        back_text = small_font.render(t.get("back", "Back"), True, (255, 255, 255))
        screen.blit(back_text, back_text.get_rect(center=back_rect.center))
        hint = small_font.render(t.get("stats_hint", "Press Esc or Enter to return"), True, (150, 150, 150))
        screen.blit(hint, hint.get_rect(center=(width // 2, height - 55)))
        pygame.display.flip()

        for event in pygame.event.get():
            if controls is not None:
                controls.process_event(event)
            if event.type == pygame.QUIT:
                return "EXIT"
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                play_menu_sound("click")
                return "BACK"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and back_rect.collidepoint(event.pos):
                play_menu_sound("click")
                return "BACK"
        clock.tick(60)


def pause_menu(screen, font, small_font, settings, trans_dict, languages, controls=None, stats=None):
    pygame.mouse.set_visible(True)
    sel = 0
    W, H = screen.get_size()
    clock = pygame.time.Clock()
    last_hovered = None

    while True:
        t = trans_dict[languages[settings['lang_idx']]]
        options = [t["resume"], t["stats"], t["settings"], t["menu"]]

        screen.fill((0, 0, 0))
        m_pos = pygame.mouse.get_pos()
        rects = [pygame.Rect(50, 200 + i * 100, 500, 60) for i in range(len(options))]

        for event in pygame.event.get():
            if controls is not None:
                controls.process_event(event)
            if event.type == pygame.QUIT: return "EXIT"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    play_menu_sound("click")
                    return "CONTINUE"
                if event.key == pygame.K_UP:
                    sel = (sel - 1) % len(options)
                    play_menu_sound("hover")
                if event.key == pygame.K_DOWN:
                    sel = (sel + 1) % len(options)
                    play_menu_sound("hover")
                if event.key == pygame.K_RETURN:
                    play_menu_sound("click")
                    if sel == 0: return "CONTINUE"
                    if sel == 1:
                        if stats_dialog(screen, font, small_font, t, stats, controls) == "EXIT": return "EXIT"
                    if sel == 2: settings_sub_menu(screen, font, settings, trans_dict, languages, controls)
                    if sel == 3:
                        if confirm_dialog(screen, font, small_font, t, controls): return "MENU"

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, r in enumerate(rects):
                    if r.collidepoint(event.pos):
                        play_menu_sound("click")
                        if i == 0: return "CONTINUE"
                        if i == 1:
                            if stats_dialog(screen, font, small_font, t, stats, controls) == "EXIT": return "EXIT"
                        if i == 2: settings_sub_menu(screen, font, settings, trans_dict, languages, controls)
                        if i == 3:
                            if confirm_dialog(screen, font, small_font, t, controls): return "MENU"

        for i, opt in enumerate(options):
            if rects[i].collidepoint(m_pos):
                if last_hovered != i:
                    play_menu_sound("hover")
                last_hovered = i
                sel = i
            color = (212, 91, 18) if i == sel else (255, 255, 255)
            txt = font.render(opt, True, color)
            screen.blit(txt, (50, 200 + i * 100))
        if not any(rect.collidepoint(m_pos) for rect in rects):
            last_hovered = None

        pygame.display.flip()
        clock.tick(60)


def settings_sub_menu(screen, font, settings, trans_dict, languages, controls=None):
    sel = 0
    clock = pygame.time.Clock()
    COLOR_ORANGE = (212, 91, 18)
    COLOR_WHITE = (255, 255, 255)
    # --- МАГІЧНИЙ ФІКС ---
    # Визначаємо поточну мову
    lang_name = languages[settings['lang_idx']]
    t = trans_dict[lang_name]

    # Якщо якимось дивом ключів немає, ми їх створюємо силоміць
    if 'vol' not in t: t['vol'] = "Volume" if lang_name == "English" else "Гучність"
    if 'lang' not in t: t['lang'] = "Language" if lang_name == "English" else "Мова"
    if 'back' not in t: t['back'] = "Back" if lang_name == "English" else "Назад"
    # ---------------------
    last_hovered = None
    while True:
        # 1. Отримуємо словник для поточної мови
        raw_t = trans_dict[languages[settings['lang_idx']]]

        # 2. Використовуємо .get(), щоб ніколи не вилітало, навіть якщо ключів немає
        vol_txt = raw_t.get('vol', 'Volume' if settings['lang_idx'] == 0 else 'Гучність')
        lang_txt = raw_t.get('lang', 'Language' if settings['lang_idx'] == 0 else 'Мова')
        back_txt = raw_t.get('back', 'Back' if settings['lang_idx'] == 0 else 'Назад')

        # 3. Формуємо список опцій
        opts = [
            f"{vol_txt}: < {settings['volume']}% >",
            f"{lang_txt}: < {languages[settings['lang_idx']]} >",
            back_txt
        ]

        screen.fill((20, 20, 20))
        # ... далі твій код без змін
        m_pos = pygame.mouse.get_pos()

        # Створюємо ректи (використовуємо 700, як у головному меню, для стабільності)
        rects = [pygame.Rect(50, 250 + i * 100, 700, 70) for i in range(len(opts))]

        for event in pygame.event.get():
            if controls is not None:
                controls.process_event(event)
            if event.type == pygame.QUIT: return

            # --- КЛАВІАТУРА ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    play_menu_sound("click")
                    return
                if event.key == pygame.K_UP:
                    sel = (sel - 1) % len(opts)
                    play_menu_sound("hover")
                if event.key == pygame.K_DOWN:
                    sel = (sel + 1) % len(opts)
                    play_menu_sound("hover")

                if sel == 0:
                    if event.key == pygame.K_RIGHT:
                        settings['volume'] = min(100, settings['volume'] + 5)
                        play_menu_sound("click")
                    if event.key == pygame.K_LEFT:
                        settings['volume'] = max(0, settings['volume'] - 5)
                        play_menu_sound("click")
                elif sel == 1:
                    if event.key == pygame.K_RIGHT:
                        settings['lang_idx'] = (settings['lang_idx'] + 1) % len(languages)
                        play_menu_sound("click")
                    if event.key == pygame.K_LEFT:
                        settings['lang_idx'] = (settings['lang_idx'] - 1) % len(languages)
                        play_menu_sound("click")
                elif sel == 2 and event.key == pygame.K_RETURN:
                    play_menu_sound("click")
                    return

                pygame.mixer.music.set_volume(settings['volume'] / 100)

            # --- МИША ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, r in enumerate(rects):
                    if r.collidepoint(event.pos):
                        play_menu_sound("click")
                        if i == 0:  # ГУЧНІСТЬ
                            # Текст починається на 50.
                            # Слово "Гучність" закінчується десь на 200-250.
                            # Якщо клікаємо ближче до початку (ліворуч) — зменшуємо.
                            # Якщо далі (там де цифри) — збільшуємо.

                            if event.pos[0] < 250:
                                settings['volume'] = max(0, settings['volume'] - 5)
                                print("Клік вліво (МЕНШЕ)")  # Для відладки
                            else:
                                settings['volume'] = min(100, settings['volume'] + 5)
                                print("Клік вправо (БІЛЬШЕ)")  # Для відладки

                            pygame.mixer.music.set_volume(settings['volume'] / 100)

                        elif i == 1:  # МОВА
                            settings['lang_idx'] = (settings['lang_idx'] + 1) % len(languages)

                        elif i == 2:  # НАЗАД
                            return

        # --- МАЛЮВАННЯ ---
        for i, text in enumerate(opts):
            # Якщо миша над прямокутником — цей пункт стає вибраним (sel)
            if rects[i].collidepoint(m_pos):
                if last_hovered != i:
                    play_menu_sound("hover")
                last_hovered = i
                sel = i

            color = COLOR_ORANGE if i == sel else COLOR_WHITE
            surf = font.render(text, True, color)
            screen.blit(surf, (50, 250 + i * 100))
        if not any(rect.collidepoint(m_pos) for rect in rects):
            last_hovered = None

        pygame.display.flip()
        clock.tick(60)


def confirm_dialog(screen, font, small_font, t, controls=None):
    # Невелика пауза для стабільності
    pygame.time.delay(150)

    q_txt = t.get("confirm_q", "Вийти?")
    w_txt = t.get("confirm_w", "Дані буде втрачено")

    selected = 1  # 0 - YES, 1 - NO
    clock = pygame.time.Clock()
    pygame.mouse.set_visible(True)
    last_hovered = None

    while True:
        W, H = screen.get_size()
        m_pos = pygame.mouse.get_pos()
        m_click = pygame.mouse.get_pressed()[0]  # Ліва кнопка миші

        # 1. МАЛЮЄМО ВІКНО
        dr = pygame.Rect(W // 2 - 300, H // 2 - 110, 600, 220)
        pygame.draw.rect(screen, (30, 30, 30), dr)
        pygame.draw.rect(screen, (255, 255, 255), dr, 2)

        # 2. ТЕКСТ
        q_surf = font.render(q_txt, True, (255, 255, 255))
        w_surf = small_font.render(w_txt, True, (200, 200, 200))
        screen.blit(q_surf, (W // 2 - q_surf.get_width() // 2, H // 2 - 80))
        screen.blit(w_surf, (W // 2 - w_surf.get_width() // 2, H // 2 - 30))

        # 3. КНОПКИ
        by = pygame.Rect(W // 2 - 130, H // 2 + 40, 100, 50)  # YES
        bn = pygame.Rect(W // 2 + 30, H // 2 + 40, 100, 50)  # NO

        # --- ЛОГІКА МИШІ ---
        hovered = 0 if by.collidepoint(m_pos) else 1 if bn.collidepoint(m_pos) else None
        if hovered != last_hovered:
            if hovered is not None:
                play_menu_sound("hover")
            last_hovered = hovered
        if hovered is not None:
            selected = hovered
            if m_click:
                play_menu_sound("click")
                return selected == 0

        # 4. ВІЗУАЛІЗАЦІЯ ВИБОРУ
        y_col = (0, 200, 0) if selected == 0 else (0, 80, 0)
        n_col = (200, 0, 0) if selected == 1 else (80, 0, 0)

        pygame.draw.rect(screen, y_col, by)
        pygame.draw.rect(screen, n_col, bn)

        # Рамка навколо вибраного елемента
        active_rect = by if selected == 0 else bn
        pygame.draw.rect(screen, (255, 255, 255), active_rect, 3)

        yes_label = small_font.render(t.get("yes", "YES"), True, (255, 255, 255))
        no_label = small_font.render(t.get("no", "NO"), True, (255, 255, 255))
        screen.blit(yes_label, yes_label.get_rect(center=by.center))
        screen.blit(no_label, no_label.get_rect(center=bn.center))

        pygame.display.flip()

        # 5. ІВЕНТИ (КЛАВІАТУРА)
        for event in pygame.event.get():
            if controls is not None:
                controls.process_event(event)
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_LEFT, pygame.K_RIGHT] or (
                    controls is not None and (
                        controls.matches(event, pygame.K_a) or controls.matches(event, pygame.K_d)
                    )
                ):
                    selected = 1 - selected
                    play_menu_sound("hover")
                if event.key == pygame.K_RETURN:
                    play_menu_sound("click")
                    return selected == 0
                if event.key == pygame.K_ESCAPE:
                    play_menu_sound("click")
                    return False

        clock.tick(30)
def toggle_location(self, target_state):
    if target_state == "HOUSE":
        # Створюємо копію Атома для хати
        self.house_atom = HousePlayer(self.house_visual.get_width() // 2,
                                     self.house_visual.get_height() // 2)
        self.state = "HOUSE"
    else:
        self.state = "CITY"
        # Повертаємо координати основного Атома
        self.atom.pos = pygame.Vector2(7738, 2450)


def draw_atom_character(ctx, x, y, atom_tex, angle):
    """Малює Атома з правильним поворотом текстури."""
    # Використовуємо -angle, як у твоєму робочому коді
    rotated_atom = pygame.transform.rotate(atom_tex, -angle)
    rect = rotated_atom.get_rect(center=(int(x), int(y)))
    ctx.blit(rotated_atom, rect)


def draw_debug_coords(screen, target, mode_label):
    """Виводить технічну інформацію на екран (твоя версія)."""
    if not target: return
    try:
        debug_f = pygame.font.SysFont("Consolas", 20, bold=True)
    except:
        debug_f = pygame.font.SysFont("Arial", 20)

    # Універсальна перевірка для різних типів об'єктів
    curr_x = int(target.pos.x)
    curr_y = int(target.pos.y)

    debug_text = f"X: {curr_x} Y: {curr_y} | MODE: {mode_label}"
    txt_surf = debug_f.render(debug_text, True, (255, 255, 0))

    # Підкладка
    bg_rect = pygame.Rect(10, 10, txt_surf.get_width() + 10, 30)
    bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
    bg_surf.fill((0, 0, 0, 180))

    screen.blit(bg_surf, (10, 10))
    screen.blit(txt_surf, (15, 15))


def full_screen_map(screen, map_img, target, world_w, world_h, house_pos=(7738, 2325), controls=None):
    """Твоя реалізація великої карти з зумом та іконками."""
    try:
        haus_icon = pygame.image.load("ch_home/haus.png").convert_alpha()
    except:
        haus_icon = None

    WIDTH, HEIGHT = screen.get_size()
    map_zoom = 1.0
    map_off_x, map_off_y = 0, 0
    clock = pygame.time.Clock()
    running = True

    while running:
        screen.fill((20, 20, 20))
        for event in pygame.event.get():
            if controls is not None:
                controls.process_event(event)
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEWHEEL:
                map_zoom += event.y * 0.1
                map_zoom = max(1.0, min(5.0, map_zoom))
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_TAB, pygame.K_ESCAPE]:
                    running = False

        scaled_w, scaled_h = int(WIDTH * map_zoom), int(HEIGHT * map_zoom)
        keys = controls if controls is not None else pygame.key.get_pressed()
        move_speed = 15 / map_zoom

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:  map_off_x += move_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: map_off_x -= move_speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:    map_off_y += move_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:  map_off_y -= move_speed

        limit_x, limit_y = (scaled_w - WIDTH) // 2, (scaled_h - HEIGHT) // 2
        if limit_x > 0:
            map_off_x = max(-limit_x, min(limit_x, map_off_x))
        else:
            map_off_x = 0
        if limit_y > 0:
            map_off_y = max(-limit_y, min(limit_y, map_off_y))
        else:
            map_off_y = 0

        map_rect = pygame.Rect(0, 0, scaled_w, scaled_h)
        map_rect.center = (WIDTH // 2 + map_off_x, HEIGHT // 2 + map_off_y)

        temp_map = pygame.transform.scale(map_img, (scaled_w, scaled_h))
        screen.blit(temp_map, map_rect.topleft)

        def world_to_map(wx, wy):
            mx = (wx / world_w) * scaled_w + map_rect.left
            my = (wy / world_h) * scaled_h + map_rect.top
            return int(mx), int(my)

        # Іконка будинку
        hx, hy = world_to_map(house_pos[0], house_pos[1])
        if haus_icon:
            i_size = int(24 * map_zoom)
            s_haus = pygame.transform.scale(haus_icon, (i_size, i_size))
            screen.blit(s_haus, (hx - i_size // 2, hy - i_size // 2))
        else:
            pygame.draw.circle(screen, (0, 0, 255), (hx, hy), int(10 * map_zoom))

        # Гравець
        px, py = world_to_map(target.pos.x, target.pos.y)
        pygame.draw.circle(screen, (255, 0, 0), (px, py), int(8 * map_zoom))
        pygame.draw.circle(screen, (255, 255, 255), (px, py), int(8 * map_zoom), 2)

        pygame.display.flip()
        clock.tick(60)

def draw_city_hints(screen, small_font, atom, car, t):
    """Малює підказки біля машини та будинку в місті."""
    dist_car = atom.pos.distance_to(car.pos)
    dist_house = atom.pos.distance_to(pygame.Vector2(7738, 2330))

    if dist_car < 100:
        msg = t["hint"].replace("[E]", "[F]")
        txt = small_font.render(msg, True, (255, 255, 255))
        screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT - 120))

    if dist_house < 80:
        txt = small_font.render(t["enter"], True, (255, 255, 0))
        screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT - 160))

def draw_house_scene(screen, house_visual, house_info, atom_h, small_font, t):
    """Малює сцену всередині будинку та перевіряє зону виходу."""
    screen.fill((10, 10, 10))
    h_rect = house_visual.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(house_visual, h_rect)

    # Малюємо персонажа (відносно центру)
    atom_h.draw(screen, h_rect.x, h_rect.y)

    # Перевірка зони виходу для тексту
    try:
        px, py = int(atom_h.pos.x), int(atom_h.pos.y)
        color_at_feet = house_info.get_at((px, py))[:3]
        if color_at_feet == (153, 229, 80):
            txt = small_font.render(t["exit"], True, (255, 255, 0))
            screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT - 100))
    except:
        pass

def handle_car_logic(atom, car, in_car):
    """Логіка посадки/висадки з авто (клавіша F)."""
    if not in_car and atom.pos.distance_to(car.pos) < 100:
        return True # Стає in_car = True
    elif in_car:
        atom.pos = car.pos + pygame.Vector2(60, 0)
        return False # Стає in_car = False
    return in_car
def check_house_exit(atom_h, house_info):
    try:
        px, py = int(atom_h.pos.x), int(atom_h.pos.y)
        return house_info.get_at((px, py))[:3] == (153, 229, 80)
    except: return False


def handle_surface_footsteps(keys, in_car, game_state, pos, col_mask, sounds, channel):
    # Кроки відтворюються лише якщо натиснуті клавіші руху і ми не в машині
    is_moving = any(keys[k] for k in [
        pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,
        pygame.K_UP, pygame.K_LEFT, pygame.K_DOWN, pygame.K_RIGHT,
    ])

    if not is_moving or in_car:
        channel.stop()
        return

    target_sound = None

    if game_state == "HOUSE":
        target_sound = sounds['house']  # Твій wood

    elif game_state == "CITY":
        try:
            # Читаємо колір пікселя на масці за координатами гравця
            color = col_mask.get_at((int(pos.x), int(pos.y)))[:3]

            if color == (255, 242, 0):  # Жовтий (Асфальт)
                target_sound = sounds['asphalt']
            elif color == (185, 122, 87):  # Коричневий (Ґрунт)
                target_sound = sounds['dirt']
            elif color == (27, 56, 0):  # Зелений (Трава)
                target_sound = sounds['grass']
            else:
                target_sound = sounds['asphalt']  # Стандартний звук
        except:
            pass

    # Відтворюємо звук, якщо він знайдений і канал вільний
    if target_sound and not channel.get_busy():
        channel.play(target_sound)
def handle_car_audio(car, in_car, sounds, e_chan, c_chan, controls=None):
    if not in_car:
        e_chan.stop()
        return

    # 1. Логіка мотора
    if not e_chan.get_busy():
        e_chan.play(sounds['engine'], loops=-1)

    # Міняємо гучність від швидкості
    vol = min(0.6, 0.2 + (abs(car.speed) / 20.0))
    e_chan.set_volume(vol)

    # 2. Логіка сигналу (Гудок)
    keys = controls if controls is not None else pygame.key.get_pressed()
    if keys[pygame.K_h]:
        # Використовуємо окремий канал для сигналу, щоб не перебивати мотор
        # Або просто play(), якщо не боїшся накладання звуків
        if not pygame.mixer.Channel(4).get_busy():
            pygame.mixer.Channel(4).play(sounds['beep'])

    # 3. Логіка удару
    if getattr(car, 'just_hit', False):
        if not c_chan.get_busy():
            c_chan.play(sounds['crash'])
        car.just_hit = False

    # Міняємо гучність від швидкості (чим швидше, тим гучніше)
    vol = min(0.6, 0.2 + (abs(car.speed) / 20.0))
    e_chan.set_volume(vol)

    # 2. Логіка удару
    # Якщо в коді машини car.speed різко падає до 0 при зіткненні:
    if getattr(car, 'just_hit', False):
        if not c_chan.get_busy():
            c_chan.play(sounds['crash'])
        car.just_hit = False # Скидаємо прапорець


def get_ambient_color(game_time_minutes):
    """
    game_time_minutes: час у хвилинах від 0 до 1440.
    Повертає (r, g, b, alpha) для накладання на екран.
    """
    h = game_time_minutes / 60.0

    # День (08:00 - 18:00) -> Прозоро
    if 8 <= h < 18:
        return (0, 0, 0, 0)
    # Ніч (21:00 - 05:00) -> Темно-синій
    elif h >= 21 or h < 5:
        return (15, 15, 40, 160)
    # Сутінки (Ранок/Вечір) -> Плавний перехід
    else:
        if 5 <= h < 8:  # Ранок
            factor = (h - 5) / 3.0
        else:  # Вечір (18:00 - 21:00)
            factor = 1.0 - (h - 18) / 3.0

        # Чим менше factor, тим темніше
        alpha = int(160 * (1.0 - factor))
        return (15, 15, 40, alpha)
def draw_car_smoke(screen, car, off_x, off_y):
    """Малює всі частинки диму машини на екрані з урахуванням зміщення камери."""
    # Для напівпрозорості нам потрібна тимчасова поверхня
    smoke_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    for p in car.smoke_particles:
        x, y, r, alpha, vy, life = p

        # Перетворюємо світові координати в екранні
        screen_x = int(x + off_x)
        screen_y = int(y + off_y)

        # Перевіряємо, чи частинка взагалі на екрані, щоб не малювати зайвого
        if -r < screen_x < WIDTH + r and -r < screen_y < HEIGHT + r:
            # Колір диму (беремо сірий або чорний, який ми задали при створенні)
            # p[0] - x, p[1] - y, p[2] - radius, p[3] - alpha
            # Ми задали колір при створенні, але в структуру не записали.
            # Давай просто визначимо колір тут, на основі початкового p[3].

            # Це трохи костиль, але простіше. Сірий за замовчуванням.
            color_val = 150
            if car.health < car.max_health * 0.2:
                color_val = 50 # Чорний, якщо зовсім погано

            # Малюємо коло на тимчасовій поверхні
            pygame.draw.circle(smoke_surf, (color_val, color_val, color_val, int(alpha)), (screen_x, screen_y), int(r))

    # Блітуємо поверхню з димом на основний екран
    screen.blit(smoke_surf, (0, 0))


import json
import os
import pygame  # Не забудь імпортувати pygame тут


# 1. Робота з пам'яттю телефону
def get_phone_settings():
    path = "phone_settings.json"
    default_settings = {
        "bg_idx": 0,
        "case_idx": 0,
        "owner": "Atom"
    }
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default_settings, f)
        return default_settings
    with open(path, "r") as f:
        return json.load(f)


def save_phone_settings(settings):
    with open("phone_settings.json", "w") as f:
        json.dump(settings, f)


# 2. Палітра кольорів
BG_PALETTE = [(10, 10, 30), (60, 20, 20), (20, 60, 20), (40, 40, 40), (100, 50, 10)]
CASE_PALETTE = [(30, 30, 30), (200, 200, 200), (0, 120, 255), (255, 215, 0), (255, 0, 100)]


# 3. Головна функція малювання
PHONE_TRANSLATIONS = {
    "English": {
        "bank": "Triple1 Bank", "history": "Recent transactions:",
        "start": "Starting balance", "guard": "By the guard", "bridge": "By the bridge",
        "repair": "Repair", "nightstand": "Nightstand", "sofa": "On the sofa",
    },
    "Українська": {
        "bank": "Банк Triple1", "history": "Останні транзакції:",
        "start": "Стартовий баланс", "guard": "Біля охоронця", "bridge": "Коло мосту",
        "repair": "Ремонт", "nightstand": "Тумбочка", "sofa": "На дивані",
    },
    "Русский": {
        "bank": "Банк Triple1", "history": "Последние транзакции:",
        "start": "Стартовый баланс", "guard": "У охранника", "bridge": "У моста",
        "repair": "Ремонт", "nightstand": "Тумбочка", "sofa": "На диване",
    },
}


def draw_mobile_phone(screen, money, game_time, font_small, current_app, phone_settings,
                      phone_y_offset, money_history, language="English"):
    width, height = screen.get_size()
    labels = PHONE_TRANSLATIONS.get(language, PHONE_TRANSLATIONS["English"])
    p_w, p_h = 220, 400

    # Розрахунок позиції телефону (p_y змінюється динамічно)
    p_x = width - p_w - 20
    p_y = height - p_h - 20 + phone_y_offset

    # 1. КОРПУС ТА ЕКРАН
    case_col = CASE_PALETTE[phone_settings["case_idx"]]
    pygame.draw.rect(screen, case_col, (p_x, p_y, p_w, p_h), border_radius=25)

    # Дисплей тепер ЗАВЖДИ прив'язаний до p_y
    display_rect = pygame.Rect(p_x + 10, p_y + 10, p_w - 20, p_h - 20)
    pygame.draw.rect(screen, BG_PALETTE[phone_settings["bg_idx"]], display_rect, border_radius=15)

    # 2. ВЕРХНЯ ПАНЕЛЬ (БАТАРЕЯ ТА СИГНАЛ)
    signal_bars = 4 if 480 < game_time < 1200 else 2
    for i in range(4):
        bar_h = 5 + (i * 3)
        color = (255, 255, 255) if i < signal_bars else (80, 80, 80)
        # Малюємо відносно display_rect.y (який уже включає offset)
        pygame.draw.rect(screen, color, (display_rect.x + 10 + (i * 5), display_rect.y + 12, 3, bar_h))

    # Батарея
    pygame.draw.rect(screen, (255, 255, 255), (display_rect.right - 35, display_rect.y + 7, 25, 12), 1)
    bat_color = (0, 255, 0) if signal_bars > 2 else (255, 50, 50)
    pygame.draw.rect(screen, bat_color, (display_rect.right - 33, display_rect.y + 9, 18, 8))

    # 3. ДОДАТКИ
    if current_app == 0:
        icon_x, icon_y = display_rect.x + 20, display_rect.y + 50
        pygame.draw.rect(screen, (80, 80, 120), (icon_x, icon_y, 45, 45), border_radius=10)
        screen.blit(font_small.render("1", True, (255, 255, 255)), (icon_x + 15, icon_y + 10))
        name_surf = pygame.font.SysFont("Arial", 12, bold=True).render("Triple1", True, (220, 220, 220))
        screen.blit(name_surf, (icon_x, icon_y + 50))

    elif current_app == 1:
        # УСІ КООРДИНАТИ ТЕКСТУ ТЕПЕР ВІДНОСНО display_rect.y
        bank_label = font_small.render(labels["bank"], True, (255, 215, 0))
        screen.blit(bank_label, (display_rect.x + 15, display_rect.y + 40))

        balance_surf = font_small.render(f"{money} UAH", True, (0, 255, 0))
        screen.blit(balance_surf, (display_rect.x + 15, display_rect.y + 75))

        # Історія транзакцій
        # ВАЖЛИВО: y_hist рахується як сума від display_rect.y
        y_hist = display_rect.y + 130
        history_title = pygame.font.SysFont("Arial", 12, bold=True).render(labels["history"], True, (150, 150, 150))
        screen.blit(history_title, (display_rect.x + 15, y_hist))

        for item in money_history[-3:]:
            y_hist += 25
            label = labels.get(item[1], item[1])
            txt = pygame.font.SysFont("Arial", 12).render(f"{item[0]} - {label}", True, (200, 200, 200))
            screen.blit(txt, (display_rect.x + 15, y_hist))