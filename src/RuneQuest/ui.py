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


def draw_text_outlined(surf, font, text, color, outline, center, thickness=2):
    """Texto con contorno: se lee bien aunque el fondo tenga zonas claras."""
    shadow = font.render(text, True, outline)
    rect = shadow.get_rect(center=center)
    for dx in range(-thickness, thickness + 1):
        for dy in range(-thickness, thickness + 1):
            if dx or dy:
                surf.blit(shadow, rect.move(dx, dy))
    surf.blit(font.render(text, True, color), rect)
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


class CloseButton:
    """Botón cuadrado con una X (salir)."""

    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.pressed = False

    def hit(self, pos) -> bool:
        return self.rect.collidepoint(pos)

    def draw(self, surf):
        pygame.draw.rect(surf, S.BUTTON_PRESSED if self.pressed else S.BUTTON, self.rect,
                         border_radius=8)
        pygame.draw.rect(surf, S.BUTTON_EDGE, self.rect, width=2, border_radius=8)
        k = self.rect.width // 4
        cx, cy = self.rect.center
        cy += 1 if self.pressed else 0
        pygame.draw.line(surf, S.WHITE, (cx - k, cy - k), (cx + k, cy + k), 4)
        pygame.draw.line(surf, S.WHITE, (cx - k, cy + k), (cx + k, cy - k), 4)


class ModeButton(Button):
    """Selector: subtítulo pequeño arriba, opción actual en grande y un punto por opción."""

    def __init__(self, rect, subtitle, label, index, count, small_font):
        super().__init__(rect, label)
        self.subtitle = subtitle
        self.index = index
        self.count = count
        self.small_font = small_font

    def draw(self, surf, font):
        fill = S.BUTTON_PRESSED if self.pressed else S.BUTTON
        pygame.draw.rect(surf, fill, self.rect, border_radius=14)
        pygame.draw.rect(surf, S.BUTTON_EDGE, self.rect, width=2, border_radius=14)
        dy = 1 if self.pressed else 0
        cx = self.rect.centerx
        draw_text(surf, self.small_font, self.subtitle, S.ACCENT,
                  center=(cx, self.rect.top + 16 + dy))
        draw_text(surf, font, self.label, S.WHITE, center=(cx, self.rect.centery + 4 + dy))
        for i in range(self.count):
            x = cx + (i - (self.count - 1) / 2) * 16
            pygame.draw.circle(surf, S.ACCENT if i == self.index else S.BUTTON_EDGE,
                               (round(x), self.rect.bottom - 12 + dy), 4 if i == self.index else 3)


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
