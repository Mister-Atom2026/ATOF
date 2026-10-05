import pygame
import sys

# Спроба імпорту глави
try:
    import chapters.ch1 as ch1
except ImportError:
    ch1 = None

# Ініціалізація
pygame.init()
pygame.mixer.init()
import engine
VERSION = "0.0.2"

# Налаштування екрану
WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(f"ATOF v{VERSION}")

# Кольори та шрифти
COLOR_BG = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_ORANGE = (212, 91, 18)
COLOR_BROWN = (60, 40, 30)

font_path = "static.ttf"
try:
    logo_font = pygame.font.Font(font_path, 150)
    menu_font = pygame.font.Font(font_path, 70)
except:
    logo_font = pygame.font.SysFont("Arial", 150)
    menu_font = pygame.font.SysFont("Arial", 70)

# Глобальні змінні
current_screen = "MAIN"
volume = 20
languages = ["English", "Українська", "Русский"]
lang_idx = 1

# Музика
try:
    pygame.mixer.music.load("6729032246362112.wav")
    pygame.mixer.music.set_volume(volume / 100)
    pygame.mixer.music.play(-1)
except:
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
            "vol": "Volume",
            "lang": "Language",
            "back": "BACK"
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
            "vol": "Гучність",
            "lang": "Мова",
            "back": "Назад"
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
            "vol": "Громкость",
            "lang": "Язык",
            "back": "Назад"
        }
    }
def draw_logo():
    ato_surf = logo_font.render("ATO", True, COLOR_ORANGE)
    f_surf = logo_font.render("F", True, COLOR_BROWN)
    screen.blit(ato_surf, (50, 50))
    screen.blit(f_surf, (50 + ato_surf.get_width(), 50))

def get_menu_rects(options):
    return [pygame.Rect(50, 250 + i * 100, 700, 70) for i in range(len(options))]

def main():
    global current_screen, volume, lang_idx
    selected_index = 0
    last_hover_key = None
    running = True

    while running:
        lang = languages[lang_idx]
        t = translations[lang]

        if current_screen == "MAIN":
            options = [t["play"], t["settings"], t["exit"]]
        else:
            options = [f"{t['vol']}: < {volume}% >", f"{t['lang']}: < {lang} >", t["back"]]

        screen.fill(COLOR_BG)
        draw_logo()

        rects = get_menu_rects(options)
        mouse_pos = pygame.mouse.get_pos()
        hovered_index = next((i for i, rect in enumerate(rects) if rect.collidepoint(mouse_pos)), None)
        hover_key = (current_screen, hovered_index)
        if hovered_index is not None and hover_key != last_hover_key:
            engine.play_menu_sound("hover")
        last_hover_key = hover_key

        for i, text in enumerate(options):
            color = COLOR_ORANGE if (rects[i].collidepoint(mouse_pos) or i == selected_index) else COLOR_WHITE
            surf = menu_font.render(text, True, color)
            screen.blit(surf, (50, 250 + i * 100))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(rects):
                    if rect.collidepoint(event.pos):
                        engine.play_menu_sound("click")
                        if current_screen == "MAIN":
                            if i == 0:  # PLAY
                                if ch1:
                                    # ПЕРЕДАЄМО ГУЧНІСТЬ ТА МОВУ
                                    game_settings = {"volume": volume, "lang_idx": lang_idx}

                                    pygame.mixer.music.stop()
                                    res = ch1.run(screen, game_settings)

                                    # ПРИЙМАЄМО ОНОВЛЕНІ НАЛАШТУВАННЯ
                                    volume = game_settings["volume"]
                                    lang_idx = game_settings["lang_idx"]

                                    if res == "EXIT":
                                        pygame.quit()
                                        sys.exit()

                                    pygame.mixer.music.play(-1)
                                    pygame.mixer.music.set_volume(volume / 100)

                            elif i == 1:
                                current_screen = "SETTINGS"
                                selected_index = 0
                            elif i == 2:
                                pygame.quit()
                                sys.exit()

                        else:  # SETTINGS кліки
                            if i == 0:
                                mid = rect.x + (rect.width / 2)
                                volume = min(100, volume + 5) if event.pos[0] > mid else max(0, volume - 5)
                                pygame.mixer.music.set_volume(volume / 100)
                            elif i == 1:
                                lang_idx = (lang_idx + 1) % len(languages)
                            elif i == 2:
                                current_screen = "MAIN"
                                selected_index = 1

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_index = (selected_index - 1) % len(options)
                    engine.play_menu_sound("hover")
                elif event.key == pygame.K_DOWN:
                    selected_index = (selected_index + 1) % len(options)
                    engine.play_menu_sound("hover")

                if current_screen == "SETTINGS":
                    if selected_index == 0:
                        if event.key == pygame.K_RIGHT:
                            volume = min(100, volume + 5)
                            engine.play_menu_sound("click")
                        if event.key == pygame.K_LEFT:
                            volume = max(0, volume - 5)
                            engine.play_menu_sound("click")
                        pygame.mixer.music.set_volume(volume / 100)
                    elif selected_index == 1:
                        if event.key == pygame.K_RIGHT:
                            lang_idx = (lang_idx + 1) % len(languages)
                            engine.play_menu_sound("click")
                        if event.key == pygame.K_LEFT:
                            lang_idx = (lang_idx - 1) % len(languages)
                            engine.play_menu_sound("click")

                if event.key == pygame.K_RETURN:
                    engine.play_menu_sound("click")
                    if current_screen == "MAIN":
                        if selected_index == 0:
                            if ch1:
                                game_settings = {"volume": volume, "lang_idx": lang_idx}
                                pygame.mixer.music.stop()
                                res = ch1.run(screen, game_settings)
                                volume = game_settings["volume"]
                                lang_idx = game_settings["lang_idx"]
                                if res == "EXIT": pygame.quit(); sys.exit()
                                pygame.mixer.music.play(-1)
                                pygame.mixer.music.set_volume(volume / 100)
                        elif selected_index == 1:
                            current_screen = "SETTINGS"
                            selected_index = 0
                        elif selected_index == 2:
                            pygame.quit()
                            sys.exit()
                    else:
                        if selected_index == 2:
                            current_screen = "MAIN"
                            selected_index = 1

        pygame.display.flip()

if __name__ == "__main__":
    main()