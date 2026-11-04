# constants.py
WIDTH, HEIGHT = 1280, 720  # Keep the window size fixed.
MAP_EDIT_SCALE = 4
MAP_EDIT_WIDTH, MAP_EDIT_HEIGHT = 2202, 875
MAP_NATIVE_WIDTH, MAP_NATIVE_HEIGHT = 8808, 3500
WORLD_WIDTH, WORLD_HEIGHT = 1280 * 4, 720 * 4
FPS = 60

# Collision and navigation mask paths.
MAP_MINI = "Карта Вишневого.png"
MAP_COLLISION = "Нізя їздити.png"
MAP_NAV = "мона їздити.png"

# Colors used by the game logic.
C_WALL = (136, 0, 21)   # Red represents a wall.
C_ROAD = (255, 242, 0)  # Yellow represents the main road.
C_DIRT = (185, 122, 87) # Brown represents the dirt road.

# House sleep spot position.
HOUSE_SLEEP_SPOT = (147, 156)
HOUSE_SLEEP_RADIUS = 24
HOUSE_ENTRY_SPOT = (300, 70)

# City garage shown near the player's starting vehicle.
GARAGE_POS = (8013, 2484)
GARAGE_RADIUS = 150
NPC_TRAFFIC_LIMIT = 22
NPC_RESPAWN_SECONDS = 60.0
