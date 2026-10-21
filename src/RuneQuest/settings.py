"""Constantes del juego. Todo en coordenadas lógicas (se escala a la ventana)."""

# --- Carpetas de usuario (datos y logs) ---
APP_NAME = "RuneQuest"
LEGACY_APP_NAME = "RuneQuest"         # carpetas de versiones anteriores (se migra la BDD)

# --- Game Center: debe coincidir con el ID de la clasificación en App Store Connect ---
GAMECENTER_LEADERBOARD_ID = "runequest_highscores"

# --- Tablero ---
COLS = 8
ROWS = 14
CELL = 45
BOARD_X = 0
BOARD_Y = 100
BOARD_W = COLS * CELL            # 360
COL_SHIFT = CELL // 2            # las columnas impares están desplazadas media celda hacia abajo
BOARD_H = ROWS * CELL + COL_SHIFT  # 652

# --- Pantalla lógica (relación ~ iPhone en vertical) ---
LOGICAL_W = BOARD_W
LOGICAL_H = 760
FPS = 60
ANIM_RATE = 12.0                 # velocidad con que los orbes llegan a su sitio (mayor = más rápido)
LINK_ALPHA = 135                 # opacidad (0-255) de los enlaces entre orbes de un grupo
LINK_WIDTH = int(CELL * 0.62)    # grosor de esos enlaces
RAIN_ANIM_RATE = 6.0             # la lluvia de orbes cae a la mitad de velocidad

# --- Modos de juego (de momento todos usan las mismas reglas) ---
GAME_MODES = ("classic", "fast", "surprise")

# --- Ayuda visual sobre los orbes: ninguna, formas geométricas o runas nórdicas ---
ASSIST_MODES = ("none", "geo", "runes")

# --- Reglas ---
MIN_GROUP = 3                    # orbes conectados mínimos para poder reventar
POINTS_PER_PAIR = 10             # puntos = n * (n - 1) * POINTS_PER_PAIR
COLOR_CLEAR_BONUS = 5000         # eliminar todos los orbes de un color
BOARD_CLEAR_BONUS = 10000        # dejar el tablero sin ningún orbe
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
BUTTON_PRESSED = (28, 34, 72)     # botón mientras se mantiene pulsado
BUTTON_EDGE = (120, 140, 230)

PALETTE = [
    (232, 84, 84),     # 0 rojo
    (84, 144, 240),    # 1 azul
    (96, 204, 112),    # 2 verde
    (242, 202, 72),    # 3 amarillo
    (172, 104, 222),   # 4 violeta
    (72, 202, 212),    # 5 turquesa
]
