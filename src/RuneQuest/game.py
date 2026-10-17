"""Reglas de la partida. Lógica pura (sin pygame).

El tablero empieza lleno. Cada toque sobre un grupo de >= MIN_GROUP orbes del mismo color lo
revienta y suma n*(n-1)*10 puntos; los orbes de encima caen. Cuando ya no quedan grupos
posibles, "llueven" orbes nuevos hasta llenar el tablero; si aun así no hay jugadas, se acaba.
Se sube de nivel por puntos; cada nivel añade un color a los orbes que llueven.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field

from . import settings as S
from .board import EMPTY, Board

log = logging.getLogger(__name__)


def level_params(level: int) -> dict:
    return {"colors": min(S.MAX_COLORS, S.START_COLORS + max(0, level - 1))}


def level_threshold(level: int) -> int:
    """Puntos necesarios para pasar del nivel ``level`` al siguiente."""
    return S.LEVEL_POINTS * level * (level + 1) // 2


def clear_points(n: int) -> int:
    return n * (n - 1) * S.POINTS_PER_PAIR


@dataclass
class Event:
    """Aviso para la capa visual: 'clear', 'rain', 'level' u 'over'."""
    kind: str
    data: dict = field(default_factory=dict)


class Game:
    def __init__(self, seed=None, level: int = 1, mode: str = S.GAME_MODES[0]):
        if mode not in S.GAME_MODES:
            log.warning("Modo de juego desconocido %r; se usa %r", mode, S.GAME_MODES[0])
            mode = S.GAME_MODES[0]
        self.mode = mode
        self.rng = random.Random(seed)
        self.score = 0
        self.level = level
        self.over = False
        self.taps = 0                 # toques válidos totales
        self.rains = 0
        self.best_chain = 0
        self.events: list[Event] = []
        p = level_params(level)
        log.info("Nueva partida (modo %s) en el nivel %d: %s", mode, level, p)
        self.board = Board(n_colors=p["colors"], rng=self.rng)
        self.board.fill()

    # --- guardar / restaurar ---
    def to_state(self) -> dict:
        """Estado serializable de la partida: marcadores y cada bola con su fila, columna y color."""
        b = self.board
        return {
            "score": self.score, "level": self.level, "taps": self.taps, "rains": self.rains,
            "best_chain": self.best_chain, "mode": self.mode, "rows": b.rows, "cols": b.cols,
            "balls": [[r, c, b.grid[r][c]] for r in range(b.rows) for c in range(b.cols)
                      if b.grid[r][c] != EMPTY],
        }

    @classmethod
    def from_state(cls, state: dict, seed=None) -> "Game":
        """Reconstruye una partida guardada con ``to_state``. ValueError si no es válida."""
        g = cls(seed=seed, level=int(state["level"]), mode=state.get("mode", S.GAME_MODES[0]))
        if (state["rows"], state["cols"]) != (g.board.rows, g.board.cols):
            raise ValueError(f"tablero guardado de {state['rows']}x{state['cols']}, "
                             f"se esperaba {g.board.rows}x{g.board.cols}")
        g.score = int(state["score"])
        g.taps = int(state.get("taps", 0))
        g.rains = int(state.get("rains", 0))
        g.best_chain = int(state.get("best_chain", 0))
        grid = [[EMPTY] * g.board.cols for _ in range(g.board.rows)]
        for r, c, color in state["balls"]:
            if not (0 <= r < g.board.rows and 0 <= c < g.board.cols and 0 <= color < S.MAX_COLORS):
                raise ValueError(f"bola fuera de rango: fila {r}, columna {c}, color {color}")
            grid[r][c] = color
        g.board.grid = grid
        g.board.settle()              # por si el estado guardado tuviera huecos bajo una bola
        log.info("Partida restaurada: %d puntos, nivel %d, %d bolas",
                 g.score, g.level, g.board.count())
        if not g.board.has_moves():
            log.warning("La partida restaurada no tenía jugadas: llueve")
            g._rain()
        return g

    @property
    def next_level_at(self) -> int:
        return level_threshold(self.level)

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

        while self.score >= self.next_level_at:
            self._level_up()
        if not self.board.has_moves():
            self._rain()
        return True

    def _rain(self) -> None:
        self.rains += 1
        log.info("Sin jugadas posibles: lluvia de orbes n.º %d", self.rains)
        self.events.append(Event("rain", {"moves": self.board.rain()}))
        if not self.board.has_moves():
            self.over = True
            log.info("Fin de la partida: %d puntos, nivel %d, mejor cadena %d",
                     self.score, self.level, self.best_chain)
            self.events.append(Event("over", {"score": self.score, "level": self.level}))

    def _level_up(self) -> None:
        self.level += 1
        p = level_params(self.level)
        self.board.n_colors = p["colors"]
        log.info("Subida al nivel %d con %d puntos: %s", self.level, self.score, p)
        self.events.append(Event("level", {"level": self.level}))
