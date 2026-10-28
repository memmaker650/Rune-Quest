"""Utilidades de interfaz mínimas."""

import math

import pygame

from . import settings as S
from .flags import flag_surface


def luminance(color) -> float:
    """Luminancia relativa (WCAG) de un color RGB: 0 = negro, 1 = blanco."""
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in color[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    """Contraste WCAG entre dos colores (1 a 21)."""
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def readable(color, background=S.OVER_PANEL, minimum=4.5):
    """``color`` si se lee bien sobre ``background``; si no (p. ej. negro), un gris claro."""
    return color if contrast(color, background) >= minimum else (200, 200, 212)


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


def draw_star(surf, center, radius, color, outline=None):
    """Estrella de 5 puntas (la fuente por defecto no tiene el carácter ★)."""
    cx, cy = center
    points = []
    for i in range(10):
        r = radius if i % 2 == 0 else radius * 0.45
        ang = math.radians(-90 + i * 36)
        points.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    pygame.draw.polygon(surf, color, points)
    if outline is not None:
        pygame.draw.polygon(surf, outline, points, 2)


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


class SegmentedControl:
    """Selector de varias opciones en fila (pestañas): la elegida va rellena."""

    def __init__(self, rect, labels, index, font):
        self.rect = pygame.Rect(rect)
        self.labels = labels
        self.index = index
        self.font = font
        self.pressed = False
        self.pressed_index = None
        w = self.rect.width / len(labels)
        self.segments = [pygame.Rect(round(self.rect.x + i * w), self.rect.y, round(w),
                                     self.rect.height) for i in range(len(labels))]

    def hit(self, pos) -> bool:
        return self.rect.collidepoint(pos)

    def segment_at(self, pos):
        return next((i for i, seg in enumerate(self.segments) if seg.collidepoint(pos)), None)

    def draw(self, surf):
        pygame.draw.rect(surf, S.BUTTON, self.rect, border_radius=12)
        for i, (seg, label) in enumerate(zip(self.segments, self.labels)):
            if i == self.index:
                pygame.draw.rect(surf, S.BUTTON_EDGE, seg.inflate(-6, -6), border_radius=9)
                color = S.BG                      # texto oscuro sobre la pestaña elegida
            else:
                if self.pressed and i == self.pressed_index:
                    pygame.draw.rect(surf, S.BUTTON_PRESSED, seg.inflate(-6, -6), border_radius=9)
                color = S.WHITE
            draw_text(surf, self.font, label, color, center=seg.center)
        pygame.draw.rect(surf, S.BUTTON_EDGE, self.rect, width=2, border_radius=12)


class SoundToggle:
    """Icono pequeño de activar/desactivar: "fx" (efectos) o "music" (dos corcheas unidas).
    Desactivado se ve apagado y tachado."""

    def __init__(self, rect, kind, on, font):
        self.rect = pygame.Rect(rect)
        self.kind = kind
        self.on = on
        self.font = font

    def hit(self, pos) -> bool:
        return self.rect.collidepoint(pos)

    def draw(self, surf):
        ink = S.WHITE if self.on else S.BUTTON_EDGE
        pygame.draw.rect(surf, S.BUTTON, self.rect, border_radius=6)
        pygame.draw.rect(surf, S.BUTTON_EDGE, self.rect, width=1, border_radius=6)
        cx, cy = self.rect.center
        if self.kind == "fx":
            draw_text(surf, self.font, "FX", ink, center=(cx, cy + 1))
        else:
            self._draw_notes(surf, ink, cx, cy)
        if not self.on:
            r = self.rect.inflate(-6, -6)
            pygame.draw.line(surf, S.DANGER, r.bottomleft, r.topright, 2)

    @staticmethod
    def _draw_notes(surf, ink, cx, cy):
        """Dos corcheas unidas por una barra (♫)."""
        heads = [(cx - 5, cy + 6), (cx + 5, cy + 4)]
        for hx, hy in heads:
            pygame.draw.ellipse(surf, ink, (hx - 4, hy - 3, 8, 6))
        stems = [(cx - 2, cy + 6), (cx + 8, cy + 4)]
        for (sx, sy) in stems:
            pygame.draw.line(surf, ink, (sx, sy), (sx, sy - 12), 2)
        pygame.draw.polygon(surf, ink, [(cx - 2, cy - 6), (cx + 8, cy - 8),
                                        (cx + 8, cy - 5), (cx - 2, cy - 3)])


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
