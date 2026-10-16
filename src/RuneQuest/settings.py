"""Constantes del juego. Todo en coordenadas lógicas (se escala a la ventana)."""

# --- Carpetas de usuario (datos y logs) ---
APP_NAME = "RuneQuest"
LEGACY_APP_NAME = "Orbes"         # carpetas de versiones anteriores (se migra la BDD)

# --- Tablero ---
COLS = 8
ROWS = 14
CELL = 45
BOARD_X = 0
BOARD_Y = 100
BOARD_W = COLS * CELL            # 360
BOARD_H = ROWS * CELL            # 630

# --- Pantalla lógica (relación ~ iPhone en vertical) ---
LOGICAL_W = BOARD_W
LOGICAL_H = 760
FPS = 60

# --- Reglas ---
MIN_GROUP = 3                    # orbes conectados mínimos para poder reventar
POINTS_PER_PAIR = 10             # puntos = n * (n - 1) * POINTS_PER_PAIR
LEVEL_POINTS = 1000              # nivel n -> n+1 al llegar a LEVEL_POINTS * n*(n+1)/2 puntos

# --- Dificultad (ver game.level_params) ---
START_COLORS = 3                 # colores de los orbes nuevos en el nivel 1
MAX_COLORS = 6

# --- Colores ---
BG = (18, 20, 40)
PANEL = (28, 31, 62)
DANGER = (235, 70, 70)
WHITE = (240, 240, 250)
BLACK = (0, 0, 0)
ACCENT = (150, 210, 255)
BUTTON = (50, 60, 120)
BUTTON_EDGE = (120, 140, 230)

PALETTE = [
    (232, 84, 84),     # 0 rojo
    (84, 144, 240),    # 1 azul
    (96, 204, 112),    # 2 verde
    (242, 202, 72),    # 3 amarillo
    (172, 104, 222),   # 4 violeta
    (72, 202, 212),    # 5 turquesa
]
