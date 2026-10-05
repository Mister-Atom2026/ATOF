import pygame

# Try to import the game chapter.
try:
    import chapters.ch1 as ch1
except ImportError:
    ch1 = None

from settings_manager import load_settings, save_settings

pygame.init()
pygame.mixer.init()
import engine

VERSION = "0.0.3"
WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(f"ATOF v{VERSION}")

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

LANGUAGES = ["English", "Українська", "Русский"]
APP_SETTINGS = load_settings()
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
        "exit": "Exit",
        "hint": "[F] Enter Car",
        "enter": "[E] Enter House",
        "exit_h": "[E] Exit House",
        "resume": "Resume",
        "stats": "Stats",
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
        "exit": "Вихід",
        "hint": "[F] Сісти в авто",
        "enter": "[E] Увійти в дім",
        "exit_h": "[E] Вийти з дому",
        "resume": "Продовжити",
        "stats": "Статистика",
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
        "exit": "Выход",
        "hint": "[F] Сесть в авто",
        "enter": "[E] Войти в дом",
        "exit_h": "[E] Выйти из дома",
        "resume": "Продолжить",
        "stats": "Статистика",
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
}


def draw_logo():
    atom_surface = logo_font.render("ATO", True, COLOR_ORANGE)
    f_surface = logo_font.render("F", True, COLOR_BROWN)
    screen.blit(atom_surface, (50, 50))
    screen.blit(f_surface, (50 + atom_surface.get_width(), 50))


def get_menu_rects(options):
    return [pygame.Rect(50, 250 + index * 100, 700, 70) for index, _ in enumerate(options)]


def activate_menu_option(index):
    if index == 0:
        if ch1 is None:
            return True
        pygame.mixer.music.stop()
        result = ch1.run(screen, APP_SETTINGS)
        engine.configure_audio(APP_SETTINGS)
        if result == "EXIT":
            return False
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
        return result != "EXIT"

    language = LANGUAGES[APP_SETTINGS["lang_idx"]]
    return not engine.confirm_dialog(
        screen,
        settings_font,
        settings_font,
        translations[language],
    )


def main():
    selected_index = 0
    last_hover_key = None

    try:
        while True:
            language = LANGUAGES[APP_SETTINGS["lang_idx"]]
            text = translations[language]
            options = [text["play"], text["settings"], text["exit"]]

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
                screen.blit(rendered, (50, 250 + index * 100))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

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
    finally:
        try:
            save_settings(APP_SETTINGS)
        finally:
            pygame.quit()


if __name__ == "__main__":
    main()
