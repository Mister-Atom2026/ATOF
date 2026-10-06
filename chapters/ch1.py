import os
import time
import pygame
import engine
from engine import Car, KeyboardState, Player
from house import HousePlayer
from navigator import GPS
from settings_manager import save_settings, save_statistics
import traffic  # Import the traffic module.
from constants import *

os.environ['SDL_VIDEO_CENTERED'] = '1'


def run(screen, settings):
    traffic_timer = 0
    traffic_state = "RED"  # RED pauses route N; GREEN pauses route A1.
    frame_count = 0
    keyboard = KeyboardState()
    # Spawn the configured traffic and police at game start.
    npc_cars = traffic.init_traffic(11)
    # Load the game resources.
    target_y = 450.0
    phone_y_offset = 450.0
    game_audio = engine.load_game_audio()
    phone_click_sfx = game_audio.phone_click
    current_app = 0  # 0 is the phone menu; 1–9 are apps.
    money = 100  # Starting cash.
    total_earned = 0
    total_spent = 0
    money_history = [("+100", "start")]
    # Keep track of collected treasures so they cannot be collected repeatedly.
    collected_treasures = set()
    phone_active = False  # Phone state.
    phone_settings = engine.get_phone_settings()
    # --- Time and lighting ---
    game_time = 480
    night_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    car_sfx = game_audio.car_sounds
    step_sounds = game_audio.footsteps

    def apply_audio_settings():
        engine.configure_game_audio(settings, game_audio)
        traffic.configure_audio(settings)

    apply_audio_settings()

    engine_chan = game_audio.engine_channel
    crash_chan = game_audio.crash_channel
    foot_chan = game_audio.footstep_channel
    clock = pygame.time.Clock()
    languages = ["English", "Українська", "Русский", "Español", "Deutsch", "Français"]

    MAP_SCALE = 4.0
    CURR_WORLD_W, CURR_WORLD_H = int(WORLD_WIDTH * MAP_SCALE), int(WORLD_HEIGHT * MAP_SCALE)
    assets = engine.load_game_assets(
        screen.get_size(),
        (CURR_WORLD_W, CURR_WORLD_H),
    )
    atom_img = assets.atom
    original_nav_map = assets.original_nav_map
    world_bg = assets.world_background
    full_map_img = assets.full_map
    col_mask = assets.collision_mask
    house_visual = assets.house_visual
    house_collision = assets.house_collision
    house_info = assets.house_info

    show_debug = False
    game_state = "HOUSE"
    in_car = False

    # GAME OBJECTS
    atom = Player(7738, 2330)
    car = Car(7985, 2383)
    car.angle = 270
    atom_h = HousePlayer(162, 161)
    gps = GPS()

    game_font, small_font = engine.load_game_fonts()

    translations = {
        "English": {
            "hint": "[F] Enter Car", "enter": "[E] Enter House", "exit": "[E] Exit House",
            "resume": "Resume", "stats": "Stats", "settings": "Settings", "menu": "To Menu",
            "vol": "Volume", "lang": "Language", "back": "Back",
            "volume": "Volume", "music_vol": "Music Volume", "npc_vol": "NPC Volume",
            "crash_vol": "Crash Volume", "button_vol": "Button Volume",
            "footsteps_vol": "Footsteps Volume",
            "audio_hint": "Up/Down selects a sound; Left/Right adjusts it; Esc returns",
            "repair": "Hold [R] to repair", "confirm_q": "Leave the game?",
            "confirm_w": "Progress in this session will be lost.", "yes": "YES", "no": "NO",
            "stats_title": "Session statistics", "stats_money": "Money: {money} UAH",
            "stats_time": "Time: {time}", "stats_treasures": "Treasures found: {treasures}",
            "stats_earned": "Total earned: {amount} UAH", "stats_spent": "Total spent: {amount} UAH", "stats_hint": "Press Esc or Enter to return",
            "gps_distance": "Distance: {distance} units", "gps_set": "Left-click: set destination",
            "gps_clear": "Right-click/Delete: clear destination"
        },
        "Українська": {
            "hint": "[А] Сісти в авто", "enter": "[У] Увійти в дім", "exit": "[У] Вийти з дому",
            "resume": "Продовжити", "stats": "Статистика", "settings": "Налаштування", "menu": "В меню",
            "vol": "Гучність", "lang": "Мова", "back": "Назад",
            "volume": "Гучність", "music_vol": "Гучність музики", "npc_vol": "Гучність НПС",
            "crash_vol": "Гучність аварій", "button_vol": "Гучність кнопок",
            "footsteps_vol": "Гучність кроків",
            "audio_hint": "↑/↓ обирає звук; ←/→ змінює гучність; Esc — назад",
            "repair": "Тримайте [К] для ремонту", "confirm_q": "Вийти з гри?",
            "confirm_w": "Прогрес цієї сесії буде втрачено.", "yes": "ТАК", "no": "НІ",
            "stats_title": "Статистика сесії", "stats_money": "Гроші: {money} UAH",
            "stats_time": "Час: {time}", "stats_treasures": "Знайдено скарбів: {treasures}",
            "stats_earned": "Всього зароблено: {amount} UAH", "stats_spent": "Всього витрачено: {amount} UAH", "stats_hint": "Натисніть Esc або Enter, щоб повернутися",
            "gps_distance": "Відстань: {distance} ігрових од.", "gps_set": "ЛКМ: поставити точку",
            "gps_clear": "ПКМ/Delete: прибрати точку"
        },
        "Русский": {
            "hint": "[А] Сесть в авто", "enter": "[У] Войти в дом", "exit": "[У] Выйти из дома",
            "resume": "Продолжить", "stats": "Статистика", "settings": "Настройки", "menu": "В меню",
            "vol": "Громкость", "lang": "Язык", "back": "Назад",
            "volume": "Громкость", "music_vol": "Громкость музыки", "npc_vol": "Громкость НПС",
            "crash_vol": "Громкость аварий", "button_vol": "Громкость кнопок",
            "footsteps_vol": "Громкость шагов",
            "audio_hint": "↑/↓ выбирает звук; ←/→ меняет громкость; Esc — назад",
            "repair": "Удерживайте [К], чтобы починить", "confirm_q": "Выйти из игры?",
            "confirm_w": "Прогресс этой сессии будет потерян.", "yes": "ДА", "no": "НЕТ",
            "stats_title": "Статистика сессии", "stats_money": "Деньги: {money} UAH",
            "stats_time": "Время: {time}", "stats_treasures": "Найдено сокровищ: {treasures}",
            "stats_earned": "Всего заработано: {amount} UAH", "stats_spent": "Всего потрачено: {amount} UAH", "stats_hint": "Нажмите Esc или Enter, чтобы вернуться",
            "gps_distance": "Расстояние: {distance} игровых ед.", "gps_set": "ЛКМ: поставить точку",
            "gps_clear": "ПКМ/Delete: убрать точку"
        },
        "Español": {
            "hint": "[F] Subir al coche", "enter": "[E] Entrar en casa", "exit": "[E] Salir de casa",
            "resume": "Reanudar", "stats": "Estadísticas", "settings": "Ajustes", "menu": "Volver al menú",
            "vol": "Volumen", "lang": "Idioma", "back": "Atrás",
            "volume": "Volumen", "music_vol": "Volumen de la música", "npc_vol": "Volumen de los NPC",
            "crash_vol": "Volumen de choques", "button_vol": "Volumen de botones",
            "footsteps_vol": "Volumen de pasos",
            "audio_hint": "↑/↓ elegir sonido; ←/→ ajustar volumen; Esc para volver",
            "repair": "Mantén [R] para reparar", "confirm_q": "¿Salir del juego?",
            "confirm_w": "Se perderá el progreso de esta sesión.", "yes": "SÍ", "no": "NO",
            "stats_title": "Estadísticas de la sesión", "stats_money": "Dinero: {money} UAH",
            "stats_time": "Tiempo: {time}", "stats_treasures": "Tesoros encontrados: {treasures}",
            "stats_earned": "Total ganado: {amount} UAH", "stats_spent": "Total gastado: {amount} UAH",
            "stats_hint": "Pulsa Esc o Enter para volver",
            "gps_distance": "Distancia: {distance} unidades", "gps_set": "Clic izquierdo: marcar destino",
            "gps_clear": "Clic derecho/Delete: borrar destino",
        },
        "Deutsch": {
            "hint": "[F] Ins Auto steigen", "enter": "[E] Haus betreten", "exit": "[E] Haus verlassen",
            "resume": "Fortsetzen", "stats": "Statistik", "settings": "Einstellungen", "menu": "Zum Hauptmenü",
            "vol": "Lautstärke", "lang": "Sprache", "back": "Zurück",
            "volume": "Lautstärke", "music_vol": "Musiklautstärke", "npc_vol": "NPC-Lautstärke",
            "crash_vol": "Lautstärke für Unfälle", "button_vol": "Tastenlautstärke",
            "footsteps_vol": "Schrittlautstärke",
            "audio_hint": "↑/↓ Ton wählen; ←/→ Lautstärke ändern; Esc zurück",
            "repair": "[R] zum Reparieren halten", "confirm_q": "Spiel verlassen?",
            "confirm_w": "Der Fortschritt dieser Sitzung geht verloren.", "yes": "JA", "no": "NEIN",
            "stats_title": "Sitzungsstatistik", "stats_money": "Geld: {money} UAH",
            "stats_time": "Zeit: {time}", "stats_treasures": "Gefundene Schätze: {treasures}",
            "stats_earned": "Insgesamt verdient: {amount} UAH", "stats_spent": "Insgesamt ausgegeben: {amount} UAH",
            "stats_hint": "Esc oder Enter drücken, um zurückzukehren",
            "gps_distance": "Entfernung: {distance} Einheiten", "gps_set": "Linksklick: Ziel setzen",
            "gps_clear": "Rechtsklick/Delete: Ziel löschen",
        },
        "Français": {
            "hint": "[F] Monter en voiture", "enter": "[E] Entrer dans la maison", "exit": "[E] Sortir de la maison",
            "resume": "Reprendre", "stats": "Statistiques", "settings": "Paramètres", "menu": "Menu principal",
            "vol": "Volume", "lang": "Langue", "back": "Retour",
            "volume": "Volume", "music_vol": "Volume de la musique", "npc_vol": "Volume des PNJ",
            "crash_vol": "Volume des collisions", "button_vol": "Volume des boutons",
            "footsteps_vol": "Volume des pas",
            "audio_hint": "↑/↓ choisir le son ; ←/→ régler le volume ; Échap pour revenir",
            "repair": "Maintenir [R] pour réparer", "confirm_q": "Quitter la partie ?",
            "confirm_w": "La progression de cette session sera perdue.", "yes": "OUI", "no": "NON",
            "stats_title": "Statistiques de la session", "stats_money": "Argent : {money} UAH",
            "stats_time": "Temps : {time}", "stats_treasures": "Trésors trouvés : {treasures}",
            "stats_earned": "Total gagné : {amount} UAH", "stats_spent": "Total dépensé : {amount} UAH",
            "stats_hint": "Appuyez sur Échap ou Entrée pour revenir",
            "gps_distance": "Distance : {distance} unités", "gps_set": "Clic gauche : définir la destination",
            "gps_clear": "Clic droit/Delete : supprimer la destination",
        }
    }

    def save_last_session_stats():
        save_statistics({
            "money": money,
            "earned": total_earned,
            "spent": total_spent,
            "time": f"{int(game_time / 60):02d}:{int(game_time % 60):02d}",
            "treasures": len(collected_treasures),
        })

    running = True
    last_frame_time = time.perf_counter()
    while running:
        clock.tick(FPS)
        now = time.perf_counter()
        frame_scale = (now - last_frame_time) * 60
        last_frame_time = now
        frame_scale = max(0.05, min(frame_scale, 3.0))
        target = car if in_car else atom
        off_x = off_y = 0
        traffic_timer += frame_scale / 60
        if traffic_timer > 5:  # Switch the traffic-light phase every five seconds.
            traffic_state = "GREEN" if traffic_state == "RED" else "RED"
            traffic_timer = 0
        phone_y_offset += (target_y - phone_y_offset) * (1 - (5 / 6) ** frame_scale)
        # Update the phone slide animation before drawing it.
        target_y = 0.0 if phone_active else 450.0
        current_lang_name = languages[settings['lang_idx']]
        t = translations.get(current_lang_name, translations["English"])
        keys = keyboard
        # Advance game time by one second per real second at 60 FPS.
        game_time += frame_scale / 60
        if game_time >= 1440: game_time = 0

        frame_count += frame_scale
        if frame_count >= 60:
            traffic.analyze_traffic_jams(npc_cars)
            frame_count %= 60

        # 1. Process events.
        for event in pygame.event.get():
            keyboard.process_event(event)
            if event.type == pygame.VIDEORESIZE:
                screen = engine.apply_window_resize(event.size, settings)
                full_map_img = pygame.transform.scale(original_nav_map, (WIDTH, HEIGHT))
                night_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                save_settings(settings)
            if event.type == pygame.QUIT:
                save_last_session_stats()
                return "EXIT"
            if event.type == pygame.KEYDOWN:
                # --- Phone controls ---
                if keyboard.matches(event, pygame.K_m):
                    phone_active = not phone_active
                    current_app = 0
                    phone_click_sfx.play()  # Play a sound when M opens or closes the phone.

                if phone_active:
                    # BACKSPACE controls.
                    if event.key == pygame.K_BACKSPACE:
                        if current_app != 0:
                            current_app = 0  # Return to the phone menu.
                            phone_click_sfx.play()
                        else:
                            phone_active = False  # Close the phone.
                            phone_click_sfx.play()

                    # Open phone apps from the home screen.
                    elif current_app == 0:
                        if keyboard.matches(event, pygame.K_1) or event.key == pygame.K_KP1:
                            current_app = 1
                            phone_click_sfx.play()
                        elif keyboard.matches(event, pygame.K_2) or event.key == pygame.K_KP2:
                            current_app = 2
                            phone_click_sfx.play()
                    elif current_app == 2:
                        # Number keys select one of the available phone case colors.
                        phone_color_keys = {
                            pygame.K_1: 0, pygame.K_KP1: 0,
                            pygame.K_2: 1, pygame.K_KP2: 1,
                            pygame.K_3: 2, pygame.K_KP3: 2,
                            pygame.K_4: 3, pygame.K_KP4: 3,
                            pygame.K_5: 4, pygame.K_KP5: 4,
                        }
                        if event.key in phone_color_keys:
                            phone_settings["case_idx"] = phone_color_keys[event.key]
                            engine.save_phone_settings(phone_settings)
                            phone_click_sfx.play()
                if event.key == pygame.K_F3:
                    show_debug = not show_debug
                if event.key == pygame.K_TAB:
                    engine.full_screen_map(
                        screen, full_map_img, (car if in_car else atom),
                        CURR_WORLD_W, CURR_WORLD_H, controls=keyboard, gps=gps, labels=t
                    )
                if event.key == pygame.K_ESCAPE:
                    res = engine.pause_menu(
                        screen, game_font, small_font, settings, translations, languages, keyboard,
                        {
                            "money": money,
                            "earned": total_earned,
                            "spent": total_spent,
                            "time": f"{int(game_time / 60):02d}:{int(game_time % 60):02d}",
                            "treasures": len(collected_treasures),
                        },
                        on_change=save_settings,
                    )
                    apply_audio_settings()
                    if res == "VIDEO_CHANGED":
                        screen = engine.apply_video_settings(settings)
                        full_map_img = pygame.transform.scale(original_nav_map, (WIDTH, HEIGHT))
                        night_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    clock.tick(0)
                    last_frame_time = time.perf_counter()
                    if res in ["MENU", "EXIT"]:
                        save_last_session_stats()
                        return res
                if keyboard.matches(event, pygame.K_f) and game_state == "CITY":
                    old_in_car = in_car  # Save the previous state before toggling.
                    in_car = engine.handle_car_logic(atom, car, in_car)

                    # Play the sound only when the state changes.
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

        # 2. Update the game state.

        if game_state == "CITY":
            target = car if in_car else atom

            # Update all traffic and pass the collision mask.
            # 1. Update traffic and police.
            for npc in npc_cars:
                # Pass the arguments used by traffic.py.
                npc.update(col_mask, car, npc_cars, traffic_state, frame_scale)
            if in_car:
                car.update(keys, col_mask, True, npc_cars, frame_scale)
                atom.pos = pygame.Vector2(car.pos)
            else:
                atom.update(keys, col_mask, car, npc_cars, frame_scale)
                car.update(keys, col_mask, False, npc_cars, frame_scale)

                # Treasures and secrets.
                if "guard" not in collected_treasures and atom.pos.distance_to(pygame.Vector2(8909, 1139)) < 60:
                    money += 100
                    total_earned += 100
                    money_history.append(("+100", "guard"))
                    collected_treasures.add("guard")

                if "exit" not in collected_treasures and atom.pos.distance_to(pygame.Vector2(4549, 5245)) < 60:
                    money += 111
                    total_earned += 111
                    money_history.append(("+111", "bridge"))
                    collected_treasures.add("exit")

                # Repair logic.
                if car.is_broken and atom.pos.distance_to(car.pos) < 100:
                    if money >= 50 and keys[pygame.K_r]:
                        car.repair_progress += frame_scale
                        if car.repair_progress >= 180:  # Three seconds at 60 FPS.
                            car.health = car.max_health
                            car.is_broken = False
                            car.repair_progress = 0
                            money -= 50
                            total_spent += 50
                            money_history.append(("-50", "repair"))
                    else:
                        car.repair_progress = 0

            engine.handle_surface_footsteps(keys, in_car, game_state, atom.pos, col_mask, step_sounds, foot_chan)
            engine.handle_car_audio(car, in_car, car_sfx, engine_chan, crash_chan, keyboard)
            off_x = max(-(CURR_WORLD_W - WIDTH), min(0, WIDTH // 2 - target.pos.x))
            off_y = max(-(CURR_WORLD_H - HEIGHT), min(0, HEIGHT // 2 - target.pos.y))
        else:
            atom_h.update(keys, house_collision, frame_scale)
            if "nightstand" not in collected_treasures:
                if atom_h.pos.distance_to(pygame.Vector2(206, 199)) < 40:
                    money += 200
                    total_earned += 200
                    money_history.append(("+200", "nightstand"))
                    collected_treasures.add("nightstand")

            if "sofa" not in collected_treasures:
                if atom_h.pos.distance_to(pygame.Vector2(723, 128)) < 40:
                    money += 300
                    total_earned += 300
                    money_history.append(("+300", "sofa"))
                    collected_treasures.add("sofa")
            engine.handle_surface_footsteps(keys, in_car, game_state, atom_h.pos, None, step_sounds, foot_chan)

        # 3. Draw the scene.
        if game_state == "CITY":
            screen.fill((30, 30, 30))
            screen.blit(world_bg, (off_x, off_y))

            # 1. Draw the player’s car and its smoke.
            car.draw(screen, off_x, off_y)
            engine.draw_car_smoke(screen, car, off_x, off_y)

            # 2. Draw traffic and police.
            for npc in npc_cars:
                npc.draw(screen, off_x, off_y)

            # 3. Draw the player on top when on foot.
            if not in_car:
                engine.draw_atom_character(screen, atom.pos.x + off_x, atom.pos.y + off_y, atom_img, atom.angle)
                engine.draw_city_hints(screen, small_font, atom, car, t)

                # Repair prompt.
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
            engine.draw_gta_minimap(
                screen, original_nav_map, target, CURR_WORLD_W, CURR_WORLD_H,
                gps=gps, labels=t,
            )
        else:
            engine.draw_house_scene(screen, house_visual, house_info, atom_h, small_font, t)

        if game_state == "CITY":
                ambient = engine.get_ambient_color(game_time)
                if ambient[3] > 0:
                    night_overlay.fill(ambient)
                    screen.blit(night_overlay, (0, 0))
        # In-game clock.
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

    save_last_session_stats()
    return "EXIT"
