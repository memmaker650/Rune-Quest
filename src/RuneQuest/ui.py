"""Utilidades de interfaz mínimas."""

import pygame

from . import settings as S
from .flags import flag_surface


def draw_text(surf, font, text, color, center=None, topleft=None, topright=None):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center is not None:
        rect.center = center
    if topleft is not None:
        rect.topleft = topleft
    if topright is not None:
        rect.topright = topright
    surf.blit(img, rect)
    return rect


class Button:
    def __init__(self, rect, label):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.pressed = False          # se dibuja más oscuro mientras está pulsado

    def hit(self, pos) -> bool:
        return self.rect.collidepoint(pos)

    def draw(self, surf, font):
        fill = S.BUTTON_PRESSED if self.pressed else S.BUTTON
        pygame.draw.rect(surf, fill, self.rect, border_radius=14)
        pygame.draw.rect(surf, S.BUTTON_EDGE, self.rect, width=2, border_radius=14)
        cx, cy = self.rect.center
        draw_text(surf, font, self.label, S.WHITE, center=(cx, cy + (1 if self.pressed else 0)))


class FlagButton:
    """Botón con la bandera del idioma activo."""

    def __init__(self, rect, flag):
        self.rect = pygame.Rect(rect)
        self.flag = flag
        self.pressed = False

    def hit(self, pos) -> bool:
        return self.rect.collidepoint(pos)

    def draw(self, surf):
        inner = self.rect.inflate(-8, -8)
        pygame.draw.rect(surf, S.BUTTON_PRESSED if self.pressed else S.BUTTON, self.rect,
                         border_radius=8)
        surf.blit(flag_surface(self.flag, inner.size), inner)
        if self.pressed:  # oscurece la bandera
            shade = pygame.Surface(inner.size, pygame.SRCALPHA)
            shade.fill((0, 0, 0, 90))
            surf.blit(shade, inner)
        pygame.draw.rect(surf, S.BUTTON_EDGE, self.rect, width=2, border_radius=8)
