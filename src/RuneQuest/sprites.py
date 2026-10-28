"""Dibujo de orbes con formas básicas (sin imágenes externas) y caché de sprites."""

import logging

import pygame

from . import settings as S
from .board import SURPRISE
from .runes import draw_rune, rune_for_color
from .ui import contrast, luminance

log = logging.getLogger(__name__)

_cache: dict = {}


def _shade(color, factor):
    return tuple(max(0, min(255, int(v * factor))) for v in color)


def _glyph(surf, color_idx, c, r, ink):
    """Marca interior distinta por color: ayuda a distinguirlos sin depender del color."""
    k = max(3, r // 2)
    if color_idx == 0:
        pygame.draw.rect(surf, ink, (c - k, c - k, 2 * k, 2 * k))
    elif color_idx == 1:
        pygame.draw.circle(surf, ink, (c, c), k)
    elif color_idx == 2:
        pygame.draw.polygon(surf, ink, [(c, c - k - 1), (c - k - 1, c + k), (c + k + 1, c + k)])
    elif color_idx == 3:
        pygame.draw.polygon(surf, ink, [(c, c - k - 2), (c + k + 2, c), (c, c + k + 2), (c - k - 2, c)])
    elif color_idx == 4:
        pygame.draw.line(surf, ink, (c - k, c), (c + k, c), 4)
        pygame.draw.line(surf, ink, (c, c - k), (c, c + k), 4)
    elif color_idx == 5:
        pygame.draw.circle(surf, ink, (c, c), k, 3)
    elif color_idx == 6:                                  # aspa
        pygame.draw.line(surf, ink, (c - k, c - k), (c + k, c + k), 4)
        pygame.draw.line(surf, ink, (c - k, c + k), (c + k, c - k), 4)
    elif color_idx == 7:                                  # cuadrado hueco
        pygame.draw.rect(surf, ink, (c - k, c - k, 2 * k, 2 * k), 3)
    elif color_idx == 8:                                  # triángulo invertido
        pygame.draw.polygon(surf, ink, [(c, c + k + 1), (c - k - 1, c - k), (c + k + 1, c - k)])
    elif color_idx == 9:                                  # dos barras
        pygame.draw.rect(surf, ink, (c - k, c - k, k * 2 // 3, 2 * k))
        pygame.draw.rect(surf, ink, (c + k - k * 2 // 3, c - k, k * 2 // 3, 2 * k))
    elif color_idx == 10:                                 # triángulo hueco
        pygame.draw.polygon(surf, ink, [(c, c - k - 1), (c - k - 1, c + k), (c + k + 1, c + k)], 3)
    elif color_idx == 11:                                 # barra horizontal gruesa
        pygame.draw.rect(surf, ink, (c - k, c - k // 3, 2 * k, 2 * (k // 3) + 1))
    else:                                                 # tres puntos
        for dx in (-k, 0, k):
            pygame.draw.circle(surf, ink, (c + dx, c), max(2, k // 3))


def _surprise_sprite(size: int):
    """Orbe sorpresa: blanco, con brillo y un signo de interrogación negro."""
    sprite = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    r = size // 2 - 3
    pygame.draw.circle(sprite, S.GOLD, (c, c), r + 1)          # anillo dorado: no se confunde
    pygame.draw.circle(sprite, S.SURPRISE_ORB, (c, c), r - 2)  # con un orbe blanco normal
    pygame.draw.circle(sprite, (255, 255, 255), (c - r // 3, c - r // 3), max(2, r // 4))
    mark = pygame.font.Font(None, int(size * 0.95)).render("?", True, S.SURPRISE_INK)
    sprite.blit(mark, mark.get_rect(center=(c, c + 2)))
    return sprite


def orb_sprite(color_idx: int, size: int = S.CELL, assist: str = "none"):
    """Superficie con transparencia de un orbe. Se dibuja una vez y se reutiliza.

    ``assist`` (ver ``settings.ASSIST_MODES``) añade una marca que distingue el color sin
    depender de él: "geo" = forma geométrica, "runes" = runa nórdica.
    """
    key = (color_idx, size, assist)
    sprite = _cache.get(key)
    if sprite is not None:
        return sprite
    if color_idx == SURPRISE:
        sprite = _surprise_sprite(size)
        _cache[key] = sprite
        return sprite
    if not 0 <= color_idx < len(S.PALETTE):
        log.warning("Índice de color fuera de la paleta: %d (se usa %d)",
                    color_idx, color_idx % len(S.PALETTE))
    base = S.PALETTE[color_idx % len(S.PALETTE)]
    sprite = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    r = size // 2 - 3
    dark = luminance(base) < 0.05                 # negro: sin esto no se ve sobre el fondo
    rim = (150, 150, 168) if dark else _shade(base, 0.55)
    shine = (120, 120, 136) if dark else _shade(base, 1.0 + 0.45)
    # Tinta de la marca de ayuda: la clara o la oscura, la que más contraste con este color.
    ink = max(((215, 215, 225), _shade(base, 0.3)), key=lambda c: contrast(c, base))
    pygame.draw.circle(sprite, rim, (c, c), r + 1)
    pygame.draw.circle(sprite, base, (c, c), r - 1)
    pygame.draw.circle(sprite, shine, (c - r // 3, c - r // 3), max(2, r // 4))
    if assist == "geo":
        _glyph(sprite, color_idx % len(S.PALETTE), c, r, ink)
    elif assist == "runes":
        draw_rune(sprite, rune_for_color(color_idx % len(S.PALETTE)), (c, c), r * 0.52,
                  ink, max(2, size // 15))
    elif assist != "none":
        log.warning("Modo de ayuda desconocido %r; se dibuja sin ayuda", assist)
    _cache[key] = sprite
    return sprite
