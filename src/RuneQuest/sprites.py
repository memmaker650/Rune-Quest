"""Dibujo de orbes con formas básicas (sin imágenes externas) y caché de sprites."""

import pygame

from . import settings as S

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
    else:
        pygame.draw.circle(surf, ink, (c, c), k, 3)


def orb_sprite(color_idx: int, size: int = S.CELL, assist: bool = False):
    """Superficie con transparencia de un orbe. Se dibuja una vez y se reutiliza."""
    key = (color_idx, size, assist)
    sprite = _cache.get(key)
    if sprite is not None:
        return sprite
    base = S.PALETTE[color_idx % len(S.PALETTE)]
    sprite = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    r = size // 2 - 3
    pygame.draw.circle(sprite, _shade(base, 0.55), (c, c), r + 1)
    pygame.draw.circle(sprite, base, (c, c), r - 1)
    pygame.draw.circle(sprite, _shade(base, 1.0 + 0.45), (c - r // 3, c - r // 3), max(2, r // 4))
    if assist:
        _glyph(sprite, color_idx % len(S.PALETTE), c, r, _shade(base, 0.45))
    _cache[key] = sprite
    return sprite
