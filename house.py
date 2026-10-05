import pygame


class HousePlayer:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.speed = 4
        self.angle = 0
        self.image = None

        try:
            raw = pygame.image.load("characters/atom.png").convert_alpha()
            self.image = pygame.transform.scale(raw, (48, 48))
        except:
            print("Помилка: atom.png не знайдено для хати")

    def update(self, keys, col_mask):
        move = pygame.Vector2(0, 0)

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y = -1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y = 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x = -1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x = 1

        if move.length() == 0:
            return

        # нормалізація руху
        move = move.normalize() * self.speed
        new_pos = self.pos + move

        # --- перевірка колізії ---
        try:
            x = int(new_pos.x)
            y = int(new_pos.y)

            if 0 <= x < col_mask.get_width() and 0 <= y < col_mask.get_height():
                color = col_mask.get_at((x, y))[:3]

                # чорне = стіна
                if color != (0, 0, 0):
                    self.pos = new_pos
        except:
            pass

        # --- кут (нормальна версія, без цирку) ---
        if move.x > 0 and move.y == 0:
            self.angle = -90
        elif move.x < 0 and move.y == 0:
            self.angle = 90
        elif move.y > 0 and move.x == 0:
            self.angle = 0
        elif move.y < 0 and move.x == 0:
            self.angle = 180
        elif move.x > 0 and move.y > 0:
            self.angle = -45
        elif move.x < 0 and move.y > 0:
            self.angle = 45
        elif move.x > 0 and move.y < 0:
            self.angle = -135
        elif move.x < 0 and move.y < 0:
            self.angle = 135

    def draw(self, screen, offset_x, offset_y):
        if not self.image:
            return

        rotated = pygame.transform.rotate(self.image, -self.angle)
        rect = rotated.get_rect(
            center=(int(self.pos.x + offset_x), int(self.pos.y + offset_y))
        )
        screen.blit(rotated, rect)