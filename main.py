import os
os.environ.setdefault("SDL_VIDEO_CENTERED", "1")

import pygame

from settings_manager import load_settings, load_statistics, save_settings

VERSION = "0.6.0-rc.1"
RELEASE_NAME = "Driver Inferno"
LANGUAGES = ["English", "Українська", "Русский", "Español", "Deutsch", "Français"]
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

pygame.display.set_caption(f"ATOF v{VERSION} — {RELEASE_NAME}")

import engine

# Load the chapter after applying the saved display size, because it imports
# WIDTH, HEIGHT, and FPS from constants.py.
try:
    import chapters.ch1 as ch1
except ImportError:
    ch1 = None

COLOR_BG = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_ORANGE = (212, 91, 18)
COLOR_BROWN = (60, 40, 30)
font_path = "static.ttf"
try:
    logo_font = pygame.font.Font(font_path, 150)
    menu_font = pygame.font.Font(font_path, 70)
    settings_font = pygame.font.Font(font_path, 42)
except (pygame.error, OSError):
    logo_font = pygame.font.SysFont("Arial", 150)
    menu_font = pygame.font.SysFont("Arial", 70)
    settings_font = pygame.font.SysFont("Arial", 42)


def rebuild_fonts():
    global logo_font, menu_font, settings_font
    try:
        logo_font = pygame.font.Font(font_path, min(150, max(80, HEIGHT // 6)))
        menu_font = pygame.font.Font(font_path, min(70, max(40, HEIGHT // 10)))
        settings_font = pygame.font.Font(font_path, min(42, max(24, HEIGHT // 17)))
    except (pygame.error, OSError):
        logo_font = pygame.font.SysFont("Arial", min(150, max(80, HEIGHT // 6)))
        menu_font = pygame.font.SysFont("Arial", min(70, max(40, HEIGHT // 10)))
        settings_font = pygame.font.SysFont("Arial", min(42, max(24, HEIGHT // 17)))

rebuild_fonts()

APP_STATS = load_statistics()
engine.configure_audio(APP_SETTINGS)

try:
    pygame.mixer.music.load("6729032246362112.wav")
    pygame.mixer.music.play(-1)
    engine.configure_audio(APP_SETTINGS)
except (pygame.error, OSError):
    print("Файл музики не знайдено!")

translations = {
    "English": {
        "play": "Play",
        "settings": "Settings",
        "additional_content": "Additional Content",
        "exit": "Exit",
        "hint": "[F] Enter Car",
        "enter": "[E] Enter House",
        "exit_h": "[E] Exit House",
        "resume": "Resume",
        "stats": "Stats",
        "last_session_stats": "Last Session Statistics",
        "stats_money": "Balance: {money} UAH",
        "stats_time": "In-game time: {time}",
        "stats_treasures": "Treasures found: {treasures}",
        "stats_earned": "Total earned: {amount} UAH",
        "stats_spent": "Total spent: {amount} UAH",
        "stats_hint": "Press Esc or Enter to return",
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
        "additional_content": "Додатковий контент",
        "exit": "Вихід",
        "hint": "[F] Сісти в авто",
        "enter": "[E] Увійти в дім",
        "exit_h": "[E] Вийти з дому",
        "resume": "Продовжити",
        "stats": "Статистика",
        "last_session_stats": "Статистика останньої сесії",
        "stats_money": "Баланс: {money} UAH",
        "stats_time": "Ігровий час: {time}",
        "stats_treasures": "Знайдено скарбів: {treasures}",
        "stats_earned": "Всього зароблено: {amount} UAH",
        "stats_spent": "Всього витрачено: {amount} UAH",
        "stats_hint": "Натисніть Esc або Enter, щоб повернутися",
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
        "additional_content": "Дополнительный контент",
        "exit": "Выход",
        "hint": "[F] Сесть в авто",
        "enter": "[E] Войти в дом",
        "exit_h": "[E] Выйти из дома",
        "resume": "Продолжить",
        "stats": "Статистика",
        "last_session_stats": "Статистика последней сессии",
        "stats_money": "Баланс: {money} UAH",
        "stats_time": "Игровое время: {time}",
        "stats_treasures": "Найдено сокровищ: {treasures}",
        "stats_earned": "Всего заработано: {amount} UAH",
        "stats_spent": "Всего потрачено: {amount} UAH",
        "stats_hint": "Нажмите Esc или Enter, чтобы вернуться",
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
        "additional_content": "Contenido adicional",
        "exit": "Salir",
        "hint": "[F] Subir al coche",
        "enter": "[E] Entrar en casa",
        "exit_h": "[E] Salir de casa",
        "resume": "Reanudar",
        "stats": "Estadísticas",
        "last_session_stats": "Estadísticas de la última sesión",
        "stats_money": "Saldo: {money} UAH",
        "stats_time": "Hora del juego: {time}",
        "stats_treasures": "Tesoros encontrados: {treasures}",
        "stats_earned": "Total ganado: {amount} UAH",
        "stats_spent": "Total gastado: {amount} UAH",
        "stats_hint": "Pulsa Esc o Enter para volver",
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
        "additional_content": "Zusatzinhalte",
        "exit": "Beenden",
        "hint": "[F] Ins Auto steigen",
        "enter": "[E] Haus betreten",
        "exit_h": "[E] Haus verlassen",
        "resume": "Fortsetzen",
        "stats": "Statistik",
        "last_session_stats": "Statistik der letzten Sitzung",
        "stats_money": "Kontostand: {money} UAH",
        "stats_time": "Uhrzeit im Spiel: {time}",
        "stats_treasures": "Gefundene Schätze: {treasures}",
        "stats_earned": "Insgesamt verdient: {amount} UAH",
        "stats_spent": "Insgesamt ausgegeben: {amount} UAH",
        "stats_hint": "Esc oder Enter drücken, um zurückzukehren",
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
        "additional_content": "Contenu supplémentaire",
        "exit": "Quitter",
        "hint": "[F] Monter en voiture",
        "enter": "[E] Entrer dans la maison",
        "exit_h": "[E] Sortir de la maison",
        "resume": "Reprendre",
        "stats": "Statistiques",
        "last_session_stats": "Statistiques de la dernière session",
        "stats_money": "Solde : {money} UAH",
        "stats_time": "Heure en jeu : {time}",
        "stats_treasures": "Trésors trouvés : {treasures}",
        "stats_earned": "Total gagné : {amount} UAH",
        "stats_spent": "Total dépensé : {amount} UAH",
        "stats_hint": "Appuyez sur Échap ou Entrée pour revenir",
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


def apply_video_settings():
    global screen, WIDTH, HEIGHT, logo_font, menu_font, settings_font
    screen = engine.apply_video_settings(APP_SETTINGS)
    WIDTH, HEIGHT = screen.get_size()
    pygame.display.set_caption(f"ATOF v{VERSION} — {RELEASE_NAME}")
    rebuild_fonts()
    save_settings(APP_SETTINGS)


def activate_menu_option(index):
    global screen, WIDTH, HEIGHT
    if index == 0:
        if ch1 is None:
            return True
        pygame.mixer.music.stop()
        result = ch1.run(screen, APP_SETTINGS)
        screen = pygame.display.get_surface()
        WIDTH, HEIGHT = screen.get_size()
        rebuild_fonts()
        APP_STATS.clear()
        APP_STATS.update(load_statistics())
        engine.configure_audio(APP_SETTINGS)
        if result == "EXIT":
            return False
        pygame.mixer.music.load("6729032246362112.wav")
        pygame.mixer.music.play(-1)
        engine.configure_audio(APP_SETTINGS)
        return True

    if index == 1:
        result = engine.settings_sub_menu(
            screen,
            settings_font,
            APP_SETTINGS,
            translations,
            LANGUAGES,
            on_change=save_settings,
        )
        if result == "VIDEO_CHANGED":
            apply_video_settings()
        return result != "EXIT"

    if index == 2:
        language = LANGUAGES[APP_SETTINGS["lang_idx"]]
        text = dict(translations[language])
        text["stats_title"] = text["last_session_stats"]
        result = engine.stats_dialog(screen, settings_font, settings_font, text, APP_STATS)
        return result != "EXIT"

    language = LANGUAGES[APP_SETTINGS["lang_idx"]]
    return not engine.confirm_dialog(
        screen,
        settings_font,
        settings_font,
        translations[language],
    )


def main():
    global screen, WIDTH, HEIGHT
    selected_index = 0
    last_hover_key = None
    clock = pygame.time.Clock()

    try:
        while True:
            language = LANGUAGES[APP_SETTINGS["lang_idx"]]
            text = translations[language]
            options = [text["play"], text["settings"], text["additional_content"], text["exit"]]

            screen.fill(COLOR_BG)
            draw_logo()
            rects = get_menu_rects(options)
            mouse_pos = pygame.mouse.get_pos()
            hovered_index = next(
                (index for index, rect in enumerate(rects) if rect.collidepoint(mouse_pos)),
                None,
            )
            hover_key = (hovered_index,)
            if hovered_index is not None and hover_key != last_hover_key:
                engine.play_menu_sound("hover")
            last_hover_key = hover_key

            for index, option in enumerate(options):
                highlighted = rects[index].collidepoint(mouse_pos) or index == selected_index
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
                    for index, rect in enumerate(rects):
                        if rect.collidepoint(event.pos):
                            selected_index = index
                            engine.play_menu_sound("click")
                            if not activate_menu_option(index):
                                return
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
                        if not activate_menu_option(selected_index):
                            return

            pygame.display.flip()
            clock.tick(constants.FPS)
    finally:
        try:
            save_settings(APP_SETTINGS)
        finally:
            pygame.quit()


if __name__ == "__main__":
    main()
