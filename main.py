import os
os.environ.setdefault("SDL_VIDEO_CENTERED", "1")

import pygame

from settings_manager import load_settings, load_statistics, save_settings

VERSION = "0.9.1-alpha.8"
RELEASE_NAME = "Alpha 8"
APP_SETTINGS = load_settings()

import constants

constants.WIDTH = APP_SETTINGS["video_width"]
constants.HEIGHT = APP_SETTINGS["video_height"]
constants.FPS = APP_SETTINGS["fps_limit"]
WIDTH, HEIGHT = constants.WIDTH, constants.HEIGHT

pygame.init()

try:
    pygame.mixer.init()
except pygame.error:
    pass

display_flags = pygame.RESIZABLE
try:
    screen = pygame.display.set_mode((WIDTH, HEIGHT), display_flags)
except pygame.error:
    APP_SETTINGS.update({"video_width": 1280, "video_height": 720})
    constants.WIDTH, constants.HEIGHT = 1280, 720
    WIDTH, HEIGHT = constants.WIDTH, constants.HEIGHT
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

pygame.display.set_caption("ATOF")

import engine
import open_world
import story_mission
from video_intro import play_intro_videos
LANGUAGES = list(engine.SUPPORTED_LANGUAGES)

COLOR_BG = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_ORANGE = (212, 91, 18)
COLOR_BROWN = (60, 40, 30)
def _menu_font_path(weight="regular"):
    try:
        return str(engine._resolve_font_path(weight))
    except Exception:
        return str(engine._FONT_PATH)

try:
    logo_font = pygame.font.Font(_menu_font_path("bold"), 150)
    menu_font = pygame.font.Font(_menu_font_path("semibold"), 70)
    settings_font = pygame.font.Font(_menu_font_path("regular"), 42)
except (pygame.error, OSError):
    logo_font = pygame.font.Font(None, 150)
    menu_font = pygame.font.Font(None, 70)
    settings_font = pygame.font.Font(None, 42)


def rebuild_fonts():
    global logo_font, menu_font, settings_font
    try:
        logo_font = pygame.font.Font(_menu_font_path("bold"), min(150, max(80, HEIGHT // 6)))
        menu_font = pygame.font.Font(_menu_font_path("semibold"), min(70, max(40, HEIGHT // 10)))
        settings_font = pygame.font.Font(_menu_font_path("regular"), min(42, max(24, HEIGHT // 17)))
    except (pygame.error, OSError):
        logo_font = pygame.font.Font(None, min(150, max(80, HEIGHT // 6)))
        menu_font = pygame.font.Font(None, min(70, max(40, HEIGHT // 10)))
        settings_font = pygame.font.Font(None, min(42, max(24, HEIGHT // 17)))

rebuild_fonts()

APP_STATS = load_statistics()
engine.configure_audio(APP_SETTINGS)


def load_and_play_menu_music():
    try:
        pygame.mixer.music.load("6729032246362112.wav")
        pygame.mixer.music.play(-1)
        engine.configure_audio(APP_SETTINGS)
    except (pygame.error, OSError):
        pass


load_and_play_menu_music()

translations = {
    "English": {
        "play": "Play",
        "settings": "Settings",
        "tutorial": "Tutorial",
        "story_mission": "Story Mission",
        "additional_content": "Additional Content",
        "exit": "Exit",
        "hint": "[F] Enter Car",
        "enter": "[E] Enter House",
        "exit_h": "[E] Exit House",
        "resume": "Resume",
        "stats": "Stats",
        "last_session_stats": "Last Session Statistics",
        "stats_money": "Balance: {money} ₭",
        "stats_time": "In-game time: {time}",
        "stats_treasures": "Treasures found: {treasures}",
        "stats_earned": "Total earned: {amount} ₭",
        "stats_spent": "Total spent: {amount} ₭",
        "stats_hint": "Press Esc or Enter to return",
        "load_save": "Load Save",
        "no_save": "No saved game was found",
        "stats_honor": "Honor: {value}",
        "stats_respect": "Respect: {value}",
        "fine": "Fine", "bribe": "Police bribe",
        "menu": "To Menu",
        "music_vol": "Music Volume",
        "npc_vol": "NPC Volume",
        "crash_vol": "Crash Volume",
        "button_vol": "Button Volume",
        "footsteps_vol": "Footsteps Volume",
        "volume": "Volume",
        "audio_hint": "Up/Down selects a sound; Left/Right adjusts it; Esc returns",
        "lang": "Language",
        "back": "Back",
        "confirm_q": "Exit the game?",
        "confirm_w": "The game will close.",
        "yes": "YES",
        "no": "NO",
    },
    "Українська": {
        "play": "Грати",
        "settings": "Налаштування",
        "tutorial": "Навчання",
        "story_mission": "Сюжетна місія",
        "additional_content": "Додатковий контент",
        "exit": "Вихід",
        "hint": "[F] Сісти в авто",
        "enter": "[E] Увійти в дім",
        "exit_h": "[E] Вийти з дому",
        "resume": "Продовжити",
        "stats": "Статистика",
        "last_session_stats": "Статистика останньої сесії",
        "stats_money": "Баланс: {money} ₭",
        "stats_time": "Ігровий час: {time}",
        "stats_treasures": "Знайдено скарбів: {treasures}",
        "stats_earned": "Всього зароблено: {amount} ₭",
        "stats_spent": "Всього витрачено: {amount} ₭",
        "stats_hint": "Натисніть Esc або Enter, щоб повернутися",
        "load_save": "Завантажити збереження",
        "no_save": "Збереження не знайдено",
        "stats_honor": "Честь: {value}",
        "stats_respect": "Повага: {value}",
        "fine": "Штраф", "bribe": "Хабар поліції",
        "menu": "В меню",
        "music_vol": "Гучність музики",
        "npc_vol": "Гучність НПС",
        "crash_vol": "Гучність аварій",
        "button_vol": "Гучність кнопок",
        "footsteps_vol": "Гучність кроків",
        "volume": "Гучність",
        "audio_hint": "←/→ змінює гучність; ↑/↓ обирає звук; Esc — назад",
        "lang": "Мова",
        "back": "Назад",
        "confirm_q": "Вийти з гри?",
        "confirm_w": "Гру буде закрито.",
        "yes": "ТАК",
        "no": "НІ",
    },
    "Русский": {
        "play": "Играть",
        "settings": "Настройки",
        "tutorial": "Обучение",
        "story_mission": "Сюжетная миссия",
        "additional_content": "Дополнительный контент",
        "exit": "Выход",
        "hint": "[F] Сесть в авто",
        "enter": "[E] Войти в дом",
        "exit_h": "[E] Выйти из дома",
        "resume": "Продолжить",
        "stats": "Статистика",
        "last_session_stats": "Статистика последней сессии",
        "stats_money": "Баланс: {money} ₭",
        "stats_time": "Игровое время: {time}",
        "stats_treasures": "Найдено сокровищ: {treasures}",
        "stats_earned": "Всего заработано: {amount} ₭",
        "stats_spent": "Всего потрачено: {amount} ₭",
        "stats_hint": "Нажмите Esc или Enter, чтобы вернуться",
        "load_save": "Загрузить сохранение",
        "no_save": "Сохранение не найдено",
        "stats_honor": "Честь: {value}",
        "stats_respect": "Уважение: {value}",
        "fine": "Штраф", "bribe": "Взятка полиции",
        "menu": "В меню",
        "music_vol": "Громкость музыки",
        "npc_vol": "Громкость НПС",
        "crash_vol": "Громкость аварий",
        "button_vol": "Громкость кнопок",
        "footsteps_vol": "Громкость шагов",
        "volume": "Громкость",
        "audio_hint": "←/→ меняет громкость; ↑/↓ выбирает звук; Esc — назад",
        "lang": "Язык",
        "back": "Назад",
        "confirm_q": "Выйти из игры?",
        "confirm_w": "Игра будет закрыта.",
        "yes": "ДА",
        "no": "НЕТ",
    },
    "Español": {
        "play": "Jugar",
        "settings": "Ajustes",
        "tutorial": "Tutorial",
        "story_mission": "Story Mission",
        "additional_content": "Contenido adicional",
        "exit": "Salir",
        "hint": "[F] Subir al coche",
        "enter": "[E] Entrar en casa",
        "exit_h": "[E] Salir de casa",
        "resume": "Reanudar",
        "stats": "Estadísticas",
        "last_session_stats": "Estadísticas de la última sesión",
        "stats_money": "Saldo: {money} ₭",
        "stats_time": "Hora del juego: {time}",
        "stats_treasures": "Tesoros encontrados: {treasures}",
        "stats_earned": "Total ganado: {amount} ₭",
        "stats_spent": "Total gastado: {amount} ₭",
        "stats_hint": "Pulsa Esc o Enter para volver",
        "load_save": "Cargar partida",
        "no_save": "No se encontró ninguna partida guardada",
        "stats_honor": "Honor: {value}",
        "stats_respect": "Respeto: {value}",
        "fine": "Multa", "bribe": "Soborno policial",
        "menu": "Volver al menú",
        "music_vol": "Volumen de la música",
        "npc_vol": "Volumen de los NPC",
        "crash_vol": "Volumen de choques",
        "button_vol": "Volumen de botones",
        "footsteps_vol": "Volumen de pasos",
        "volume": "Volumen",
        "audio_hint": "↑/↓ elegir sonido; ←/→ ajustar volumen; Esc para volver",
        "lang": "Idioma",
        "back": "Atrás",
        "confirm_q": "¿Salir del juego?",
        "confirm_w": "El juego se cerrará.",
        "yes": "SÍ",
        "no": "NO",
    },
    "Deutsch": {
        "play": "Spielen",
        "settings": "Einstellungen",
        "tutorial": "Tutorial",
        "story_mission": "Story Mission",
        "additional_content": "Zusatzinhalte",
        "exit": "Beenden",
        "hint": "[F] Ins Auto steigen",
        "enter": "[E] Haus betreten",
        "exit_h": "[E] Haus verlassen",
        "resume": "Fortsetzen",
        "stats": "Statistik",
        "last_session_stats": "Statistik der letzten Sitzung",
        "stats_money": "Kontostand: {money} ₭",
        "stats_time": "Uhrzeit im Spiel: {time}",
        "stats_treasures": "Gefundene Schätze: {treasures}",
        "stats_earned": "Insgesamt verdient: {amount} ₭",
        "stats_spent": "Insgesamt ausgegeben: {amount} ₭",
        "stats_hint": "Esc oder Enter drücken, um zurückzukehren",
        "load_save": "Spielstand laden",
        "no_save": "Kein Spielstand gefunden",
        "stats_honor": "Ehre: {value}",
        "stats_respect": "Ansehen: {value}",
        "fine": "Bußgeld", "bribe": "Polizei-Bestechung",
        "menu": "Zum Hauptmenü",
        "music_vol": "Musiklautstärke",
        "npc_vol": "NPC-Lautstärke",
        "crash_vol": "Lautstärke für Unfälle",
        "button_vol": "Tastenlautstärke",
        "footsteps_vol": "Schrittlautstärke",
        "volume": "Lautstärke",
        "audio_hint": "↑/↓ Ton wählen; ←/→ Lautstärke ändern; Esc zurück",
        "lang": "Sprache",
        "back": "Zurück",
        "confirm_q": "Spiel beenden?",
        "confirm_w": "Das Spiel wird geschlossen.",
        "yes": "JA",
        "no": "NEIN",
    },
    "Français": {
        "play": "Jouer",
        "settings": "Paramètres",
        "tutorial": "Tutoriel",
        "story_mission": "Mission histoire",
        "additional_content": "Contenu supplémentaire",
        "exit": "Quitter",
        "hint": "[F] Monter en voiture",
        "enter": "[E] Entrer dans la maison",
        "exit_h": "[E] Sortir de la maison",
        "resume": "Reprendre",
        "stats": "Statistiques",
        "last_session_stats": "Statistiques de la dernière session",
        "stats_money": "Solde : {money} ₭",
        "stats_time": "Heure en jeu : {time}",
        "stats_treasures": "Trésors trouvés : {treasures}",
        "stats_earned": "Total gagné : {amount} ₭",
        "stats_spent": "Total dépensé : {amount} ₭",
        "stats_hint": "Appuyez sur Échap ou Entrée pour revenir",
        "load_save": "Charger la sauvegarde",
        "no_save": "Aucune sauvegarde trouvée",
        "stats_honor": "Honneur : {value}",
        "stats_respect": "Respect : {value}",
        "fine": "Amende", "bribe": "Pot-de-vin policier",
        "menu": "Menu principal",
        "music_vol": "Volume de la musique",
        "npc_vol": "Volume des PNJ",
        "crash_vol": "Volume des collisions",
        "button_vol": "Volume des boutons",
        "footsteps_vol": "Volume des pas",
        "volume": "Volume",
        "audio_hint": "↑/↓ choisir le son ; ←/→ régler le volume ; Échap pour revenir",
        "lang": "Langue",
        "back": "Retour",
        "confirm_q": "Quitter le jeu ?",
        "confirm_w": "Le jeu va se fermer.",
        "yes": "OUI",
        "no": "NON",
    },
}

_RECORD_TRANSLATIONS = {
    "English": {
        "stats_max_speed": "Top speed: {value} km/h",
        "stats_longest_drift": "Longest drift: {value} m",
        "stats_no_crash": "Longest drive without a crash: {value} m",
    },
    "Українська": {
        "stats_max_speed": "Максимальна швидкість: {value} км/год",
        "stats_longest_drift": "Найдовший занос: {value} м",
        "stats_no_crash": "Найдовша поїздка без аварій: {value} м",
    },
    "Русский": {
        "stats_max_speed": "Максимальная скорость: {value} км/ч",
        "stats_longest_drift": "Самый длинный занос: {value} м",
        "stats_no_crash": "Самая длинная поездка без аварий: {value} м",
    },
    "Español": {
        "stats_max_speed": "Velocidad máxima: {value} km/h",
        "stats_longest_drift": "Derrape más largo: {value} m",
        "stats_no_crash": "Trayecto más largo sin choque: {value} m",
    },
    "Deutsch": {
        "stats_max_speed": "Höchstgeschwindigkeit: {value} km/h",
        "stats_longest_drift": "Längster Drift: {value} m",
        "stats_no_crash": "Längste Fahrt ohne Unfall: {value} m",
    },
    "Français": {
        "stats_max_speed": "Vitesse maximale : {value} km/h",
        "stats_longest_drift": "Dérapage le plus long : {value} m",
        "stats_no_crash": "Trajet le plus long sans accident : {value} m",
    },
}
for _language, _labels in _RECORD_TRANSLATIONS.items():
    translations[_language].update(_labels)

_VIDEO_TRANSLATIONS = {
    "English": {
        "video": "Video", "window_mode": "Window mode", "window_mode_value": "Resizable",
        "resolution": "Resolution", "fps_limit": "Frame rate limit", "fps_unlimited": "Unlimited",
        "video_hint": "FPS is not monitor Hz. Use □ in the title bar to maximize.",
    },
    "Українська": {
        "video": "Відео", "window_mode": "Режим вікна", "window_mode_value": "Змінний розмір",
        "resolution": "Роздільність", "fps_limit": "Ліміт кадрів (FPS)", "fps_unlimited": "Без обмежень",
        "video_hint": "FPS — не герци монітора. Натисніть □ у заголовку, щоб розгорнути вікно.",
    },
    "Русский": {
        "video": "Видео", "window_mode": "Режим окна", "window_mode_value": "Изменяемый размер",
        "resolution": "Разрешение", "fps_limit": "Лимит кадров (FPS)", "fps_unlimited": "Без ограничений",
        "video_hint": "FPS — не герцы монитора. Нажмите □ в заголовке, чтобы развернуть окно.",
    },
    "Español": {
        "video": "Vídeo", "window_mode": "Modo de ventana", "window_mode_value": "Redimensionable",
        "resolution": "Resolución", "fps_limit": "Límite de fotogramas (FPS)", "fps_unlimited": "Sin límite",
        "video_hint": "FPS no son los Hz. Usa □ en la barra superior para maximizar.",
    },
    "Deutsch": {
        "video": "Video", "window_mode": "Fenstermodus", "window_mode_value": "Größe änderbar",
        "resolution": "Auflösung", "fps_limit": "Bildratenlimit (FPS)", "fps_unlimited": "Unbegrenzt",
        "video_hint": "FPS sind nicht Monitor-Hz. Mit □ in der Titelleiste maximieren.",
    },
    "Français": {
        "video": "Vidéo", "window_mode": "Mode fenêtre", "window_mode_value": "Redimensionnable",
        "resolution": "Résolution", "fps_limit": "Limite d’images (FPS)", "fps_unlimited": "Illimitée",
        "video_hint": "Les FPS ne sont pas les Hz. Cliquez sur □ dans la barre de titre.",
    },
}
for _language, _labels in _VIDEO_TRANSLATIONS.items():
    translations[_language].update(_labels)

_CONTROLS_TRANSLATIONS = {
    "English": {
        "controls_up": "Up / Forward",
        "controls_down": "Down / Brake",
        "controls_left": "Left",
        "controls_right": "Right",
        "controls_interact": "Interact (E)",
        "controls_enter_vehicle": "Enter/Exit vehicle (F)",
        "controls_reload": "Reload (R)",
        "controls_sprint": "Sprint (Shift)",
        "controls_map": "Map (Tab)",
        "controls_phone": "Phone (P)",
        "controls_handbrake": "Handbrake (Space)",
        "controls_quick_nav": "Quick locations (K)",
        "controls_journal": "Journal (J)",
        "controls_hint": "Enter: rebind, Esc: back",
    },
    "Українська": {
        "controls_up": "Вгору / Вперед",
        "controls_down": "Вниз / Гальмо",
        "controls_left": "Вліво",
        "controls_right": "Вправо",
        "controls_interact": "Взаємодія (E)",
        "controls_enter_vehicle": "Сісти/вийти з авто (F)",
        "controls_reload": "Перезарядка (R)",
        "controls_sprint": "Біг (Shift)",
        "controls_map": "Мапа (Tab)",
        "controls_phone": "Телефон (P)",
        "controls_handbrake": "Ручник (Space)",
        "controls_quick_nav": "Швидкі точки (K)",
        "controls_journal": "Журнал (J)",
        "controls_hint": "Enter: змінити, Esc: назад",
    },
    "Русский": {
        "controls_up": "Вверх / Вперед",
        "controls_down": "Вниз / Тормоз",
        "controls_left": "Влево",
        "controls_right": "Вправо",
        "controls_interact": "Взаимодействие (E)",
        "controls_enter_vehicle": "Сесть/выйти из авто (F)",
        "controls_reload": "Перезарядка (R)",
        "controls_sprint": "Бег (Shift)",
        "controls_map": "Карта (Tab)",
        "controls_phone": "Телефон (P)",
        "controls_handbrake": "Ручник (Space)",
        "controls_quick_nav": "Быстрые точки (K)",
        "controls_journal": "Журнал (J)",
        "controls_hint": "Enter: изменить, Esc: назад",
    },
    "Español": {
        "controls_up": "Arriba / Adelante",
        "controls_down": "Abajo / Frenar",
        "controls_left": "Izquierda",
        "controls_right": "Derecha",
        "controls_interact": "Interactuar (E)",
        "controls_enter_vehicle": "Entrar/salir del coche (F)",
        "controls_reload": "Recargar (R)",
        "controls_sprint": "Correr (Shift)",
        "controls_map": "Mapa (Tab)",
        "controls_phone": "Teléfono (P)",
        "controls_handbrake": "Freno de mano (Space)",
        "controls_quick_nav": "Puntos rápidos (K)",
        "controls_journal": "Diario (J)",
        "controls_hint": "Enter: reasignar, Esc: volver",
    },
    "Deutsch": {
        "controls_up": "Oben / Vorwärts",
        "controls_down": "Unten / Bremsen",
        "controls_left": "Links",
        "controls_right": "Rechts",
        "controls_interact": "Interagieren (E)",
        "controls_enter_vehicle": "Ein-/Aussteigen (F)",
        "controls_reload": "Nachladen (R)",
        "controls_sprint": "Sprinten (Shift)",
        "controls_map": "Karte (Tab)",
        "controls_phone": "Telefon (P)",
        "controls_handbrake": "Handbremse (Space)",
        "controls_quick_nav": "Schnellpunkte (K)",
        "controls_journal": "Journal (J)",
        "controls_hint": "Enter: neu belegen, Esc: zurück",
    },
    "Français": {
        "controls_up": "Haut / Avant",
        "controls_down": "Bas / Frein",
        "controls_left": "Gauche",
        "controls_right": "Droite",
        "controls_interact": "Interagir (E)",
        "controls_enter_vehicle": "Monter/descendre de voiture (F)",
        "controls_reload": "Recharger (R)",
        "controls_sprint": "Courir (Shift)",
        "controls_map": "Carte (Tab)",
        "controls_phone": "Téléphone (P)",
        "controls_handbrake": "Frein à main (Space)",
        "controls_quick_nav": "Points rapides (K)",
        "controls_journal": "Journal (J)",
        "controls_hint": "Entrée : réattribuer, Échap : retour",
    },
}
for _language, _labels in _CONTROLS_TRANSLATIONS.items():
    translations[_language].update(_labels)


def draw_logo():
    atom_surface = logo_font.render("ATO", True, COLOR_ORANGE)
    f_surface = logo_font.render("F", True, COLOR_BROWN)
    screen.blit(atom_surface, (50, 50))
    screen.blit(f_surface, (50 + atom_surface.get_width(), 50))


def get_menu_rects(options):
    screen_height = screen.get_height()
    step = min(100, max(76, (screen_height - 190) // max(1, len(options))))
    first_y = max(180, (screen_height - (step * (len(options) - 1) + 70)) // 2)
    return [pygame.Rect(50, first_y + index * step, 700, 70) for index, _ in enumerate(options)]


def get_menu_hitboxes(options, layout_rects):
    """Create click targets around the visible menu labels, not arbitrary rows."""
    hitboxes = []
    for option, layout_rect in zip(options, layout_rects):
        label_rect = menu_font.render(option, True, COLOR_WHITE).get_rect(
            topleft=(50, layout_rect.y)
        )
        hitboxes.append(label_rect.inflate(32, 24).move(0, -18))
    return hitboxes


def apply_video_settings():
    global screen, WIDTH, HEIGHT, logo_font, menu_font, settings_font
    screen = engine.apply_video_settings(APP_SETTINGS)
    WIDTH, HEIGHT = screen.get_size()
    pygame.display.set_caption("ATOF")
    rebuild_fonts()
    save_settings(APP_SETTINGS)


def launch_open_world(continue_game):
    global screen, WIDTH, HEIGHT
    pygame.mixer.music.stop()
    result = open_world.run(
        screen,
        APP_SETTINGS,
        continue_game=continue_game,
    )
    screen = pygame.display.get_surface()
    WIDTH, HEIGHT = screen.get_size()
    rebuild_fonts()
    APP_STATS.clear()
    APP_STATS.update(load_statistics())
    engine.configure_audio(APP_SETTINGS)
    if result == "EXIT":
        return False
    load_and_play_menu_music()
    return True


def start_open_world():
    game_save = engine.load_game_save()
    return launch_open_world(continue_game=game_save is not None)


def activate_menu_option(index):
    global screen, WIDTH, HEIGHT
    if index == 0:
        return start_open_world()

    if index == 1:
        engine.fade_menu_out(screen)
        result = engine.settings_sub_menu(
            screen,
            settings_font,
            APP_SETTINGS,
            translations,
            LANGUAGES,
            on_change=save_settings,
            fade_in=True,
        )
        if result == "VIDEO_CHANGED":
            apply_video_settings()
        return "BACK" if result != "EXIT" else "EXIT"

    if index == 2:
        engine.fade_menu_out(screen)
        result = engine.tutorial_menu(
            screen,
            settings_font,
            APP_SETTINGS,
            translations,
            LANGUAGES,
            fade_in=True,
        )
        return "BACK" if result != "EXIT" else "EXIT"

    if index == 3:
        pygame.mixer.music.stop()
        result = story_mission.run_story_mission(screen, APP_SETTINGS)
        screen = pygame.display.get_surface()
        rebuild_fonts()
        engine.configure_audio(APP_SETTINGS)
        load_and_play_menu_music()
        return "BACK" if result != "EXIT" else "EXIT"

    if index == 4:
        language = LANGUAGES[APP_SETTINGS["lang_idx"]]
        text = dict(translations[language])
        text["stats_title"] = text["last_session_stats"]
        engine.fade_menu_out(screen)
        result = engine.stats_dialog(screen, settings_font, settings_font, text, APP_STATS, fade_in=True)
        return "BACK" if result != "EXIT" else "EXIT"

    language = LANGUAGES[APP_SETTINGS["lang_idx"]]
    return False if engine.confirm_dialog(
        screen,
        settings_font,
        settings_font,
        translations[language],
    ) else "BACK"


def main():
    global screen, WIDTH, HEIGHT
    selected_index = 0
    last_hover_key = None
    clock = pygame.time.Clock()
    needs_fade_in = False

    try:
        if not play_intro_videos(screen):
            return
        while True:
            language = LANGUAGES[APP_SETTINGS["lang_idx"]]
            text = translations[language]
            options = [text["play"], text["settings"], text.get("tutorial", "Tutorial"), text.get("story_mission", "Story Mission"), text["additional_content"], text["exit"]]

            screen.fill(COLOR_BG)
            draw_logo()
            rects = get_menu_rects(options)
            hitboxes = get_menu_hitboxes(options, rects)
            mouse_pos = pygame.mouse.get_pos()
            hovered_index = next(
                (index for index, rect in enumerate(hitboxes) if rect.collidepoint(mouse_pos)),
                None,
            )
            hover_key = (hovered_index,)
            if hovered_index is not None and hover_key != last_hover_key:
                engine.play_menu_sound("hover")
            last_hover_key = hover_key

            for index, option in enumerate(options):
                highlighted = hitboxes[index].collidepoint(mouse_pos) or index == selected_index
                color = COLOR_ORANGE if highlighted else COLOR_WHITE
                rendered = menu_font.render(option, True, color)
                screen.blit(rendered, (50, rects[index].y))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

                if event.type == pygame.VIDEORESIZE:
                    screen = engine.apply_window_resize(event.size, APP_SETTINGS)
                    WIDTH, HEIGHT = screen.get_size()
                    rebuild_fonts()
                    save_settings(APP_SETTINGS)

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for index, rect in enumerate(hitboxes):
                        if rect.collidepoint(event.pos):
                            selected_index = index
                            engine.play_menu_sound("click")
                            result = activate_menu_option(index)
                            if result is False or result == "EXIT":
                                return
                            if result == "BACK":
                                needs_fade_in = True
                            break

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        selected_index = (selected_index - 1) % len(options)
                        engine.play_menu_sound("hover")
                    elif event.key == pygame.K_DOWN:
                        selected_index = (selected_index + 1) % len(options)
                        engine.play_menu_sound("hover")
                    elif event.key == pygame.K_RETURN:
                        engine.play_menu_sound("click")
                        result = activate_menu_option(selected_index)
                        if result is False or result == "EXIT":
                            return
                        if result == "BACK":
                            needs_fade_in = True

            if needs_fade_in:
                engine.fade_menu_in(screen)
                needs_fade_in = False
            else:
                pygame.display.flip()
            clock.tick(constants.FPS)
    finally:
        try:
            save_settings(APP_SETTINGS)
        finally:
            pygame.quit()


if __name__ == "__main__":
    main()
