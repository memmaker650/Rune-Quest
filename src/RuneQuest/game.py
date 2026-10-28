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
from .board import EMPTY, SURPRISE, Board, neighbours

log = logging.getLogger(__name__)


# Efectos del orbe sorpresa (misma probabilidad cada uno):
#   vanish    desaparece y los de encima caen a ocupar el hueco
#   explode   explota y destruye también sus 6 vecinos
#   neighbour se convierte en el color de uno de sus vecinos, al azar
#   next      se convierte en el color del próximo orbe que caerá
#   mega      mega explosión: destruye todo a SURPRISE_MEGA_DEPTH pasos o menos
SURPRISE_EFFECTS = ("vanish", "explode", "neighbour", "next", "mega")


def level_params(level: int) -> dict:
    return {"colors": min(S.MAX_COLORS, S.START_COLORS + max(0, level - 1))}


def level_threshold(level: int) -> int:
    """Puntos necesarios para pasar del nivel ``level`` al siguiente."""
    return S.LEVEL_POINTS * level * (level + 1) // 2


def clear_points(n: int) -> int:
    return n * (n - 1) * S.POINTS_PER_PAIR


@dataclass
class Event:
    """Aviso para la capa visual: 'clear', 'color_clear', 'board_clear', 'rain', 'level',
    'surprise_spawn', 'surprise' u 'over'."""
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
            valid_color = 0 <= color < S.MAX_COLORS or color == SURPRISE
            if not (0 <= r < g.board.rows and 0 <= c < g.board.cols and valid_color):
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
        if self.board.get(r, c) == SURPRISE:
            self.open_surprise(r, c)
            return True
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
        self._check_clear_bonuses({result.color})
        self._after_move()
        return True

    def _after_move(self) -> None:
        while self.score >= self.next_level_at:
            self._level_up()
        if not self.board.has_moves():
            self._rain()

    # --- orbe sorpresa ---
    def open_surprise(self, r: int, c: int, effect: str | None = None) -> None:
        """Pulsar el orbe sorpresa de (r, c): aplica ``effect`` (o uno al azar)."""
        board = self.board
        effect = effect or self.rng.choice(SURPRISE_EFFECTS)
        destroyed, color = [], None
        if effect == "vanish":
            destroyed = [(r, c)]
        elif effect == "explode":
            destroyed = board.cells_within(r, c, 1)
        elif effect == "mega":
            destroyed = board.cells_within(r, c, S.SURPRISE_MEGA_DEPTH)
        elif effect == "neighbour":
            around = [board.get(nr, nc) for nr, nc in neighbours(r, c)
                      if 0 <= nr < board.rows and 0 <= nc < board.cols]
            around = [v for v in around if v != EMPTY and v != SURPRISE]
            color = self.rng.choice(around) if around else board.next_color
        elif effect == "next":
            color = board.next_color
        else:
            raise ValueError(f"efecto sorpresa desconocido: {effect!r}")

        colors = {board.get(*cell) for cell in destroyed} - {SURPRISE}
        orbs = [cell for cell in destroyed if board.get(*cell) != SURPRISE]
        points = clear_points(len(orbs)) if orbs else 0
        cell_colors = [board.get(*cell) for cell in destroyed]
        moves = []
        if color is not None:
            board.grid[r][c] = color
        else:
            moves = board.remove(destroyed)
        self.score += points
        self.taps += 1
        log.info("Orbe sorpresa en (%d, %d): %s (%d orbes destruidos, +%d)",
                 r, c, effect, len(orbs), points)
        self.events.append(Event("surprise", {
            "cell": (r, c), "effect": effect, "cells": destroyed, "colors": cell_colors,
            "color": color, "points": points, "moves": moves,
        }))
        if colors:
            self._check_clear_bonuses(colors)
        self._after_move()

    def _maybe_spawn_surprise(self) -> None:
        """En modo sorpresa, a partir de SURPRISE_FIRST_LEVEL y cada SURPRISE_EVERY niveles, un
        orbe al azar se convierte en orbe sorpresa (solo puede haber uno a la vez)."""
        if self.mode != "surprise" or self.level < S.SURPRISE_FIRST_LEVEL:
            return
        if (self.level - S.SURPRISE_FIRST_LEVEL) % S.SURPRISE_EVERY:
            return
        board = self.board
        if board.find(SURPRISE) is not None:
            log.info("Nivel %d: ya hay un orbe sorpresa en el tablero", self.level)
            return
        cells = [(r, c) for r in range(board.rows) for c in range(board.cols)
                 if board.grid[r][c] not in (EMPTY, SURPRISE)]
        if not cells:
            return
        r, c = self.rng.choice(cells)
        board.grid[r][c] = SURPRISE
        log.info("Nivel %d: aparece un orbe sorpresa en (%d, %d)", self.level, r, c)
        self.events.append(Event("surprise_spawn", {"cell": (r, c)}))

    def _check_clear_bonuses(self, colors) -> None:
        """Bonus por cada color de ``colors`` que ya no quede en el tablero y por dejar el
        tablero vacío (el último grupo de una pantalla limpia gana los dos)."""
        for color in sorted(colors):
            if any(v == color for row in self.board.grid for v in row):
                continue
            self.score += S.COLOR_CLEAR_BONUS
            log.info("Color %d eliminado del tablero: +%d", color, S.COLOR_CLEAR_BONUS)
            self.events.append(Event("color_clear", {"color": color,
                                                     "bonus": S.COLOR_CLEAR_BONUS}))
        if self.board.is_empty():
            self.score += S.BOARD_CLEAR_BONUS
            log.info("¡Tablero limpio!: +%d", S.BOARD_CLEAR_BONUS)
            self.events.append(Event("board_clear", {"bonus": S.BOARD_CLEAR_BONUS}))

    def _rain(self) -> None:
        self.rains += 1
        log.info("Sin jugadas posibles: lluvia de orbes n.º %d", self.rains)
        self.events.append(Event("rain", {"moves": self.board.rain()}))
        # Sin grupos tras la lluvia se acaba, salvo que quede el orbe sorpresa por pulsar.
        if not self.board.has_moves() and self.board.find(SURPRISE) is None:
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
        self._maybe_spawn_surprise()
