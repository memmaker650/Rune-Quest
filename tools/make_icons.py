"""Genera los iconos de la app (iOS, macOS y Windows) a partir del propio código del juego.

El icono es el orbe naranja con su runa (Raidho), dibujado con la misma paleta, proporciones
y trazos que en el tablero, y detrás un vikingo que levanta un martillo para golpearla.

Uso (desde la raíz del proyecto):
    python tools/make_icons.py

Escribe en src/RuneQuest/resources/:
    icon-<tamaño>.png   iOS (20 ... 1024) y pantallas de arranque (640, 1280, 1920)
    icon.icns           macOS (con la forma de esquinas redondeadas y margen de macOS)
    icon.ico            Windows
    icon.png            512 px, vista previa e icono de ventana (Windows, Linux)
    icon-macos.png      512 px con la forma de macOS: icono del Dock al ejecutar sin empaquetar
"""

import io
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pygame  # noqa: E402

from RuneQuest import settings as S  # noqa: E402
from RuneQuest.runes import draw_rune, rune_for_color  # noqa: E402
from RuneQuest.sprites import _shade  # noqa: E402
from RuneQuest.ui import contrast  # noqa: E402

OUT = ROOT / "src" / "RuneQuest" / "resources"
ORANGE = S.PALETTE.index((245, 129, 12))
IOS_SIZES = (20, 29, 40, 58, 60, 76, 80, 87, 120, 152, 167, 180, 640, 1024, 1280, 1920)
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
CANVAS = 2048                     # se dibuja grande y se reduce con suavizado

# Colores del vikingo, sacados de la paleta del juego
GRAY = S.PALETTE[12]              # casco y cabeza del martillo
WHITE = S.PALETTE[10]             # cuernos y brillos
BROWN = S.PALETTE[9]              # barba y mango
RED = S.PALETTE[0]                # túnica
SKIN = (236, 178, 138)
OUTLINE = (14, 14, 26)


def P(x, y):
    """Coordenadas de diseño (lienzo de 1024) a píxeles del lienzo real."""
    k = CANVAS / 1024
    return (round(x * k), round(y * k))


def L(v):
    return round(v * CANVAS / 1024)


def poly(surf, color, points, outline=True):
    pts = [P(*p) for p in points]
    if outline:
        pygame.draw.polygon(surf, OUTLINE, pts, L(14))
    pygame.draw.polygon(surf, color, pts)


def circle(surf, color, center, r, outline=True):
    if outline:
        pygame.draw.circle(surf, OUTLINE, P(*center), L(r + 7))
    pygame.draw.circle(surf, color, P(*center), L(r))


def thick_line(surf, color, a, b, width, outline=True):
    """Segmento grueso con extremos redondeados (y contorno oscuro)."""
    for col, w in (((OUTLINE, width + 14) if outline else (None, 0)), (color, width)):
        if col is None:
            continue
        pygame.draw.line(surf, col, P(*a), P(*b), L(w))
        for p in (a, b):
            pygame.draw.circle(surf, col, P(*p), L(w) // 2)


def background(surf):
    """Degradado vertical con los azules del tablero."""
    top, bottom = (46, 52, 104), (14, 16, 34)
    h = surf.get_height()
    for y in range(h):
        t = y / (h - 1)
        color = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
        pygame.draw.line(surf, color, (0, y), (surf.get_width(), y))
    glow = pygame.Surface(surf.get_size(), pygame.SRCALPHA)   # halo cálido tras la runa
    for i in range(40, 0, -1):
        pygame.draw.circle(glow, (*S.PALETTE[ORANGE], 5), P(*ORB_CENTER), L(ORB_RADIUS + i * 9))
    surf.blit(glow, (0, 0))


def bez(*pts, steps=18):
    """Curva de Bézier cúbica encadenada: p0, c1, c2, p1, c3, c4, p2, ... -> lista de puntos."""
    out = [pts[0]]
    for i in range(0, len(pts) - 1, 3):
        p0, c1, c2, p1 = pts[i:i + 4]
        for k in range(1, steps + 1):
            t = k / steps
            a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
            out.append((a * p0[0] + b * c1[0] + c * c2[0] + d * p1[0],
                        a * p0[1] + b * c1[1] + c * c2[1] + d * p1[1]))
    return out


def volume(surf, color, pts, shade=0.68, depth=22, light=1.18, outline=True):
    """Forma con volumen: luz desde arriba a la izquierda (brillo) y sombra abajo a la derecha."""
    px = [P(*p) for p in pts]
    if outline:
        pygame.draw.polygon(surf, OUTLINE, px, L(12))
    layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    d = L(depth)
    pygame.draw.polygon(layer, _shade(color, shade), px)
    pygame.draw.polygon(layer, color, [(x - d, y - d) for x, y in px])
    pygame.draw.polygon(layer, _shade(color, light), [(x - 2 * d, y - 2 * d) for x, y in px])
    pygame.draw.polygon(layer, color, [(x - 2 * d + d // 2, y - 2 * d + d // 2) for x, y in px])
    mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), px)
    layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(layer, (0, 0))


def stroke(surf, color, pts, width):
    """Trazo curvo (pelo, correas, arrugas)."""
    pygame.draw.lines(surf, color, False, [P(*p) for p in pts], L(width))


def ellipse(surf, color, center, rx, ry, outline=True):
    rect = pygame.Rect(0, 0, L(rx * 2), L(ry * 2))
    rect.center = P(*center)
    if outline:
        pygame.draw.ellipse(surf, OUTLINE, rect.inflate(L(12), L(12)))
    pygame.draw.ellipse(surf, color, rect)


FUR = (92, 74, 58)                # capa de piel
BLOND = (226, 184, 92)            # barba, bigote y cejas rubias
LEATHER = _shade(BROWN, 0.85)
METAL = GRAY


def hammer(surf, grip, head_center):
    """Martillo vikingo (tipo Mjölnir): mango con correas de cuero y cabeza biselada."""
    dx, dy = head_center[0] - grip[0], head_center[1] - grip[1]
    n = math.hypot(dx, dy)
    ax, ay = dx / n, dy / n                                    # dirección del mango
    ux, uy = -ay, ax                                           # eje largo de la cabeza
    cx, cy = head_center

    def at(a, b):                                              # a: a lo largo de la cabeza
        return (cx + ux * a + ax * b, cy + uy * a + ay * b)

    pommel = (grip[0] - ax * POMMEL_PAST_HAND * K, grip[1] - ay * POMMEL_PAST_HAND * K)
    width = 42 * K
    thick_line(surf, BROWN, pommel, head_center, width)
    length = math.hypot(cx - pommel[0], cy - pommel[1])

    def wood(t, b):                                            # t: 0 pomo .. 1 cabeza; b: través
        return (pommel[0] + ax * length * t + ux * b, pommel[1] + ay * length * t + uy * b)

    stroke(surf, _shade(BROWN, 1.3), [wood(0.04, -width * 0.28), wood(0.96, -width * 0.28)], 4)
    for b0, phase in ((-0.1, 0.0), (0.12, 1.7), (0.3, 3.1)):  # vetas onduladas
        pts = [wood(t / 40, width * (b0 + 0.05 * math.sin(t * 0.55 + phase)))
               for t in range(2, 39)]
        stroke(surf, _shade(BROWN, 0.62), pts, 3)
    for t0 in (0.62, 0.8):                                     # nudos de la madera
        c = wood(t0, width * 0.05)
        rect = pygame.Rect(0, 0, L(18 * K), L(9 * K))
        rect.center = P(*c)
        pygame.draw.ellipse(surf, _shade(BROWN, 0.55), rect, L(3))
    for k in range(6):                                         # correas de cuero del mango
        t = 0.12 + k * 0.07
        p = (pommel[0] + (cx - pommel[0]) * t, pommel[1] + (cy - pommel[1]) * t)
        stroke(surf, _shade(BROWN, 0.5), [(p[0] + ux * width * 0.55, p[1] + uy * width * 0.55),
                                          (p[0] - ux * width * 0.55 + ax * 10,
                                           p[1] - uy * width * 0.55 + ay * 10)], 6)
    circle(surf, METAL, pommel, 16 * K)
    h, t, w = HEAD_HALF * K, 64 * K, 80 * K
    head = [at(-h, -t), at(-h + 26 * K, -w), at(h - 26 * K, -w), at(h, -t),
            at(h, t), at(h - 26 * K, w), at(-h + 26 * K, w), at(-h, t)]
    volume(surf, METAL, head, depth=14)
    stroke(surf, _shade(METAL, 1.45), [at(-h + 30 * K, -t + 2), at(h - 30 * K, -t + 2)], 5)
    for side in (-1, 1):                                       # nudos grabados
        c = at(side * h * 0.5, 0)
        pygame.draw.circle(surf, _shade(METAL, 0.62), P(*c), L(32), L(7))
        pygame.draw.circle(surf, _shade(METAL, 0.62), P(*c), L(11))


def viking_head(surf):
    """Cabeza del vikingo (cuello, cara, barba trenzada, cuernos y casco con remaches),
    dibujada en vertical con la cara en (270, 480). Luz desde arriba a la izquierda."""
    # --- Cuello y orejas
    volume(surf, SKIN, [(215, 560), (325, 560), (330, 650), (210, 650)], depth=10)
    ellipse(surf, _shade(SKIN, 0.92), (172, 480), 20, 32)
    ellipse(surf, _shade(SKIN, 0.85), (368, 480), 20, 32)
    # --- Cara ovalada
    volume(surf, SKIN, bez((270, 360), (330, 360), (365, 410), (362, 480)) +
           bez((362, 480), (360, 560), (320, 600), (270, 605)) +
           bez((270, 605), (220, 600), (180, 560), (178, 480)) +
           bez((178, 480), (175, 410), (210, 360), (270, 360)), depth=14)
    # Ojos (miran hacia la runa), cejas fruncidas, nariz
    for x in (228, 312):
        ellipse(surf, WHITE, (x, 478), 21, 12, outline=False)
        pygame.draw.circle(surf, (60, 90, 140), P(x + 7, 479), L(10))
        pygame.draw.circle(surf, OUTLINE, P(x + 8, 479), L(5))
        pygame.draw.circle(surf, WHITE, P(x + 5, 475), L(3))
    volume(surf, _shade(BLOND, 0.78), [(194, 452), (213, 434), (264, 456), (260, 472)], depth=4)
    volume(surf, _shade(BLOND, 0.78), [(346, 452), (327, 434), (276, 456), (280, 472)], depth=4)
    volume(surf, SKIN, [(270, 470), (292, 535), (278, 548), (252, 544), (258, 500)], depth=8,
           shade=0.75)
    # --- Barba larga con trenzas y bigote
    beard = (bez((182, 505), (190, 560), (215, 575), (270, 572)) +
             bez((270, 572), (325, 575), (350, 560), (358, 505)) +
             bez((358, 505), (385, 600), (360, 690), (300, 730)) +
             bez((300, 730), (285, 745), (255, 745), (240, 730)) +
             bez((240, 730), (180, 690), (155, 600), (182, 505)))
    volume(surf, BLOND, beard, depth=16)
    for i in range(9):                                         # mechones
        x = 205 + i * 17
        stroke(surf, _shade(BLOND, 0.7), bez((x, 590), (x - 6, 630), (x + 6, 670), (x + 2, 705)), 5)
    for bx in (248, 292):                                      # trenzas con anillas de metal
        for k in range(4):
            ellipse(surf, BLOND, (bx, 750 + k * 26), 15, 16)
        ellipse(surf, METAL, (bx, 765), 17, 8)
        ellipse(surf, METAL, (bx, 818), 17, 8)
    mouth = (bez((220, 566), (244, 558), (296, 558), (320, 566)) +         # boca abierta: grito
             bez((320, 566), (318, 612), (296, 640), (270, 642)) +
             bez((270, 642), (244, 640), (222, 612), (220, 566)))
    volume(surf, (78, 22, 28), mouth, depth=4, shade=0.6)
    ellipse(surf, (168, 62, 72), (270, 624), 26, 10, outline=False)       # lengua
    pygame.draw.rect(surf, (246, 240, 226), (*P(228, 564), L(84), L(20)))  # dientes de arriba
    for x in (249, 270, 291):
        pygame.draw.line(surf, (190, 180, 168), P(x, 565), P(x, 583), L(2))
    pygame.draw.rect(surf, (246, 240, 226), (*P(244, 628), L(52), L(10)))  # dientes de abajo
    for x in (261, 279):
        pygame.draw.line(surf, (190, 180, 168), P(x, 628), P(x, 637), L(2))
    volume(surf, BLOND, bez((270, 548), (240, 540), (200, 560), (182, 595)) +
           bez((182, 595), (215, 585), (245, 575), (270, 572)), depth=6)        # bigote izq.
    volume(surf, BLOND, bez((270, 548), (300, 540), (340, 560), (358, 595)) +
           bez((358, 595), (325, 585), (295, 575), (270, 572)), depth=6)        # bigote dcho.
    # --- Cuernos curvos con anilla
    horn_l = (bez((200, 400), (150, 380), (95, 330), (80, 230)) +
              bez((80, 230), (115, 280), (165, 330), (215, 352)))
    horn_r = [(540 - x, y) for x, y in horn_l]
    for horn in (horn_l, horn_r):
        volume(surf, WHITE, horn, depth=10, shade=0.78)
    for x0 in (170, 370):
        stroke(surf, _shade(METAL, 0.8), [(x0 - 12, 392), (x0 + 12, 358)], 10)
    # --- Casco (spangenhelm): cúpula con bandas y remaches, borde y protector nasal
    dome = bez((150, 425), (150, 330), (205, 290), (270, 288)) + \
        bez((270, 288), (335, 290), (390, 330), (390, 425))
    volume(surf, METAL, dome, depth=20)
    for x0, x1 in ((270, 270), (205, 175), (335, 365)):        # bandas verticales
        stroke(surf, _shade(METAL, 0.62), bez((x0, 292), (x0 + (x1 - x0) * 0.3, 330),
                                              (x1, 380), (x1 + (x1 - 270) * 0.05, 420)), 9)
    volume(surf, _shade(METAL, 0.85), [(142, 412), (398, 412), (398, 450), (142, 450)], depth=6)
    for k in range(8):                                         # remaches
        pygame.draw.circle(surf, _shade(METAL, 1.5), P(158 + k * 32, 431), L(6))
    volume(surf, _shade(METAL, 0.85), [(258, 448), (282, 448), (285, 520), (270, 532),
                                       (255, 520)], depth=4)


# --- Escena del golpe -------------------------------------------------------------------
ORB_CENTER, ORB_RADIUS = (738, 790), 245
HIT_ANGLE = 255                   # punto del orbe donde golpea el martillo (grados)
HANDLE_TO_HEAD = 380              # de la mano de atrás al centro de la cabeza del martillo
HEAD_HALF = 165                   # media longitud de la cabeza del martillo
HAND_GAP = 92 
POMMEL_PAST_HAND = 118            # mango que sobresale por detrás de la mano derecha                    # separación entre las dos manos en el mango
LEAN = -13                        # inclinación de la cabeza (negativo: hacia la runa)
HEAD_SCALE = 0.5                  # la cabeza detallada, reducida a la escala del cuerpo
FIST = 0.69                       # tamaño de los puños (respecto al dibujo base)

# Esqueleto (unidades de diseño de 1024): cuerpo inclinado hacia la runa, en postura de golpe
NECK_LOCAL = (272, 640)           # base del cuello en el dibujo de la cabeza
J = {
    "shoulder_back": (218, 346), "shoulder_front": (434, 380),
    "waist_back": (188, 552), "waist_front": (372, 572),
    "hip_back": (216, 600), "hip_front": (348, 610),
    "knee_back": (192, 752), "ankle_back": (136, 892),
    "knee_front": (412, 736), "ankle_front": (418, 892),
}
UPPER_ARM, FOREARM = 122, 112     # longitudes máximas del brazo
RIGHT_ELBOW_DROP = (-40, 182)      # codo derecho respecto al hombro: casi en vertical, junto al costado
K = 1.14                          # tamaño del vikingo (y su martillo) respecto al esqueleto J
PIVOT = (280, 905)                # se escala desde los pies: sigue pisando la nieve
VIKING_DX = -50                   # desplazamiento horizontal del vikingo (deja sitio a la maza)


def V(p):
    """Punto del esqueleto J -> posición con el vikingo a escala K."""
    return (PIVOT[0] + VIKING_DX + (p[0] - PIVOT[0]) * K, PIVOT[1] + (p[1] - PIVOT[1]) * K)
TROUSERS = (84, 80, 108)
BOOT = _shade(BROWN, 0.8)


def strike_geometry():
    """Contacto, cabeza del martillo y manos. La cabeza va perpendicular al mango y su cara
    de golpeo toca el orbe en HIT_ANGLE apuntando a su centro."""
    ox, oy = ORB_CENTER
    c = (math.cos(math.radians(HIT_ANGLE)), math.sin(math.radians(HIT_ANGLE)))
    contact = (ox + ORB_RADIUS * c[0], oy + ORB_RADIUS * c[1])
    into = (-c[0], -c[1])                                      # dirección del golpe
    up = (into[1], -into[0])                                   # del mango hacia la cabeza
    head = (contact[0] - into[0] * HEAD_HALF * K, contact[1] - into[1] * HEAD_HALF * K)

    def along(d):
        return (head[0] - up[0] * d, head[1] - up[1] * d)

    return {"contact": contact, "into": into, "up": up, "head": head,
            "back_hand": along(HANDLE_TO_HEAD * K),
            "front_hand": along((HANDLE_TO_HEAD - HAND_GAP) * K),
            "pommel": along((HANDLE_TO_HEAD + POMMEL_PAST_HAND) * K)}


def place_layer(surf, draw, anchor_local, anchor_at, angle, scale):
    """Dibuja ``draw`` en una capa, la gira y escala, y la coloca con ``anchor_local`` en
    ``anchor_at``."""
    layer = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)
    draw(layer)
    a = math.radians(angle)
    x, y = (anchor_local[0] - 512) * scale, (anchor_local[1] - 512) * scale
    rx, ry = math.cos(a) * x + math.sin(a) * y, -math.sin(a) * x + math.cos(a) * y
    rotated = pygame.transform.rotozoom(layer, angle, scale)
    surf.blit(rotated, rotated.get_rect(center=P(anchor_at[0] - rx, anchor_at[1] - ry)))


def tapered(surf, a, b, wa, wb, color, depth=8):
    """Segmento que se estrecha (de ancho ``wa`` en ``a`` a ``wb`` en ``b``) con extremos
    redondeados y volumen: así son brazos y piernas."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1
    ux, uy = dx / n, dy / n
    nx, ny = -uy, ux
    start = math.atan2(ny, nx)
    pts = []
    for k in range(13):                                        # media vuelta en ``b``
        t = start - math.pi * k / 12
        pts.append((b[0] + math.cos(t) * wb / 2, b[1] + math.sin(t) * wb / 2))
    for k in range(13):                                        # media vuelta en ``a``
        t = start + math.pi - math.pi * k / 12
        pts.append((a[0] + math.cos(t) * wa / 2, a[1] + math.sin(t) * wa / 2))
    volume(surf, color, pts, depth=depth)


def bend_joint(start, end, len_a, len_b, side):
    """Codo o rodilla: el punto a ``len_a`` de ``start`` y ``len_b`` de ``end`` (``side``
    elige hacia qué lado se dobla)."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    d = min(math.hypot(dx, dy), len_a + len_b - 1)
    a = (len_a ** 2 - len_b ** 2 + d ** 2) / (2 * d)
    h = math.sqrt(max(0.0, len_a ** 2 - a ** 2))
    ux, uy = dx / (math.hypot(dx, dy) or 1), dy / (math.hypot(dx, dy) or 1)
    mx, my = start[0] + ux * a, start[1] + uy * a
    return (mx - uy * h * side, my + ux * h * side)


def _side_curve(a, b, wa, wb, bulge, sign, bulge_at=0.45, steps=10):
    """Borde de una extremidad entre ``a`` y ``b``: ancho de ``wa`` a ``wb`` con un abultamiento
    (músculo) de ``bulge`` en ``bulge_at``. ``sign`` elige el lado (+1 / -1)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1
    nx, ny = -dy / n * sign, dx / n * sign
    pts = []
    for k in range(steps + 1):
        t = k / steps
        half = (wa + (wb - wa) * t) / 2 + bulge * math.sin(math.pi * min(1, t / (2 * bulge_at)))
        pts.append((a[0] + dx * t + nx * half, a[1] + dy * t + ny * half))
    return pts


def catmull_rom(points, closed=True, steps=8):
    """Curva suave que pasa por ``points`` (spline de Catmull-Rom)."""
    pts = list(points)
    n = len(pts)
    out = []
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0, p1 = pts[(i - 1) % n], pts[i]
        p2, p3 = pts[(i + 1) % n], pts[(i + 2) % n]
        for k in range(steps):
            t = k / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 +
                                    (-a + 3 * b - 3 * c + d) * t3)
                             for a, b, c, d in zip(p0, p1, p2, p3)))
    return out


def _unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1
    return dx / n, dy / n, n


def arm(surf, shoulder, wrist, side, bend=1.15, elbow=None):
    """Brazo musculoso como una sola silueta continua, de hombro a muñeca: deltoides, bíceps
    por dentro, codo en punta por fuera con su pliegue por dentro y antebrazo ancho junto al
    codo que se afina hacia la muñeca. Encima: manga corta, brazal de cuero y relieve."""
    if elbow is None:
        reach = math.hypot(wrist[0] - shoulder[0], wrist[1] - shoulder[1])
        total = min((UPPER_ARM + FOREARM) * K, reach * bend)
        elbow = bend_joint(shoulder, wrist, total * 0.52, total * 0.48, side)
    ax1, ay1, len1 = _unit(shoulder, elbow)
    ax2, ay2, len2 = _unit(elbow, wrist)
    turn = ax1 * ay2 - ay1 * ax2                               # hacia qué lado se dobla
    o = -1 if turn > 0 else 1                                  # lado de fuera (el del codo)
    n1 = (-ay1 * o, ax1 * o)
    n2 = (-ay2 * o, ax2 * o)
    nb = (n1[0] + n2[0], n1[1] + n2[1])
    nbl = math.hypot(*nb) or 1
    nb = (nb[0] / nbl, nb[1] / nbl)

    def on1(t, w):                                             # punto del brazo
        return (shoulder[0] + ax1 * len1 * t + n1[0] * w, shoulder[1] + ay1 * len1 * t + n1[1] * w)

    def on2(t, w):                                             # punto del antebrazo
        return (elbow[0] + ax2 * len2 * t + n2[0] * w, elbow[1] + ay2 * len2 * t + n2[1] * w)

    k = K
    outline = [
        on1(-0.05, 38 * k),                                    # hombro (fuera)
        on1(0.22, 42 * k),                                     # deltoides
        on1(0.62, 33 * k),
        (elbow[0] + nb[0] * 30 * k, elbow[1] + nb[1] * 30 * k),   # codo en punta
        on2(0.22, 33 * k),                                     # músculo del antebrazo
        on2(0.62, 25 * k),
        on2(1.0, 20 * k),                                      # muñeca (fuera)
        on2(1.0, -19 * k),                                     # muñeca (dentro)
        on2(0.55, -24 * k),
        on2(0.18, -25 * k),
        (elbow[0] - nb[0] * 17 * k, elbow[1] - nb[1] * 17 * k),   # pliegue del codo
        on1(0.78, -32 * k),
        on1(0.5, -52 * k),                                     # bíceps grande
        on1(0.25, -46 * k),
        on1(0.08, -36 * k),                                    # axila
    ]
    volume(surf, SKIN, catmull_rom(outline), depth=8)
    # relieve: borde del bíceps, pliegue del codo y luz sobre el deltoides
    biceps_shadow = catmull_rom([on1(0.22, -30 * k), on1(0.5, -48 * k), on1(0.78, -28 * k),
                                 on1(0.5, -34 * k)])
    pygame.draw.polygon(surf, _shade(SKIN, 0.82), [P(*q) for q in biceps_shadow])   # volumen
    stroke(surf, _shade(SKIN, 0.68), catmull_rom([on1(0.2, -24 * k), on1(0.5, -34 * k),
                                                 on1(0.8, -22 * k)], closed=False), 3)
    pygame.draw.circle(surf, _shade(SKIN, 1.18), P(*on1(0.45, -40 * k)), L(7 * k))   # brillo
    stroke(surf, _shade(SKIN, 0.6), catmull_rom([(elbow[0] - nb[0] * 10 * k, elbow[1] - nb[1] * 10 * k),
                                                on2(0.12, -14 * k), on2(0.2, -18 * k)],
                                               closed=False), 3)
    stroke(surf, _shade(SKIN, 1.15), catmull_rom([on1(0.25, 30 * k), on1(0.45, 30 * k),
                                                 on1(0.6, 25 * k)], closed=False), 4)
    # brazal de cuero sobre el antebrazo, con correas
    bracer = catmull_rom([on2(0.48, 28 * k), on2(0.94, 23 * k), on2(0.94, -22 * k),
                          on2(0.48, -27 * k)])
    volume(surf, LEATHER, bracer, depth=5)
    for t in (0.6, 0.78):
        stroke(surf, _shade(LEATHER, 0.5), [on2(t, 26 * k), on2(t + 0.03, -25 * k)], 3)
    # manga corta sobre el hombro
    sleeve = catmull_rom([on1(-0.18, 0), on1(-0.05, 44 * k), on1(0.36, 40 * k),
                          on1(0.4, -36 * k), on1(-0.02, -38 * k)])
    volume(surf, RED, sleeve, depth=8)
    stroke(surf, _shade(RED, 0.6), [on1(0.34, 38 * k), on1(0.38, -34 * k)], 4)   # dobladillo


def leg(surf, hip, knee, ankle):
    """Pierna: el pantalón es una sola silueta continua de cadera a tobillo (muslo, rodilla,
    gemelo), con vendas, y una bota con piel cuya caña sigue la dirección de la espinilla."""
    dx, dy = ankle[0] - knee[0], ankle[1] - knee[1]
    n = math.hypot(dx, dy) or 1
    ux, uy = dx / n, dy / n                                    # dirección de la espinilla
    px, py = -uy, ux                                           # perpendicular
    tx, ty, tl = _unit(hip, knee)
    qx, qy = -ty, tx                                           # perpendicular al muslo
    kb = (qx + px, qy + py)
    kbl = math.hypot(*kb) or 1
    kb = (kb[0] / kbl, kb[1] / kbl)

    def th(t, w):                                              # punto del muslo
        return (hip[0] + tx * tl * t + qx * w, hip[1] + ty * tl * t + qy * w)

    def sh(t, w):                                              # punto de la espinilla
        return (knee[0] + dx * t + px * w, knee[1] + dy * t + py * w)

    trousers = catmull_rom([
        th(-0.08, 50), th(0.35, 50), th(0.75, 41),
        (knee[0] + kb[0] * 37, knee[1] + kb[1] * 37),          # rodilla
        sh(0.3, 38), sh(0.7, 30), sh(1.0, 28),
        sh(1.0, -28), sh(0.6, -32), sh(0.25, -38),             # gemelo
        (knee[0] - kb[0] * 33, knee[1] - kb[1] * 33),
        th(0.6, -44), th(0.2, -50), th(-0.08, -48)])
    volume(surf, TROUSERS, trousers, depth=10)
    stroke(surf, _shade(TROUSERS, 0.65), catmull_rom([th(0.7, -18), (knee[0] - kb[0] * 6,
                                                      knee[1] - kb[1] * 6), sh(0.2, -12)],
                                                     closed=False), 3)   # pliegue de la rodilla
    for t in (0.3, 0.5, 0.7):                                  # vendas cruzadas
        c = (knee[0] + dx * t, knee[1] + dy * t)
        stroke(surf, LEATHER, [(c[0] + px * 24 - ux * 8, c[1] + py * 24 - uy * 8),
                               (c[0] - px * 24 + ux * 8, c[1] - py * 24 + uy * 8)], 5)
    sole = ankle[1] + 30
    top_a = (ankle[0] + px * 31 - ux * 30, ankle[1] + py * 31 - uy * 30)   # boca de la caña,
    top_b = (ankle[0] - px * 31 - ux * 30, ankle[1] - py * 31 - uy * 30)   # perpendicular a la pierna
    back, front = sorted((top_a, top_b))
    boot = [back, front,
            (front[0] + 8, ankle[1] + 4),                      # empeine
            (ankle[0] + 64, sole - 18), (ankle[0] + 72, sole - 4),   # puntera
            (ankle[0] + 66, sole), (ankle[0] - 30, sole),      # suela
            (ankle[0] - 34, sole - 14), (back[0] - 4, ankle[1] - 6)]  # talón
    volume(surf, BOOT, boot, depth=5)
    stroke(surf, _shade(BOOT, 0.55), [(ankle[0] - 30, sole - 6), (ankle[0] + 66, sole - 6)], 5)
    def at(a, b):                                              # a: a lo largo, b: a través
        return (ankle[0] + ux * a + px * b, ankle[1] + uy * a + py * b)

    cuff = [at(-52, -36), at(-52, 36)]                         # remate de piel en la boca
    for k in range(7):                                         # borde inferior con mechones
        b = 36 - k * (72 / 6)
        cuff.append(at(-24 + (6 if k % 2 else 0), b))
    volume(surf, FUR, cuff, depth=4)
    for b in (-16, 0, 16):
        stroke(surf, _shade(FUR, 0.65), [at(-48, b), at(-30, b + 3)], 3)


def torso(surf):
    """Túnica con cinturón y hebilla, falda hasta medio muslo y capa de piel en los hombros."""
    sb, sf = J["shoulder_back"], J["shoulder_front"]
    wb, wf = J["waist_back"], J["waist_front"]
    chest = (bez((sb[0] - 30, sb[1] - 8), (sb[0] + 30, sb[1] - 30), (sf[0] - 30, sf[1] - 26),
                 (sf[0] + 26, sf[1] + 4)) +
             bez((sf[0] + 26, sf[1] + 4), (sf[0] + 40, sf[1] + 80), (wf[0] + 22, wf[1] - 70),
                 (wf[0] + 8, wf[1])) +
             [(wb[0] - 6, wb[1])] +
             bez((wb[0] - 6, wb[1]), (wb[0] - 20, wb[1] - 80), (sb[0] - 44, sb[1] + 90),
                 (sb[0] - 30, sb[1] - 8)))
    volume(surf, RED, chest, depth=16)
    stroke(surf, _shade(RED, 0.62), bez(((sb[0] + sf[0]) / 2 + 6, sb[1] + 10),
                                        (wb[0] + 50, wb[1] - 120), (wb[0] + 44, wb[1] - 60),
                                        ((wb[0] + wf[0]) / 2, wb[1] + 4)), 5)
    skirt = [(wb[0] - 8, wb[1] - 4), (wf[0] + 10, wf[1] - 4), (wf[0] + 44, wf[1] + 108),
             (wb[0] - 46, wb[1] + 104)]
    volume(surf, RED, skirt, depth=10)
    for t in (0.3, 0.55, 0.8):                                 # pliegues
        x0 = wb[0] + (wf[0] - wb[0]) * t
        stroke(surf, _shade(RED, 0.65), [(x0, wb[1] + 14), (x0 + (t - 0.5) * 50, wb[1] + 100)], 4)
    volume(surf, LEATHER, [(wb[0] - 10, wb[1] - 16), (wf[0] + 12, wf[1] - 12),
                           (wf[0] + 12, wf[1] + 14), (wb[0] - 10, wb[1] + 10)], depth=4)   # cinto
    buckle = ((wb[0] + wf[0]) / 2 + 12, (wb[1] + wf[1]) / 2)
    volume(surf, METAL, [(buckle[0] - 16, buckle[1] - 16), (buckle[0] + 16, buckle[1] - 14),
                         (buckle[0] + 16, buckle[1] + 16), (buckle[0] - 16, buckle[1] + 14)],
           depth=3)
    mantle = bez((sb[0] - 44, sb[1] + 30), (sb[0] - 20, sb[1] - 40), (sf[0] - 20, sf[1] - 40),
                 (sf[0] + 40, sf[1] + 20))
    for i in range(9):                                         # borde de mechones
        x = sf[0] + 40 - i * ((sf[0] - sb[0] + 84) / 8)
        y = sf[1] + 20 + (sb[1] - sf[1]) * i / 8
        mantle += [(x, y + 14 + 6 * math.sin(i * 1.9)), (x - 6, y + 34)]
    volume(surf, FUR, mantle, depth=8)


def fist(surf, center, up, into, show_thumb=True, k=1.0, under=False):
    """Puño cerrado sobre el mango, visto de lado: una mano compacta con los cuatro dedos
    juntos rodeando el mango (pliegues entre ellos), nudillos marcados y el pulgar por encima.
    ``k`` escala la mano."""
    cx, cy = center
    ux, uy = up                                                # a lo largo del mango
    ix, iy = into                                              # perpendicular al mango

    if under:                                                  # agarre por debajo: nudillos abajo
        ix, iy = -ix, -iy

    def at(a, b):                                              # a: a lo largo, b: a través
        return (cx + (ux * a + ix * b) * k, cy + (uy * a + iy * b) * k)

    outline_pts = (bez(at(-44, -34), at(-20, -46), at(20, -46), at(44, -34)) +
                   bez(at(44, -34), at(54, -10), at(54, 18), at(42, 34)) +
                   bez(at(42, 34), at(20, 44), at(-20, 44), at(-42, 34)) +
                   bez(at(-42, 34), at(-54, 18), at(-54, -10), at(-44, -34)))
    volume(surf, SKIN, outline_pts, depth=7 * k)
    for a in (-22, 0, 22):                                     # separación entre dedos
        stroke(surf, _shade(SKIN, 0.6), bez(at(a, -36), at(a + 2, -14), at(a - 1, 10),
                                            at(a, 30)), max(2, 4 * k))
    for a in (-33, -11, 11, 33):                               # nudillos (con luz)
        pygame.draw.circle(surf, _shade(SKIN, 1.16), P(*at(a, -30)), L(7 * k))
    if show_thumb:                                             # pulgar sobre los dedos
        thumb = (bez(at(-46, 22), at(-30, 40), at(0, 44), at(26, 36)) +
                 bez(at(26, 36), at(34, 30), at(30, 20), at(18, 20)) +
                 bez(at(18, 20), at(-6, 24), at(-30, 18), at(-46, 8)))
        volume(surf, _shade(SKIN, 0.97), thumb, depth=4 * k)
        pygame.draw.ellipse(surf, _shade(SKIN, 1.22), (*P(*at(14, 26)), L(14 * k), L(9 * k)))


def wrist_of(g, hand, under=False):
    """La muñeca: un poco por detrás del puño (por encima del mango, o por debajo si la mano
    agarra desde abajo)."""
    x, y = g[hand]
    k = 40 * FIST * K * (-1 if under else 1)
    return (x - g["into"][0] * k - g["up"][0] * 4, y - g["into"][1] * k - g["up"][1] * 4)


def rounded_rect(half_a, half_b, radius, steps=6):
    """Contorno de un rectángulo de esquinas redondeadas, centrado en el origen (a, b)."""
    pts = []
    for (ca, cb), start in (((half_a - radius, half_b - radius), 0),
                            ((-half_a + radius, half_b - radius), 90),
                            ((-half_a + radius, -half_b + radius), 180),
                            ((half_a - radius, -half_b + radius), 270)):
        for k in range(steps + 1):
            t = math.radians(start + 90 * k / steps)
            pts.append((ca + math.cos(t) * radius, cb + math.sin(t) * radius))
    return pts


def hammer_at(surf, g):
    """Martillo en el momento del impacto, con una estela de su recorrido."""
    bx, by = g["back_hand"]
    for k, ang in enumerate((-30, -20, -11)):                  # posiciones anteriores del golpe
        r = math.radians(ang)

        def rot(p):
            x, y = p[0] - bx, p[1] - by
            return (bx + x * math.cos(r) - y * math.sin(r), by + x * math.sin(r) + y * math.cos(r))

        ghost = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)
        ux, uy = g["into"]
        hx, hy = rot(g["head"])
        ax, ay = (math.cos(r) * ux - math.sin(r) * uy, math.sin(r) * ux + math.cos(r) * uy)
        nx, ny = -ay, ax
        corners = rounded_rect(HEAD_HALF * K, 82 * K, 30 * K)
        pts = [(hx + ax * a + nx * b, hy + ay * a + ny * b) for a, b in corners]
        pygame.draw.polygon(ghost, (*WHITE, 22 + k * 16), [P(*c) for c in pts])
        surf.blit(ghost, (0, 0))
    hammer(surf, g["back_hand"], g["head"])


def impact_on_orb(surf, g):
    """Lo que le pasa al orbe: grietas desde el punto de contacto y un destello."""
    cx, cy = g["contact"]
    ix, iy = g["into"]
    rng = __import__("random").Random(7)
    cracks = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)
    for base in (-38, -12, 10, 34, 58):                        # grietas que se adentran
        ang = math.atan2(iy, ix) + math.radians(base)
        x, y, pts = cx, cy, [(cx, cy)]
        for _ in range(5):
            step = rng.uniform(26, 44)
            ang += math.radians(rng.uniform(-22, 22))
            x, y = x + math.cos(ang) * step, y + math.sin(ang) * step
            pts.append((x, y))
        pygame.draw.lines(cracks, (*_shade(S.PALETTE[ORANGE], 1.6), 255), False,
                          [P(px + 2, py + 2) for px, py in pts], L(6))
        pygame.draw.lines(cracks, (*_shade(S.PALETTE[ORANGE], 0.35), 255), False,
                          [P(*q) for q in pts], L(5))
    mask = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)  # solo dentro del orbe
    pygame.draw.circle(mask, (255, 255, 255, 255), P(*ORB_CENTER), L(ORB_RADIUS - 4))
    cracks.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(cracks, (0, 0))


def impact_effects(surf, g):
    """Destello, ondas de choque, chispas y esquirlas que salen despedidas del golpe."""
    cx, cy = g["contact"]
    ix, iy = g["into"]
    out = math.atan2(-iy, -ix)                                 # hacia fuera del orbe
    rng = __import__("random").Random(3)
    fx = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)
    for r, alpha in ((120, 30), (90, 50), (62, 80), (40, 140), (22, 230)):   # destello
        color = WHITE if r < 50 else S.PALETTE[3]
        pygame.draw.circle(fx, (*color, alpha), P(cx, cy), L(r))
    for k, r in enumerate((95, 140, 185)):                     # ondas de choque
        rect = pygame.Rect(0, 0, L(r * 2), L(r * 2))
        rect.center = P(cx, cy)
        pygame.draw.arc(fx, (*WHITE, 170 - k * 50), rect, -out - math.radians(70),
                        -out + math.radians(70), L(7 - k * 2))
    for _ in range(20):                                        # chispas
        ang = out + math.radians(rng.uniform(-80, 80))
        r0, length = rng.uniform(25, 60), rng.uniform(40, 150)
        a = (cx + math.cos(ang) * r0, cy + math.sin(ang) * r0)
        b = (cx + math.cos(ang) * (r0 + length), cy + math.sin(ang) * (r0 + length))
        color = rng.choice((WHITE, S.PALETTE[3], S.PALETTE[3], S.PALETTE[ORANGE]))
        pygame.draw.line(fx, (*color, 235), P(*a), P(*b), L(rng.uniform(3, 7)))
        pygame.draw.circle(fx, (*WHITE, 255), P(*b), L(3))
    for _ in range(6):                                         # esquirlas del orbe
        ang = out + math.radians(rng.uniform(-70, 70))
        d = rng.uniform(70, 190)
        px, py = cx + math.cos(ang) * d, cy + math.sin(ang) * d
        size = rng.uniform(10, 20)
        rot = rng.uniform(0, math.tau)
        tri = [(px + math.cos(rot + k * 2.1) * size, py + math.sin(rot + k * 2.1) * size)
               for k in range(3)]
        pygame.draw.polygon(fx, (*S.PALETTE[ORANGE], 255), [P(*q) for q in tri])
        pygame.draw.polygon(fx, (*OUTLINE, 255), [P(*q) for q in tri], L(3))
    surf.blit(fx, (0, 0))


def orb(surf, center, radius, color_idx):
    """Orbe con su runa, con las mismas proporciones que ``sprites.orb_sprite``."""
    base = S.PALETTE[color_idx]
    cx, cy = P(*center)
    r = L(radius)
    rim = max(2, round(r * 0.1))
    pygame.draw.circle(surf, OUTLINE, (cx, cy), r + rim)
    pygame.draw.circle(surf, _shade(base, 0.55), (cx, cy), r)
    pygame.draw.circle(surf, base, (cx, cy), r - rim)
    pygame.draw.circle(surf, _shade(base, 1.45), (cx - r // 3, cy - r // 3), max(2, r // 4))
    ink = max(((215, 215, 225), _shade(base, 0.3)), key=lambda c: contrast(c, base))
    draw_rune(surf, rune_for_color(color_idx), (cx, cy), r * 0.52, ink, max(2, round(r * 0.14)))


def neck_point():
    """Base del cuello: entre los dos hombros, un poco por encima."""
    sb, sf = J["shoulder_back"], J["shoulder_front"]
    return ((sb[0] + sf[0]) / 2 - 6, (sb[1] + sf[1]) / 2 - 14)


SNOW = (236, 242, 250)
SNOW_SHADE = (178, 196, 226)
ICE = (150, 202, 232)
GROUND_Y = 884                    # altura del suelo nevado (detrás de los pies)


def snow_ground(surf):
    """Suelo de nieve con montículos suaves y placas de hielo brillantes."""
    top = bez((0, GROUND_Y - 6), (180, GROUND_Y - 34), (360, GROUND_Y + 10), (560, GROUND_Y - 8)) + \
        bez((560, GROUND_Y - 8), (740, GROUND_Y - 26), (900, GROUND_Y + 6), (1024, GROUND_Y - 14))
    pts = top + [(1024, 1024), (0, 1024)]
    pygame.draw.polygon(surf, SNOW, [P(*q) for q in pts])
    shade = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)        # sombra azulada abajo
    for i in range(20):
        y = GROUND_Y + 30 + i * 6
        pygame.draw.rect(shade, (*SNOW_SHADE, 6 + i * 3), (0, L(y), CANVAS, L(6)))
    surf.blit(shade, (0, 0))
    for cx, cy, rx, ry in ((520, 965, 120, 18), (150, 990, 90, 13), (880, 1000, 110, 14)):
        rect = pygame.Rect(0, 0, L(rx * 2), L(ry * 2))
        rect.center = P(cx, cy)
        pygame.draw.ellipse(surf, ICE, rect)                    # placa de hielo
        pygame.draw.ellipse(surf, _shade(ICE, 0.8), rect, L(3))
        pygame.draw.line(surf, (255, 255, 255), P(cx - rx * 0.6, cy - ry * 0.2),
                         P(cx - rx * 0.1, cy - ry * 0.5), L(4))   # brillo
        pygame.draw.line(surf, (255, 255, 255), P(cx + rx * 0.05, cy + ry * 0.1),
                         P(cx + rx * 0.35, cy - ry * 0.1), L(3))
    stroke(surf, (255, 255, 255), top[4:30], 4)                 # luz en la cresta de la nieve


def ground_shadow(surf):
    shadow = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (*_shade(SNOW_SHADE, 0.7), 150), (*P(80, 892), L(420), L(40)))
    surf.blit(shadow, (0, 0))


def snow_on_boots(surf):
    """Nieve que tapa la planta de las botas: el vikingo está pisando la nieve."""
    for ax, ay in (J["ankle_back"], J["ankle_front"]):
        mound = bez((ax - 46, ay + 30), (ax - 20, ay + 8), (ax + 30, ay + 8),
                    (ax + 74, ay + 30)) + [(ax + 74, ay + 40), (ax - 46, ay + 40)]
        pygame.draw.polygon(surf, SNOW, [P(*q) for q in mound])
        stroke(surf, (255, 255, 255), mound[3:15], 3)


def snow_drift(surf):
    """Montón de nieve delante de la base del orbe, para que se asiente en el suelo."""
    cx, cy = ORB_CENTER[0], min(ORB_CENTER[1] + ORB_RADIUS, 975)   # siempre visible
    drift = bez((cx - 260, cy + 40), (cx - 160, cy - 46), (cx + 150, cy - 50),
                (cx + 270, cy + 30)) + [(cx + 270, 1024), (cx - 260, 1024)]
    pygame.draw.polygon(surf, SNOW, [P(*q) for q in drift])
    stroke(surf, (255, 255, 255), bez((cx - 180, cy - 2), (cx - 100, cy - 36), (cx + 60, cy - 40),
                                      (cx + 160, cy - 16)), 4)


def snowflakes(surf):
    """Copos de nieve cayendo."""
    rng = __import__("random").Random(11)
    flakes = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)
    for _ in range(46):
        x, y = rng.uniform(10, 1014), rng.uniform(10, 860)
        r = rng.choice((3, 4, 5, 6))
        pygame.draw.circle(flakes, (255, 255, 255, rng.randint(110, 220)), P(x, y), L(r))
    surf.blit(flakes, (0, 0))


def artwork() -> pygame.Surface:
    surf = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)
    background(surf)
    g = strike_geometry()
    snow_ground(surf)

    def lower_body(layer):
        ground_shadow(layer)
        leg(layer, J["hip_back"], J["knee_back"], J["ankle_back"])            # pierna derecha
        leg(layer, J["hip_front"], J["knee_front"], J["ankle_front"])
        snow_on_boots(layer)
        torso(layer)

    place_layer(surf, lower_body, PIVOT, (PIVOT[0] + VIKING_DX, PIVOT[1]), 0, K)
    place_layer(surf, viking_head, NECK_LOCAL, V(neck_point()), LEAN, HEAD_SCALE * K)
    orb(surf, ORB_CENTER, ORB_RADIUS, ORANGE)
    snow_drift(surf)
    impact_on_orb(surf, g)
    arm(surf, V(J["shoulder_front"]), wrist_of(g, "front_hand", under=True), side=-1)   # izq.
    hammer_at(surf, g)                                         # el mango pasa por delante
    fist(surf, g["front_hand"], g["up"], g["into"], k=FIST * K, under=True)   # izquierda, debajo
    shoulder = V(J["shoulder_back"])                           # derecho, delante: baja por el
    arm(surf, shoulder, wrist_of(g, "back_hand"), side=1,      # costado hasta un codo bajo
        elbow=(shoulder[0] + RIGHT_ELBOW_DROP[0], shoulder[1] + RIGHT_ELBOW_DROP[1]))
    fist(surf, g["back_hand"], g["up"], g["into"], k=FIST * K)
    impact_effects(surf, g)
    snowflakes(surf)
    return surf


def macos_shape(art: pygame.Surface) -> pygame.Surface:
    """Icono de macOS: cuadrado redondeado de 824/1024 con margen y sombra (guía de Apple)."""
    out = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)
    inner = L(824)
    off = (CANVAS - inner) // 2
    shadow = pygame.Surface((CANVAS, CANVAS), pygame.SRCALPHA)
    for i in range(12, 0, -1):
        pygame.draw.rect(shadow, (0, 0, 0, 7), (off - i * 2, off + L(10) - i, inner + i * 4,
                                                inner + i * 3), border_radius=L(185) + i * 2)
    out.blit(shadow, (0, 0))
    mask = pygame.Surface((inner, inner), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=L(185))
    scaled = pygame.transform.smoothscale(art, (inner, inner))
    scaled.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    out.blit(scaled, (off, off))
    return out


def resized(surf, size):
    img = surf
    while img.get_width() // 2 >= size:                       # reducción por pasos: más nítido
        img = pygame.transform.smoothscale(img, (img.get_width() // 2, img.get_height() // 2))
    return pygame.transform.smoothscale(img, (size, size))


def png_bytes(surf) -> bytes:
    buf = io.BytesIO()
    pygame.image.save(surf, buf, "icon.png")
    return buf.getvalue()


def write_ico(path: Path, art):
    """.ico con imágenes PNG dentro (formato admitido desde Windows Vista)."""
    images = [png_bytes(resized(art, s)) for s in ICO_SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, data = b"", b""
    for size, img in zip(ICO_SIZES, images):
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(img),
                               offset + len(data))
        data += img
    path.write_bytes(header + entries + data)


def write_icns(path: Path, art):
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "icon.iconset"
        iconset.mkdir()
        for size in (16, 32, 128, 256, 512):
            pygame.image.save(resized(art, size), str(iconset / f"icon_{size}x{size}.png"))
            pygame.image.save(resized(art, size * 2), str(iconset / f"icon_{size}x{size}@2x.png"))
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(path)], check=True)


def main():
    pygame.init()
    art = artwork()
    flat = pygame.Surface(art.get_size())                     # iOS: sin transparencia
    flat.blit(art, (0, 0))
    for size in IOS_SIZES:
        pygame.image.save(resized(flat, size), str(OUT / f"icon-{size}.png"))
    pygame.image.save(resized(flat, 512), str(OUT / "icon.png"))
    mac = macos_shape(art)
    pygame.image.save(resized(mac, 512), str(OUT / "icon-macos.png"))   # ventana en macOS
    if shutil.which("iconutil"):
        write_icns(OUT / "icon.icns", mac)
    else:
        print("Aviso: iconutil no existe (solo en macOS); no se genera icon.icns")
    write_ico(OUT / "icon.ico", mac)
    print("Iconos generados en", OUT)


if __name__ == "__main__":
    main()
