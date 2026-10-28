"""Constantes del juego. Todo en coordenadas lógicas (se escala a la ventana)."""

# --- Carpetas de usuario (datos y logs) ---
APP_NAME = "RuneQuest"
LEGACY_APP_NAME = "RuneQuest"         # carpetas de versiones anteriores (se migra la BDD)

# --- Game Center: debe coincidir con el ID de la clasificación en App Store Connect ---
# Una clasificación por modo de juego.
GAMECENTER_LEADERBOARDS = {
    "classic": "runequest_classic",
    "fast": "runequest_fast",
    "surprise": "runequest_surprise",
}
TOP_SCORES = 15                  # puntuaciones que muestra la pantalla Puntuaciones (por modo)

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
LINKS_DELAY_AFTER_RAIN = 0.5     # segundos sin enlaces tras terminar de caer la lluvia
LINKS_FADE_IN = 0.25             # y luego aparecen con este fundido (segundos)
RAIN_ANIM_RATE = 6.0             # la lluvia de orbes cae a la mitad de velocidad

# --- Modos de juego (de momento todos usan las mismas reglas) ---
GAME_MODES = ("classic", "fast", "surprise")

# --- Ayuda visual sobre los orbes: ninguna, formas geométricas o runas nórdicas ---
ASSIST_MODES = ("none", "geo", "runes")

# --- Modo sorpresa: un orbe sorpresa al llegar a SURPRISE_FIRST_LEVEL y cada
#     SURPRISE_EVERY niveles (4, 6, 8...). Al pulsarlo hace uno de 5 efectos al azar. ---
SURPRISE_FIRST_LEVEL = 4
SURPRISE_EVERY = 2
SURPRISE_MEGA_DEPTH = 3          # anillos de orbes que destruye la mega explosión

# --- Reglas ---
MIN_GROUP = 3                    # orbes conectados mínimos para poder reventar
POINTS_PER_PAIR = 10             # puntos = n * (n - 1) * POINTS_PER_PAIR
COLOR_CLEAR_BONUS = 5000         # eliminar todos los orbes de un color
BOARD_CLEAR_BONUS = 10000        # dejar el tablero sin ningún orbe
LEVEL_POINTS = 1000              # nivel n -> n+1 al llegar a LEVEL_POINTS * n*(n+1)/2 puntos

# --- Dificultad (ver game.level_params) ---
START_COLORS = 3                 # colores de los orbes nuevos en el nivel 1
# Modos Clásico y Sorpresa: nivel en que se añade cada color nuevo (amarillo, violeta, turquesa,
# rosa, negro, naranja, marrón, blanco, verde oscuro, gris); cada salto es uno más largo.
# Modo Rápido: no va por niveles, cada lluvia de orbes añade el siguiente color.
COLOR_UNLOCK_LEVELS = (5, 8, 12, 17, 23, 30, 38, 47, 57, 68)
MAX_COLORS = START_COLORS + len(COLOR_UNLOCK_LEVELS)     # 13
FAST_MIN_NEW_COLOR_ORBS = 3      # modo Rápido: orbes del color nuevo que trae, como mínimo, cada lluvia

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
SURPRISE_ORB = (236, 236, 242)   # orbe sorpresa: blanco con un "?" negro
SURPRISE_INK = (18, 18, 24)
GOLD = (255, 204, 51)            # amarillo dorado de la puntuación final (contraste ~12:1 sobre
GOLD_OUTLINE = (60, 36, 0)       # el panel oscuro); el contorno lo mantiene legible sobre cualquier fondo
OVER_PANEL = (10, 12, 28)        # panel de fin de partida

# Rojo, azul y verde son los colores iniciales. Los demás se eligieron, en este orden, como el
# tono de su familia más distinto (ΔE2000) de todos los anteriores: la pareja más parecida de
# los 13 (amarillo-naranja) está a ΔE 24,8, más que la peor de la paleta antigua de 6 (24,3).
PALETTE = [
    (232, 84, 84),     # 0 rojo
    (84, 144, 240),    # 1 azul
    (96, 204, 112),    # 2 verde
    (255, 204, 38),    # 3 amarillo   (nivel 5)
    (156, 46, 184),    # 4 violeta    (nivel 8)
    (46, 217, 230),    # 5 turquesa   (nivel 12)
    (255, 166, 240),   # 6 rosa       (nivel 17)
    (31, 24, 24),      # 7 negro      (nivel 23): lleva borde claro para verse sobre el fondo
    (245, 129, 12),    # 8 naranja    (nivel 30)
    (128, 83, 32),     # 9 marrón     (nivel 38)
    (255, 251, 247),   # 10 blanco    (nivel 47): el orbe sorpresa se distingue por su anillo dorado
    (19, 97, 81),      # 11 verde oscuro (nivel 57)
    (128, 128, 128),   # 12 gris      (nivel 68)
]
MENU_ORBS = 6                    # orbes decorativos del menú (los 6 primeros colores)
