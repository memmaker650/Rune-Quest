"""Reglas de la partida. Lógica pura (sin pygame).

Cada toque sobre un grupo de >= 2 orbes del mismo color lo revienta y suma n*(n-1)*10 puntos.
Cada ``interval`` toques válidos sube una fila nueva por abajo; si la pila llega arriba, se acaba.
Si no quedan jugadas, suben filas hasta que haya alguna (o se llene la pantalla).
Al vaciar el tablero se pasa de nivel: más filas, más colores y filas nuevas más frecuentes.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field

from . import settings as S
from .board import Board

log = logging.getLogger(__name__)


def level_params(level: int) -> dict:
    step = max(0, level - 1)
    return {
        "colors": min(S.MAX_COLORS, S.START_COLORS + step // 2),
        "rows": min(S.MAX_START_ROWS, S.START_ROWS + step // 2),
        "interval": max(S.MIN_PUSH_INTERVAL, S.START_PUSH_INTERVAL - step // 3),
    }


def clear_points(n: int) -> int:
    return n * (n - 1) * S.POINTS_PER_PAIR


@dataclass
class Event:
    """Aviso para la capa visual: 'clear', 'push', 'level' u 'over'."""
    kind: str
    data: dict = field(default_factory=dict)


class Game:
    def __init__(self, seed=None, level: int = 1):
        self.rng = random.Random(seed)
        self.score = 0
        self.level = level
        self.over = False
        self.taps = 0                 # toques válidos totales
        self.best_chain = 0
        self.taps_since_push = 0
        self.events: list[Event] = []
        self._start_level()

    # --- nivel ---
    def _start_level(self) -> None:
        p = level_params(self.level)
        log.info("Empieza el nivel %d: %s", self.level, p)
        self.interval = p["interval"]
        self.taps_since_push = 0
        self.board = Board(n_colors=p["colors"], rng=self.rng)
        self.board.fill(p["rows"])

    @property
    def pushes_in(self) -> int:
        """Toques válidos que faltan para que suba la próxima fila."""
        return self.interval - self.taps_since_push

    def pop_events(self) -> list[Event]:
        events, self.events = self.events, []
        return events

    # --- jugada ---
    def tap(self, r: int, c: int) -> bool:
        """Procesa un toque. True si reventó algo."""
        if self.over:
            log.warning("Toque en (%d, %d) con la partida ya terminada; se ignora", r, c)
            return False
        result = self.board.clear_group(r, c)
        if result is None:
            return False

        n = len(result.cells)
        points = clear_points(n)
        self.score += points
        self.taps += 1
        self.best_chain = max(self.best_chain, n)
        self.events.append(Event("clear", {
            "cells": result.cells, "color": result.color, "points": points,
            "moves": result.moves,
        }))

        if self.board.is_empty():
            self._level_up()
            return True

        self.taps_since_push += 1
        if self.taps_since_push >= self.interval:
            self._push()
        if not self.over and not self.board.has_moves():
            log.info("Sin jugadas posibles: se suben filas hasta que haya alguna")
        while not self.over and not self.board.has_moves():
            self._push()              # sin jugadas: sube fila hasta que haya o se llene
        return True

    def _push(self) -> None:
        self.taps_since_push = 0
        moves = self.board.push_row()
        if moves is None:
            self.over = True
            log.info("Fin de la partida: %d puntos, nivel %d, mejor cadena %d",
                     self.score, self.level, self.best_chain)
            self.events.append(Event("over", {"score": self.score, "level": self.level}))
        else:
            self.events.append(Event("push", {"moves": moves}))

    def _level_up(self) -> None:
        bonus = S.LEVEL_BONUS * self.level
        log.info("Nivel %d completado (+%d de bonus)", self.level, bonus)
        self.score += bonus
        self.level += 1
        self._start_level()
        self.events.append(Event("level", {"level": self.level, "bonus": bonus}))
