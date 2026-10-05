# constants.py
WIDTH, HEIGHT = 1280, 720  # Keep the window size fixed.
WORLD_WIDTH, WORLD_HEIGHT = 1280 * 4, 720 * 4  # Full world-map dimensions.
FPS = 60

# Collision and navigation mask paths.
MAP_MINI = "Карта Вишневого.png"
MAP_COLLISION = "Нізя їздити.png"
MAP_NAV = "мона їздити.png"

# Colors used by the game logic.
C_WALL = (136, 0, 21)   # Red represents a wall.
C_ROAD = (255, 242, 0)  # Yellow represents the main road.
C_DIRT = (185, 122, 87) # Brown represents the dirt road.
