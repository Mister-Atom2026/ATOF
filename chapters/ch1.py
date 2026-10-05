import os
import pygame
import engine
from engine import Car, Player
from house import HousePlayer
from controls import KeyboardState
import traffic  # Імпортуємо твій новий файл
from constants import *

os.environ['SDL_VIDEO_CENTERED'] = '1'


def run(screen, settings):
    traffic_timer = 0
    traffic_state = "RED"  # RED — стоїть потік N, GREEN — стоїть потік A1
    frame_count = 0
    keyboard = KeyboardState()
    # Створюємо 3 ботів на нашому маршруті
    npc_cars = traffic.init_traffic(11)
    # У блоці ресурсів додаємо:
    target_y = 450.0
    phone_y_offset = 450.0
    phone_click_sfx = pygame.mixer.Sound("sounds/click.wav")
    phone_click_sfx.set_volume(0.4)  # Щоб не лупило по вухах
    current_app = 0  # 0 - меню, 1-9 - додатки
    money = 100  # Твоє бабло
    money_history = [("+100", "start")]
    # Список уже зібраних скарбів, щоб не брати їх нескінченно
    collected_treasures = set()
    phone_active = False  # Стан телефону
    phone_settings = engine.get_phone_settings()
    notifications = []  # Список активних сповіщень
    # --- СИСТЕМА ЧАСУ ТА ОСВІТЛЕННЯ ---
    game_time = 480
    night_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    # Ресурси
    car_sfx = {
        'engine': pygame.mixer.Sound("sounds/car_engine.wav"),
        'crash': pygame.mixer.Sound("sounds/car_crash.wav"),
        'beep': pygame.mixer.Sound("sounds/beep.wav"),
        'door_open': pygame.mixer.Sound("sounds/cd_open.wav"),
        'door_close': pygame.mixer.Sound("sounds/cd_close.wav")
    }

    # Налаштування гучності для кожного звуку
    car_sfx['engine'].set_volume(0.3)
    car_sfx['crash'].set_volume(0.5)
    car_sfx['beep'].set_volume(0.4)
    car_sfx['door_open'].set_volume(0.5)
    car_sfx['door_close'].set_volume(0.5)

    engine_chan = pygame.mixer.Channel(6)
    crash_chan = pygame.mixer.Channel(7)

    step_sounds = {
        'asphalt': pygame.mixer.Sound("sounds/footstep_on_stone.wav"),
        'dirt': pygame.mixer.Sound("sounds/footstep_on_dirt.wav"),
        'grass': pygame.mixer.Sound("sounds/footstep_on_grass.wav"),
        'house': pygame.mixer.Sound("sounds/footstep_on_wood.wav")
    }
    for s in step_sounds.values(): s.set_volume(0.2)

    foot_chan = pygame.mixer.Channel(5)
    atom_img = pygame.image.load('characters/atom.png').convert_alpha()
    clock = pygame.time.Clock()
    languages = ["English", "Українська", "Русский"]

    MAP_SCALE = 4.0
    CURR_WORLD_W, CURR_WORLD_H = int(WORLD_WIDTH * MAP_SCALE), int(WORLD_HEIGHT * MAP_SCALE)

    show_debug = False
    game_state = "HOUSE"
    in_car = False

    # СВІТ (МІСТО)
    # 2. Те, що відображається на МІНІКАРТІ та ТАБу (Схематична карта з назвами)
    # Переконайся, що файл називається саме так: "world/Карта Вишневого.png" (або .jpg)
    original_nav_map = pygame.image.load("world/Карта Вишневого.png").convert()
    full_map_img = pygame.transform.scale(original_nav_map, (WIDTH, HEIGHT))
    original_bg = pygame.image.load("world/НОРМ Карта Вишневого.png").convert()
    world_bg = pygame.transform.scale(original_bg, (CURR_WORLD_W, CURR_WORLD_H))
    full_map_img = pygame.transform.scale(original_nav_map, (WIDTH, HEIGHT))
    col_mask = pygame.transform.scale(pygame.image.load("world/Нізя їздити.png").convert(),
                                      (CURR_WORLD_W, CURR_WORLD_H))

    # БУДИНОК
    h_scale = 3
    house_visual = pygame.image.load("ch_home/hm.png").convert()
    house_visual = pygame.transform.scale(house_visual,
                                          (house_visual.get_width() * h_scale, house_visual.get_height() * h_scale))
    house_collision = pygame.transform.scale(pygame.image.load("ch_home/hkm.png").convert(),
                                             (house_visual.get_width(), house_visual.get_height()))
    house_info = pygame.transform.scale(pygame.image.load("ch_home/him.png").convert(),
                                        (house_visual.get_width(), house_visual.get_height()))

    # ОБ'ЄКТИ
    atom = Player(7738, 2330)
    car = Car(7985, 2383)
    car.angle = 270
    atom_h = HousePlayer(162, 161)

    try:
        game_font = pygame.font.Font("static.ttf", 40)
        small_font = pygame.font.Font("static.ttf", 25)
    except:
        game_font = pygame.font.SysFont("Arial", 40, bold=True)
        small_font = pygame.font.SysFont("Arial", 25)

    translations = {
        "English": {
            "hint": "[F] Enter Car", "enter": "[E] Enter House", "exit": "[E] Exit House",
            "resume": "Resume", "stats": "Stats", "settings": "Settings", "menu": "To Menu",
            "vol": "Volume", "lang": "Language", "back": "Back",
            "repair": "Hold [R] to repair", "confirm_q": "Leave the game?",
            "confirm_w": "Progress in this session will be lost.", "yes": "YES", "no": "NO",
            "stats_title": "Session statistics", "stats_money": "Money: {money} UAH",
            "stats_time": "Time: {time}", "stats_treasures": "Treasures found: {treasures}",
            "stats_traffic": "Traffic: {traffic} (police: {police})", "stats_hint": "Press Esc or Enter to return"
        },
        "Українська": {
            "hint": "[А] Сісти в авто", "enter": "[У] Увійти в дім", "exit": "[У] Вийти з дому",
            "resume": "Продовжити", "stats": "Статистика", "settings": "Налаштування", "menu": "В меню",
            "vol": "Гучність", "lang": "Мова", "back": "Назад",
            "repair": "Тримайте [К] для ремонту", "confirm_q": "Вийти з гри?",
            "confirm_w": "Прогрес цієї сесії буде втрачено.", "yes": "ТАК", "no": "НІ",
            "stats_title": "Статистика сесії", "stats_money": "Гроші: {money} UAH",
            "stats_time": "Час: {time}", "stats_treasures": "Знайдено скарбів: {treasures}",
            "stats_traffic": "Трафік: {traffic} (поліції: {police})", "stats_hint": "Натисніть Esc або Enter, щоб повернутися"
        },
        "Русский": {
            "hint": "[А] Сесть в авто", "enter": "[У] Войти в дом", "exit": "[У] Выйти из дома",
            "resume": "Продолжить", "stats": "Статистика", "settings": "Настройки", "menu": "В меню",
            "vol": "Громкость", "lang": "Язык", "back": "Назад",
            "repair": "Удерживайте [К], чтобы починить", "confirm_q": "Выйти из игры?",
            "confirm_w": "Прогресс этой сессии будет потерян.", "yes": "ДА", "no": "НЕТ",
            "stats_title": "Статистика сессии", "stats_money": "Деньги: {money} UAH",
            "stats_time": "Время: {time}", "stats_treasures": "Найдено сокровищ: {treasures}",
            "stats_traffic": "Трафик: {traffic} (полиции: {police})", "stats_hint": "Нажмите Esc или Enter, чтобы вернуться"
        }
    }

    running = True
    while running:
        traffic_timer += 1 / 60  # додаємо час (якщо 60 FPS)
        if traffic_timer > 5:  # кожні 5 секунд міняємо фазу
            traffic_state = "GREEN" if traffic_state == "RED" else "RED"
            traffic_timer = 0
        phone_y_offset += (target_y - phone_y_offset) / 6.0
        # Логіка анімації (вставити перед малюванням телефону)
        target_y = 0.0 if phone_active else 450.0
        current_lang_name = languages[settings['lang_idx']]
        t = translations.get(current_lang_name, translations["English"])
        keys = keyboard
        # Час іде (1 хвилина ігрового часу = 1 хвилина реального при 60 FPS)
        game_time += 1 / 60
        if game_time >= 1440: game_time = 0

        frame_count += 1
        if frame_count % 60 == 0:
            traffic.analyze_traffic_jams(npc_cars)

        # 1. ОБРОБКА ПОДІЙ
        for event in pygame.event.get():
            keyboard.process_event(event)
            if event.type == pygame.QUIT: return "EXIT"
            if event.type == pygame.KEYDOWN:
                # --- ЛОГІКА ТЕЛЕФОНУ ---
                if keyboard.matches(event, pygame.K_m):
                    phone_active = not phone_active
                    current_app = 0
                    phone_click_sfx.play()  # Звук при відкритті/закритті на M

                if phone_active:
                    # КЕРУВАННЯ BACKSPACE
                    if event.key == pygame.K_BACKSPACE:
                        if current_app != 0:
                            current_app = 0  # Повернення в меню
                            phone_click_sfx.play()
                        else:
                            phone_active = False  # Закриття телефону
                            phone_click_sfx.play()

                    # ВІДКРИТТЯ ТІЛЬКИ TRIPLE1 (Тільки якщо ми в меню)
                    elif current_app == 0:
                        if keyboard.matches(event, pygame.K_1) or event.key == pygame.K_KP1:
                            current_app = 1
                            phone_click_sfx.play()
                if event.key == pygame.K_F3:
                    show_debug = not show_debug
                if event.key == pygame.K_TAB:
                    engine.full_screen_map(
                        screen, full_map_img, (car if in_car else atom),
                        CURR_WORLD_W, CURR_WORLD_H, controls=keyboard
                    )
                if event.key == pygame.K_ESCAPE:
                    res = engine.pause_menu(
                        screen, game_font, small_font, settings, translations, languages, keyboard,
                        {
                            "money": money,
                            "time": f"{int(game_time / 60):02d}:{int(game_time % 60):02d}",
                            "treasures": len(collected_treasures),
                            "traffic": len(npc_cars),
                            "police": sum(1 for npc in npc_cars if npc.is_police),
                        },
                    )
                    if res in ["MENU", "EXIT"]: return res
                if keyboard.matches(event, pygame.K_f) and game_state == "CITY":
                    old_in_car = in_car  # Запам'ятовуємо стан до натискання
                    in_car = engine.handle_car_logic(atom, car, in_car)

                    # Граємо звук ТІЛЬКИ якщо стан реально змінився
                    if in_car != old_in_car:
                        if in_car:
                            car_sfx['door_open'].play()
                        else:
                            car_sfx['door_close'].play()
                if keyboard.matches(event, pygame.K_e):
                    if game_state == "CITY" and not in_car:
                        if atom.pos.distance_to(pygame.Vector2(7738, 2330)) < 80:
                            game_state = "HOUSE"
                            atom_h.pos = pygame.Vector2(294, 11)
                    elif game_state == "HOUSE":
                        if engine.check_house_exit(atom_h, house_info):
                            game_state = "CITY"
                            atom.pos = pygame.Vector2(7731, 2326)

        # 2. ОНОВЛЕННЯ (UPDATE)

        if game_state == "CITY":
            target = car if in_car else atom

            # Оновлюємо всіх ботів. Тепер передаємо col_mask (хоч він поки для краси)
            # 1. Оновлюємо ботів
            for npc in npc_cars:
                # Передаємо тільки те, що реально треба для traffic.py
                npc.update(col_mask, car, npc_cars, traffic_state)
            if in_car:
                car.update(keys, col_mask, True, npc_cars)
                atom.pos = pygame.Vector2(car.pos)
            else:
                atom.update(keys, col_mask, car, npc_cars)
                car.update(keys, col_mask, False, npc_cars)

                # Скарби та секрети
                if "guard" not in collected_treasures and atom.pos.distance_to(pygame.Vector2(8909, 1139)) < 60:
                    money += 100
                    money_history.append(("+100", "guard"))
                    collected_treasures.add("guard")

                if "exit" not in collected_treasures and atom.pos.distance_to(pygame.Vector2(4549, 5245)) < 60:
                    money += 111
                    money_history.append(("+111", "bridge"))
                    collected_treasures.add("exit")

                # Логіка ремонту (БЕЗ дублювання)
                if car.is_broken and atom.pos.distance_to(car.pos) < 100:
                    if money >= 50 and keys[pygame.K_r]:
                        car.repair_progress += 1
                        if car.repair_progress >= 180:  # 3 секунди при 60 FPS
                            car.health = car.max_health
                            car.is_broken = False
                            car.repair_progress = 0
                            money -= 50
                            money_history.append(("-50", "repair"))
                    else:
                        car.repair_progress = 0

            engine.handle_surface_footsteps(keys, in_car, game_state, atom.pos, col_mask, step_sounds, foot_chan)
            engine.handle_car_audio(car, in_car, car_sfx, engine_chan, crash_chan, keyboard)
            off_x = max(-(CURR_WORLD_W - WIDTH), min(0, WIDTH // 2 - target.pos.x))
            off_y = max(-(CURR_WORLD_H - HEIGHT), min(0, HEIGHT // 2 - target.pos.y))
        else:
            atom_h.update(keys, house_collision)
            if "nightstand" not in collected_treasures:
                if atom_h.pos.distance_to(pygame.Vector2(206, 199)) < 40:
                    money += 200
                    money_history.append(("+200", "nightstand"))
                    collected_treasures.add("nightstand")

            if "sofa" not in collected_treasures:
                if atom_h.pos.distance_to(pygame.Vector2(723, 128)) < 40:
                    money += 300
                    money_history.append(("+300", "sofa"))
                    collected_treasures.add("sofa")
            engine.handle_surface_footsteps(keys, in_car, game_state, atom_h.pos, None, step_sounds, foot_chan)

        # 3. МАЛЮВАННЯ (DRAW)
        if game_state == "CITY":
            screen.fill((30, 30, 30))
            screen.blit(world_bg, (off_x, off_y))

            # 1. Малюємо машину гравця та її дим
            car.draw(screen, off_x, off_y)
            engine.draw_car_smoke(screen, car, off_x, off_y)

            # 2. Малюємо трафік (ботів)
            for npc in npc_cars:
                npc.draw(screen, off_x, off_y)

            # 3. Якщо гравець не в машині — малюємо його зверху
            if not in_car:
                engine.draw_atom_character(screen, atom.pos.x + off_x, atom.pos.y + off_y, atom_img, atom.angle)
                engine.draw_city_hints(screen, small_font, atom, car, t)

                # Підказка ремонту
                if car.is_broken and atom.pos.distance_to(car.pos) < 100:
                    r_text = t["repair"]
                    txt_surf = small_font.render(r_text, True, (255, 255, 255))
                    screen.blit(txt_surf, (WIDTH // 2 - txt_surf.get_width() // 2, HEIGHT // 2 + 100))

                    if car.repair_progress > 0:
                        pygame.draw.rect(screen, (0, 0, 0), (WIDTH // 2 - 100, HEIGHT // 2 + 140, 200, 15))
                        w = int(200 * (car.repair_progress / 180))
                        pygame.draw.rect(screen, (0, 120, 255), (WIDTH // 2 - 100, HEIGHT // 2 + 140, w, 15))
                        pygame.draw.rect(screen, (255, 255, 255), (WIDTH // 2 - 100, HEIGHT // 2 + 140, 200, 15), 2)

            if in_car: car.draw_speedometer(screen)
            engine.draw_gta_minimap(screen, original_nav_map, target, CURR_WORLD_W, CURR_WORLD_H)
        else:
            engine.draw_house_scene(screen, house_visual, house_info, atom_h, small_font, t)

        if game_state == "CITY":
                ambient = engine.get_ambient_color(game_time)
                if ambient[3] > 0:
                    night_overlay.fill(ambient)
                    screen.blit(night_overlay, (0, 0))
        # Годинник
        h, m = int(game_time / 60), int(game_time % 60)
        time_text = small_font.render(f"{h:02d}:{m:02d}", True, (255, 255, 255))
        screen.blit(time_text, (WIDTH - 100, 20))

        if show_debug:
            engine.draw_debug_coords(screen, (atom_h if game_state == "HOUSE" else target), game_state)
        if phone_y_offset < 449.0:
            engine.draw_mobile_phone(screen, money, game_time, small_font,
                                     current_app, phone_settings, phone_y_offset, money_history,
                                     current_lang_name)

        pygame.display.flip()
        clock.tick(FPS)