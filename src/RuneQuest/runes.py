"""Las 12 runas nórdicas (Futhark antiguo) que se pueden dibujar sobre los orbes.

Cada runa se define como trazos rectos (así se tallaban), en coordenadas normalizadas:
x de -1 a 1 (izquierda a derecha) e y de -1 a 1 (arriba a abajo). Se dibujan con líneas,
porque la fuente por defecto de pygame no tiene los caracteres rúnicos de Unicode.

El orden importa: el color ``i`` de los orbes usa la runa ``RUNES[i]``. Las seis primeras son
las de formas más distintas entre sí, porque hoy el juego usa como mucho 6 colores
(``settings.MAX_COLORS``); las otras seis quedan listas por si se añaden más colores.
"""

from dataclasses import dataclass

import pygame

Point = tuple[float, float]


@dataclass(frozen=True)
class Rune:
    name: str                          # nombre en protonórdico
    char: str                          # carácter Unicode (bloque rúnico), para referencia
    meaning: str
    strokes: tuple[tuple[Point, ...], ...]   # cada trazo es una polilínea


RUNES: tuple[Rune, ...] = (
    Rune("Fehu", "ᚠ", "ganado, riqueza", (
        ((-0.45, -1.0), (-0.45, 1.0)),
        ((-0.45, -0.25), (0.5, -0.95)),
        ((-0.45, 0.3), (0.5, -0.4)),
    )),
    Rune("Uruz", "ᚢ", "uro, fuerza", (
        ((-0.5, 1.0), (-0.5, -1.0), (0.5, -0.45), (0.5, 1.0)),
    )),
    Rune("Gebo", "ᚷ", "regalo", (
        ((-0.65, -1.0), (0.65, 1.0)),
        ((0.65, -1.0), (-0.65, 1.0)),
    )),
    Rune("Tiwaz", "ᛏ", "Tyr, justicia", (
        ((0.0, -1.0), (0.0, 1.0)),
        ((-0.6, -0.35), (0.0, -1.0), (0.6, -0.35)),
    )),
    Rune("Algiz", "ᛉ", "protección", (
        ((0.0, -1.0), (0.0, 1.0)),
        ((-0.6, -0.65), (0.0, 0.05), (0.6, -0.65)),
    )),
    Rune("Hagalaz", "ᚺ", "granizo", (
        ((-0.5, -1.0), (-0.5, 1.0)),
        ((0.5, -1.0), (0.5, 1.0)),
        ((-0.5, -0.3), (0.5, 0.3)),
    )),
    Rune("Thurisaz", "ᚦ", "gigante, espina", (
        ((-0.4, -1.0), (-0.4, 1.0)),
        ((-0.4, -0.5), (0.45, 0.0), (-0.4, 0.5)),
    )),
    Rune("Ansuz", "ᚨ", "dios, inspiración", (
        ((-0.45, -1.0), (-0.45, 1.0)),
        ((-0.45, -0.85), (0.5, -0.3)),
        ((-0.45, -0.3), (0.5, 0.25)),
    )),
    Rune("Raidho", "ᚱ", "viaje", (
        ((-0.45, 1.0), (-0.45, -1.0), (0.4, -0.5), (-0.45, 0.0), (0.5, 1.0)),
    )),
    Rune("Kenaz", "ᚲ", "antorcha", (
        ((0.45, -0.75), (-0.4, 0.0), (0.45, 0.75)),
    )),
    Rune("Wunjo", "ᚹ", "alegría", (
        ((-0.4, 1.0), (-0.4, -1.0), (0.45, -0.5), (-0.4, 0.0)),
    )),
    Rune("Isa", "ᛁ", "hielo", (
        ((0.0, -1.0), (0.0, 1.0)),
    )),
)


def rune_for_color(color_idx: int) -> Rune:
    return RUNES[color_idx % len(RUNES)]


def draw_rune(surf, rune: Rune, center, half_height: float, color, width: int) -> None:
    """Dibuja ``rune`` centrada en ``center``; ``half_height`` es la mitad de su altura en píxeles."""
    cx, cy = center
    for stroke in rune.strokes:
        points = [(round(cx + x * half_height), round(cy + y * half_height)) for x, y in stroke]
        pygame.draw.lines(surf, color, False, points, width)
        for p in points:  # remata las uniones para que no queden muescas
            pygame.draw.circle(surf, color, p, max(1, width // 2))
