import os
import time
import pygame
import engine
from constants import *

os.environ['SDL_VIDEO_CENTERED'] = '1'

def run(screen, settings):
    traffic_timer = 0
    traffic_state = "RED"  # RED pauses route N; GREEN pauses route A1.
    frame_count = 0
    keyboard = engine.KeyboardState()
    # Spawn the configured traffic and police at game start.
    npc_cars = engine.traffic.init_traffic(11)
    map_scale = 4.0
    current_world_width = int(WORLD_WIDTH * map_scale)
    current_world_height = int(WORLD_HEIGHT * map_scale)
    camera = engine.Camera2D(
        screen.get_size(),
        (current_world_width, current_world_height),
    )
    resources = engine.load_chapter_resources(
        screen.get_size(),
        (current_world_width, current_world_height),
    )
    # Load the game resources.
    target_y = 450.0
    phone_y_offset = 450.0
    game_audio = resources.audio
    phone_click_sfx = game_audio.phone_click
    current_app = 0  # 0 is the phone menu; 1–9 are apps.
    game_save = engine.load_game_save()
    money = game_save["money"] if game_save else 100
    total_earned = game_save["earned"] if game_save else 0
    total_spent = game_save["spent"] if game_save else 0
    money_history = [("+100", "start")] if not game_save else []
    # Keep track of collected treasures so they cannot be collected repeatedly.
    collected_treasures = set()
    phone_active = False  # Phone state.
    phone_settings = engine.get_phone_settings()
    # --- Time and lighting ---
    game_time = game_save["game_time"] if game_save else 480.0
    night_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    wake_overlay = pygame.Surface(screen.get_size())
    car_sfx = game_audio.car_sounds
    step_sounds = game_audio.footsteps

    def apply_audio_settings():
        engine.configure_game_audio(settings, game_audio)
        engine.traffic.configure_audio(settings)

    apply_audio_settings()

    engine_chan = game_audio.engine_channel
    crash_chan = game_audio.crash_channel
    foot_chan = game_audio.footstep_channel
    horn_chan = game_audio.horn_channel
    clock = pygame.time.Clock()
    frame_clock = engine.FrameClock()
    frame_renderer = engine.LayeredRenderer()
    languages = engine.SUPPORTED_LANGUAGES

    assets = resources.assets
    atom_img = assets.atom
    original_nav_map = assets.original_nav_map
    world_bg = assets.world_background
    full_map_img = assets.full_map
    col_mask = assets.collision_mask
    house_visual = assets.house_visual
    house_collision = assets.house_collision
    house_info = assets.house_info

    show_debug = False
    game_state = game_save["game_state"] if game_save else "HOUSE"
    scene_manager = engine.SceneManager(game_state)
    scene_manager.register("CITY")
    scene_manager.register("HOUSE")
    in_car = False

    # GAME OBJECTS
    atom = engine.Player(7738, 2330)
    car = engine.Car(7985, 2383)
    car.angle = 270
    if game_save:
        atom.pos.update(game_save["player"]["x"], game_save["player"]["y"])
        atom.angle = game_save["player"]["angle"]
        car.pos.update(game_save["car"]["x"], game_save["car"]["y"])
        car.angle = game_save["car"]["angle"]
        car.speed = game_save["car"]["speed"]
        car.motion_velocity = pygame.Vector2(car.speed, 0).rotate(-car.angle + 180)
        car.health = min(game_save["car"]["health"], car.max_health)
        car.is_broken = game_save["car"]["is_broken"]
    atom_h = engine.HousePlayer(162, 161)
    atom_h.pos.update(engine.HOUSE_SLEEP_SPOT)
    if game_save and game_save["game_state"] == "HOUSE":
        atom_h.pos.update(
            game_save["house_player"]["x"],
            game_save["house_player"]["y"],
        )
        atom_h.angle = game_save["house_player"]["angle"]
    gps = engine.GPS()
    if game_save:
        collected_treasures.update(game_save["collected_treasures"])
    personal_records = engine.load_statistics()
    distance_since_crash = game_save["distance_streak"] if game_save else 0.0
    current_drift_distance = game_save["drift_streak"] if game_save else 0.0
    sleep_requested = False
    wake_fade_started = None
    manual_headlights = False
    radio = engine.GameRadio(settings)

    game_font, small_font = resources.game_font, resources.small_font

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
            "gps_distance": "Distance: {distance}", "gps_set": "Left-click: set destination",
            "gps_clear": "Right-click/Backspace: clear destination",
            "radio_on": "{station} — {track} | V: pause | ,/<: previous | ./>: next",
            "radio_paused": "{station} — {track} | V: play | ,/<: previous | ./>: next",
            "radio_off": "RADIO OFF | ,/<: previous | ./>: next",
        },
        "Українська": {
            "hint": "[F] Сісти в авто", "enter": "[E] Увійти в дім", "exit": "[E] Вийти з дому",
            "resume": "Продовжити", "stats": "Статистика", "settings": "Налаштування", "menu": "В меню",
            "vol": "Гучність", "lang": "Мова", "back": "Назад",
            "volume": "Гучність", "music_vol": "Гучність музики", "npc_vol": "Гучність НПС",
            "crash_vol": "Гучність аварій", "button_vol": "Гучність кнопок",
            "footsteps_vol": "Гучність кроків",
            "audio_hint": "↑/↓ обирає звук; ←/→ змінює гучність; Esc — назад",
            "repair": "Тримайте [R] для ремонту", "confirm_q": "Вийти з гри?",
            "confirm_w": "Прогрес цієї сесії буде втрачено.", "yes": "ТАК", "no": "НІ",
            "stats_title": "Статистика сесії", "stats_money": "Гроші: {money} UAH",
            "stats_time": "Час: {time}", "stats_treasures": "Знайдено скарбів: {treasures}",
            "stats_earned": "Всього зароблено: {amount} UAH", "stats_spent": "Всього витрачено: {amount} UAH", "stats_hint": "Натисніть Esc або Enter, щоб повернутися",
            "gps_distance": "Відстань: {distance}", "gps_set": "ЛКМ: поставити точку",
            "gps_clear": "ПКМ/Backspace: прибрати точку",
            "radio_on": "{station} — {track} | V: пауза | ,/<: попередня | ./>: наступна",
            "radio_paused": "{station} — {track} | V: слухати | ,/<: попередня | ./>: наступна",
            "radio_off": "РАДІО ВИМКНЕНО | ,/<: попередня | ./>: наступна",
        },
        "Русский": {
            "hint": "[F] Сесть в авто", "enter": "[E] Войти в дом", "exit": "[E] Выйти из дома",
            "resume": "Продолжить", "stats": "Статистика", "settings": "Настройки", "menu": "В меню",
            "vol": "Громкость", "lang": "Язык", "back": "Назад",
            "volume": "Громкость", "music_vol": "Громкость музыки", "npc_vol": "Громкость НПС",
            "crash_vol": "Громкость аварий", "button_vol": "Громкость кнопок",
            "footsteps_vol": "Громкость шагов",
            "audio_hint": "↑/↓ выбирает звук; ←/→ меняет громкость; Esc — назад",
            "repair": "Удерживайте [R], чтобы починить", "confirm_q": "Выйти из игры?",
            "confirm_w": "Прогресс этой сессии будет потерян.", "yes": "ДА", "no": "НЕТ",
            "stats_title": "Статистика сессии", "stats_money": "Деньги: {money} UAH",
            "stats_time": "Время: {time}", "stats_treasures": "Найдено сокровищ: {treasures}",
            "stats_earned": "Всего заработано: {amount} UAH", "stats_spent": "Всего потрачено: {amount} UAH", "stats_hint": "Нажмите Esc или Enter, чтобы вернуться",
            "gps_distance": "Расстояние: {distance}", "gps_set": "ЛКМ: поставить точку",
            "gps_clear": "ПКМ/Backspace: убрать точку",
            "radio_on": "{station} — {track} | V: пауза | ,/<: предыдущая | ./>: следующая",
            "radio_paused": "{station} — {track} | V: слушать | ,/<: предыдущая | ./>: следующая",
            "radio_off": "РАДИО ВЫКЛЮЧЕНО | ,/<: предыдущая | ./>: следующая",
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
            "gps_distance": "Distancia: {distance}", "gps_set": "Clic izquierdo: marcar destino",
            "gps_clear": "Clic derecho/Retroceso: borrar destino",
            "radio_on": "{station} — {track} | V: pausa | ,/<: anterior | ./>: siguiente",
            "radio_paused": "{station} — {track} | V: escuchar | ,/<: anterior | ./>: siguiente",
            "radio_off": "RADIO APAGADA | ,/<: anterior | ./>: siguiente",
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
            "gps_distance": "Entfernung: {distance}", "gps_set": "Linksklick: Ziel setzen",
            "gps_clear": "Rechtsklick/Backspace: Ziel löschen",
            "radio_on": "{station} — {track} | V: Pause | ,/<: vorheriger | ./>: nächster",
            "radio_paused": "{station} — {track} | V: abspielen | ,/<: vorheriger | ./>: nächster",
            "radio_off": "RADIO AUS | ,/<: vorheriger | ./>: nächster",
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
            "gps_distance": "Distance : {distance}", "gps_set": "Clic gauche : définir la destination",
            "gps_clear": "Clic droit/Retour arrière : supprimer la destination",
            "radio_on": "{station} — {track} | V : pause | ,/< : précédente | ./> : suivante",
            "radio_paused": "{station} — {track} | V : écouter | ,/< : précédente | ./> : suivante",
            "radio_off": "RADIO ÉTEINTE | ,/< : précédente | ./> : suivante",
        }
    }

    per_language_labels = {
        "English": {
            "sleep_save": "Press [E] / [T] by the bed to sleep and save",
            "video": "Video", "window_mode": "Window mode", "window_mode_value": "Resizable",
            "resolution": "Resolution", "fps_limit": "Frame rate limit",
            "fps_unlimited": "Unlimited",
            "video_hint": "FPS is not monitor Hz. Use the title bar button to maximize.",
            "stats_max_speed": "Top speed: {value} km/h",
            "stats_longest_drift": "Longest drift: {value} m",
            "stats_no_crash": "Longest drive without a crash: {value} m",
        },
        "Українська": {
            "sleep_save": "Натисніть [E] / [T] біля ліжка, щоб заснути й зберегтися",
            "video": "Відео", "window_mode": "Режим вікна", "window_mode_value": "Змінний розмір",
            "resolution": "Роздільність", "fps_limit": "Ліміт кадрів (FPS)",
            "fps_unlimited": "Без обмежень",
            "video_hint": "FPS — не герци монітора. Натисніть кнопку в заголовку, щоб розгорнути вікно.",
            "stats_max_speed": "Максимальна швидкість: {value} км/год",
            "stats_longest_drift": "Найдовший занос: {value} м",
            "stats_no_crash": "Найдовша поїздка без аварій: {value} м",
        },
        "Русский": {
            "sleep_save": "Нажмите [E] / [T] у кровати, чтобы поспать и сохраниться",
            "video": "Видео", "window_mode": "Режим окна", "window_mode_value": "Изменяемый размер",
            "resolution": "Разрешение", "fps_limit": "Лимит кадров (FPS)",
            "fps_unlimited": "Без ограничений",
            "video_hint": "FPS — не герцы монитора. Нажмите кнопку в заголовке, чтобы развернуть окно.",
            "stats_max_speed": "Максимальная скорость: {value} км/ч",
            "stats_longest_drift": "Самый длинный занос: {value} м",
            "stats_no_crash": "Самая длинная поездка без аварий: {value} м",
        },
        "Español": {
            "sleep_save": "Pulsa [E] / [T] junto a la cama para dormir y guardar",
            "video": "Vídeo", "window_mode": "Modo de ventana", "window_mode_value": "Redimensionable",
            "resolution": "Resolución", "fps_limit": "Límite de fotogramas (FPS)",
            "fps_unlimited": "Sin límite",
            "video_hint": "FPS no son los Hz. Usa el botón de la barra superior para maximizar.",
            "stats_max_speed": "Velocidad máxima: {value} km/h",
            "stats_longest_drift": "Derrape más largo: {value} m",
            "stats_no_crash": "Trayecto más largo sin choque: {value} m",
        },
        "Deutsch": {
            "sleep_save": "Am Bett [E] / [T] drücken, um zu schlafen und zu speichern",
            "video": "Video", "window_mode": "Fenstermodus", "window_mode_value": "Größe änderbar",
            "resolution": "Auflösung", "fps_limit": "Bildratenlimit (FPS)",
            "fps_unlimited": "Unbegrenzt",
            "video_hint": "FPS sind nicht Monitor-Hz. Mit der Schaltfläche in der Titelleiste maximieren.",
            "stats_max_speed": "Höchstgeschwindigkeit: {value} km/h",
            "stats_longest_drift": "Längster Drift: {value} m",
            "stats_no_crash": "Längste Fahrt ohne Unfall: {value} m",
        },
        "Français": {
            "sleep_save": "Appuyez sur [E] / [T] près du lit pour dormir et sauvegarder",
            "video": "Vidéo", "window_mode": "Mode fenêtre", "window_mode_value": "Redimensionnable",
            "resolution": "Résolution", "fps_limit": "Limite d’images (FPS)",
            "fps_unlimited": "Illimitée",
            "video_hint": "Les FPS ne sont pas les Hz. Utilisez le bouton de la barre de titre.",
            "stats_max_speed": "Vitesse maximale : {value} km/h",
            "stats_longest_drift": "Dérapage le plus long : {value} m",
            "stats_no_crash": "Trajet le plus long sans accident : {value} m",
        },
    }
    for language, labels in per_language_labels.items():
        translations[language].update(labels)

    def save_last_session_stats():
        engine.save_statistics({
            "money": money,
            "earned": total_earned,
            "spent": total_spent,
            "time": f"{int(game_time / 60):02d}:{int(game_time % 60):02d}",
            "treasures": len(collected_treasures),
            "max_speed_kmh": personal_records["max_speed_kmh"],
            "longest_drift_m": personal_records["longest_drift_m"],
            "distance_without_crash_m": personal_records["distance_without_crash_m"],
        })

    def save_sleep_game():
        engine.save_game_save({
            "game_state": game_state,
            "player": {
                "x": atom.pos.x,
                "y": atom.pos.y,
                "angle": atom.angle,
            },
            "house_player": {
                "x": atom_h.pos.x,
                "y": atom_h.pos.y,
                "angle": atom_h.angle,
            },
            "car": {
                "x": car.pos.x,
                "y": car.pos.y,
                "angle": car.angle,
                "speed": car.speed,
                "health": car.health,
                "is_broken": car.is_broken,
            },
            "money": money,
            "earned": total_earned,
            "spent": total_spent,
            "game_time": game_time,
            "collected_treasures": sorted(collected_treasures),
            "distance_streak": distance_since_crash,
            "drift_streak": current_drift_distance,
        })
        save_last_session_stats()

    running = True
    frame_clock.reset()
    while running:
        frame_scale = frame_clock.tick(clock, FPS)
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
            engine.traffic.analyze_traffic_jams(npc_cars)
            frame_count %= 60

        # 1. Process events.
        for event in pygame.event.get():
            keyboard.process_event(event)
            if event.type == pygame.VIDEORESIZE:
                screen = engine.apply_window_resize(event.size, settings)
                camera.resize(screen.get_size())
                full_map_img = pygame.transform.scale(original_nav_map, (WIDTH, HEIGHT))
                night_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                wake_overlay = pygame.Surface(screen.get_size())
                engine.save_settings(settings)
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
                        current_world_width, current_world_height,
                        controls=keyboard, gps=gps, labels=t
                    )
                if event.key == pygame.K_ESCAPE:
                    radio_was_playing = radio.is_playing
                    radio.pause()
                    res = engine.pause_menu(
                        screen, game_font, small_font, settings, translations, languages, keyboard,
                        {
                            "money": money,
                            "earned": total_earned,
                            "spent": total_spent,
                            "time": f"{int(game_time / 60):02d}:{int(game_time % 60):02d}",
                            "treasures": len(collected_treasures),
                            "max_speed_kmh": personal_records["max_speed_kmh"],
                            "longest_drift_m": personal_records["longest_drift_m"],
                            "distance_without_crash_m": personal_records[
                                "distance_without_crash_m"
                            ],
                        },
                        on_change=engine.save_settings,
                    )
                    apply_audio_settings()
                    if res == "VIDEO_CHANGED":
                        screen = engine.apply_video_settings(settings)
                        camera.resize(screen.get_size())
                        full_map_img = pygame.transform.scale(original_nav_map, (WIDTH, HEIGHT))
                        night_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    clock.tick(0)
                    frame_clock.reset()
                    if res in ["MENU", "EXIT"]:
                        radio.stop()
                        save_last_session_stats()
                        return res
                    if radio_was_playing:
                        radio.resume()
                if keyboard.matches(event, pygame.K_f) and game_state == "CITY":
                    old_in_car = in_car  # Save the previous state before toggling.
                    in_car = engine.handle_car_logic(atom, car, in_car)

                    # Play the sound only when the state changes.
                    if in_car != old_in_car:
                        if in_car:
                            car_sfx['door_open'].play()
                        else:
                            car_sfx['door_close'].play()
                            radio.pause()
                if game_state == "CITY" and in_car and not getattr(event, "repeat", False):
                    if keyboard.matches(event, pygame.K_h):
                        manual_headlights = not manual_headlights
                    if keyboard.matches(event, pygame.K_e):
                        engine.play_car_horn(car_sfx, horn_chan)
                        engine.traffic.respond_to_horn(npc_cars, car.pos)
                    if keyboard.matches(event, pygame.K_v):
                        radio.toggle()
                    if keyboard.matches(event, pygame.K_COMMA):
                        radio.cycle_station(-1)
                    if keyboard.matches(event, pygame.K_PERIOD):
                        radio.cycle_station(1)
                sleep_key_pressed = (
                    keyboard.matches(event, pygame.K_e)
                    or event.key == pygame.K_t
                    or getattr(event, "unicode", "").lower() in ("t", "т")
                )
                if sleep_key_pressed:
                    if game_state == "HOUSE":
                        if engine.is_at_sleep_spot(game_state, atom_h.pos):
                            sleep_requested = True
                        elif keyboard.matches(event, pygame.K_e) and engine.check_house_exit(
                            atom_h, house_info
                        ):
                            scene_manager.transition("CITY")
                            game_state = scene_manager.current
                            atom.pos = pygame.Vector2(7731, 2326)
                    elif keyboard.matches(event, pygame.K_e) and not in_car:
                        if atom.pos.distance_to(pygame.Vector2(7738, 2330)) < 80:
                            scene_manager.transition("HOUSE")
                            game_state = scene_manager.current
                            atom_h.pos = pygame.Vector2(engine.HOUSE_SLEEP_SPOT)

        radio.update()

        # 2. Update the game state.

        if game_state == "CITY":
            target = car if in_car else atom

            # Update all traffic and pass the collision mask.
            # 1. Update traffic and police.
            for npc in npc_cars:
                # Pass the arguments used by traffic.py.
                npc.update(col_mask, car, npc_cars, traffic_state, frame_scale)
            if in_car:
                previous_car_pos = pygame.Vector2(car.pos)
                car.update(
                    keys,
                    col_mask,
                    True,
                    npc_cars,
                    frame_scale,
                    surface_map=world_bg,
                )
                atom.pos = pygame.Vector2(car.pos)
                travelled = previous_car_pos.distance_to(car.pos)
                if car.just_hit:
                    distance_since_crash = 0.0
                    current_drift_distance = 0.0
                else:
                    distance_since_crash += travelled
                    personal_records["distance_without_crash_m"] = max(
                        personal_records["distance_without_crash_m"],
                        distance_since_crash,
                    )
                    if car.is_drifting:
                        current_drift_distance += travelled
                        personal_records["longest_drift_m"] = max(
                            personal_records["longest_drift_m"],
                            current_drift_distance,
                        )
                    else:
                        current_drift_distance = 0.0
                personal_records["max_speed_kmh"] = max(
                    personal_records["max_speed_kmh"],
                    abs(car.speed) * 8,
                )
            else:
                atom.update(keys, col_mask, car, npc_cars, frame_scale)
                car.update(
                    keys,
                    col_mask,
                    False,
                    npc_cars,
                    frame_scale,
                    surface_map=world_bg,
                )

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
            engine.handle_car_audio(car, in_car, car_sfx, engine_chan, crash_chan)
            off_x, off_y = camera.follow(target.pos)
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

        # 3. Build and render explicit engine-owned scene layers.
        frame_renderer.begin_frame()
        if game_state == "CITY":
            headlights_on = in_car and manual_headlights

            def draw_city_background():
                screen.fill((30, 30, 30))
                screen.blit(world_bg, (off_x, off_y))

            def draw_city_world():
                car.draw(screen, off_x, off_y)
                engine.draw_car_smoke(screen, car, off_x, off_y)
                for npc in npc_cars:
                    npc.draw(screen, off_x, off_y)
                if in_car:
                    return

                screen_position = camera.world_to_screen(atom.pos)
                engine.draw_atom_character(
                    screen, screen_position.x, screen_position.y, atom_img, atom.angle
                )
                engine.draw_city_hints(screen, small_font, atom, car, t)
                if car.is_broken and atom.pos.distance_to(car.pos) < 100:
                    rendered = small_font.render(t["repair"], True, (255, 255, 255))
                    screen.blit(
                        rendered,
                        (WIDTH // 2 - rendered.get_width() // 2, HEIGHT // 2 + 100),
                    )
                    if car.repair_progress > 0:
                        pygame.draw.rect(
                            screen, (0, 0, 0),
                            (WIDTH // 2 - 100, HEIGHT // 2 + 140, 200, 15),
                        )
                        progress_width = int(200 * (car.repair_progress / 180))
                        pygame.draw.rect(
                            screen, (0, 120, 255),
                            (WIDTH // 2 - 100, HEIGHT // 2 + 140, progress_width, 15),
                        )
                        pygame.draw.rect(
                            screen, (255, 255, 255),
                            (WIDTH // 2 - 100, HEIGHT // 2 + 140, 200, 15), 2,
                        )

            def draw_city_lighting():
                ambient = engine.get_ambient_color(game_time)
                if ambient[3] > 0:
                    night_overlay.fill(ambient)
                    screen.blit(night_overlay, (0, 0))
                if headlights_on:
                    car.draw_headlights(screen, off_x, off_y, col_mask)

            def draw_city_ui():
                if in_car:
                    car.draw_speedometer(screen)
                engine.draw_gta_minimap(
                    screen,
                    original_nav_map,
                    target,
                    current_world_width,
                    current_world_height,
                    gps=gps,
                    labels=t,
                )
                if in_car:
                    radio_label = (
                        t["radio_off"]
                        if not radio.is_on
                        else t["radio_on"] if radio.is_playing else t["radio_paused"]
                    )
                    screen.blit(
                        small_font.render(
                            radio_label.format(
                                station=radio.station_name,
                                track=radio.track_name,
                            ),
                            True,
                            (255, 255, 255),
                        ),
                        (20, 50),
                    )

            frame_renderer.submit(engine.RenderLayer.BACKGROUND, draw_city_background)
            frame_renderer.submit(engine.RenderLayer.WORLD, draw_city_world)
            frame_renderer.submit(engine.RenderLayer.LIGHTING, draw_city_lighting)
            frame_renderer.submit(engine.RenderLayer.UI, draw_city_ui)
        else:
            def draw_house_background():
                engine.draw_house_scene(
                    screen, house_visual, house_info, atom_h, small_font, t
                )

            def draw_house_ui():
                if engine.is_at_sleep_spot(game_state, atom_h.pos):
                    sleep_text = small_font.render(t["sleep_save"], True, (255, 255, 255))
                    screen.blit(
                        sleep_text,
                        sleep_text.get_rect(center=(WIDTH // 2, HEIGHT - 80)),
                    )

            frame_renderer.submit(engine.RenderLayer.BACKGROUND, draw_house_background)
            frame_renderer.submit(engine.RenderLayer.UI, draw_house_ui)
        frame_renderer.render()

        # In-game clock.
        h, m = int(game_time / 60), int(game_time % 60)
        time_text = small_font.render(f"{h:02d}:{m:02d}", True, (255, 255, 255))
        screen.blit(time_text, (WIDTH - 100, 20))

        if show_debug:
            engine.draw_debug_coords(
                screen,
                (atom_h if game_state == "HOUSE" else target),
                game_state,
                clock.get_fps(),
            )
        if phone_y_offset < 449.0:
            engine.draw_mobile_phone(screen, money, game_time, small_font,
                                     current_app, phone_settings, phone_y_offset, money_history,
                                     current_lang_name)

        if wake_fade_started is not None:
            fade_progress = (time.perf_counter() - wake_fade_started) / 1.2
            if fade_progress >= 1:
                wake_fade_started = None
            else:
                wake_overlay.fill((0, 0, 0))
                wake_overlay.set_alpha(round(255 * (1 - fade_progress)))
                screen.blit(wake_overlay, (0, 0))

        pygame.display.flip()
        if sleep_requested:
            engine.fade_screen(screen, True)
            game_time = (game_time + 540) % 1440
            save_sleep_game()
            sleep_requested = False
            wake_fade_started = time.perf_counter()

    save_last_session_stats()
    return "EXIT"
