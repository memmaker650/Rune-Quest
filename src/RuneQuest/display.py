"""Superficie lógica fija escalada a la ventana (con barras) y conversión de coordenadas."""

import logging
import sys

import pygame

from . import settings as S

log = logging.getLogger(__name__)

FINGER_EVENTS = (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION)

class Display:
    def __init__(self):
        if sys.platform == "ios":
            size = (0, 0)  # pantalla completa nativa
        else:
            size = (S.LOGICAL_W, S.LOGICAL_H)
        try:
            self.window = pygame.display.set_mode(size, pygame.RESIZABLE)
        except pygame.error:
            log.exception("No se pudo crear la ventana %s", size)
            raise
        log.info("Ventana creada: %s (driver %s)", self.window.get_size(),
                 pygame.display.get_driver())
        self.surface = pygame.Surface((S.LOGICAL_W, S.LOGICAL_H))
        self.scale = 1.0
        self.offset = (0.0, 0.0)
        self._last_size = None
        self._layout()

    def _layout(self):
        ww, wh = self.window.get_size()
        if (ww, wh) != self._last_size:
            self._last_size = (ww, wh)
            if ww <= 0 or wh <= 0:
                log.warning("Tamaño de ventana no válido: %dx%d; se mantiene la escala", ww, wh)
            else:
                log.info("Tamaño de ventana: %dx%d", ww, wh)
        if ww <= 0 or wh <= 0:
            return  # ventana minimizada: evita escala 0 y divisiones por cero
        self.scale = min(ww / S.LOGICAL_W, wh / S.LOGICAL_H)
        self.offset = (
            (ww - S.LOGICAL_W * self.scale) / 2,
            (wh - S.LOGICAL_H * self.scale) / 2,
        )

    def present(self):
        self._layout()
        size = (max(1, int(S.LOGICAL_W * self.scale)),
                max(1, int(S.LOGICAL_H * self.scale)))
        self.window.fill(S.BLACK)
        self.window.blit(pygame.transform.smoothscale(self.surface, size), self.offset)
        pygame.display.flip()

    def to_logical(self, px, py):
        return ((px - self.offset[0]) / self.scale, (py - self.offset[1]) / self.scale)

    def event_pos(self, event):
        """Posición lógica de un evento de ratón o de dedo (el dedo viene normalizado 0..1)."""
        if event.type in FINGER_EVENTS:
            ww, wh = self.window.get_size()
            return self.to_logical(event.x * ww, event.y * wh)
        return self.to_logical(*event.pos)
