"""Tablero de orbes. Lógica pura: no importa pygame, se prueba sin ventana.

El tablero es una rejilla ``grid[fila][columna]`` (fila 0 = arriba). Cada celda guarda el índice
de color del orbe o ``EMPTY``. Los orbes siempre forman pilas apoyadas en el fondo; solo caen
en vertical, nunca cambian de columna (una columna vacía se queda vacía). Empieza lleno y, cuando ya no hay jugadas, ``rain``
vuelve a llenar los huecos con orbes que caen desde arriba.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass

from . import settings as S

log = logging.getLogger(__name__)

EMPTY = -1
# Vecinos de una celda: ortogonales y diagonales.
NEIGHBOURS = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]
Cell = tuple[int, int]            # (fila, columna)
Move = tuple[Cell, Cell]          # (origen, destino); una fila < 0 está sobre el tablero


@dataclass
class Clear:
    cells: list[Cell]             # celdas reventadas (antes de recolocar)
    color: int
    moves: list[Move]             # movimientos de los orbes restantes


class Board:
    def __init__(self, cols=S.COLS, rows=S.ROWS, n_colors=S.START_COLORS, rng=None):
        self.cols = cols
        self.rows = rows
        self.n_colors = n_colors
        self.rng = rng or random.Random()
        self.grid = [[EMPTY] * cols for _ in range(rows)]

    # --- construcción ---
    @classmethod
    def from_text(cls, lines, n_colors=S.START_COLORS, rng=None) -> "Board":
        """Crea un tablero desde texto: dígito = color, '.' = vacío (útil en tests)."""
        board = cls(len(lines[0]), len(lines), n_colors, rng)
        for r, line in enumerate(lines):
            if len(line) != board.cols:
                log.error("Fila %d de longitud %d; se esperaban %d columnas", r, len(line), board.cols)
                raise ValueError(f"fila {r} con longitud distinta: {line!r}")
            for c, ch in enumerate(line):
                board.grid[r][c] = EMPTY if ch == "." else int(ch)
        return board

    def to_text(self) -> list[str]:
        return ["".join("." if v == EMPTY else str(v) for v in row) for row in self.grid]

    def _random_color(self) -> int:
        return self.rng.randrange(self.n_colors)

    def fill(self) -> None:
        """Llena todo el tablero al azar, asegurando que haya jugadas."""
        for attempt in range(200):
            self.grid = [[self._random_color() for _ in range(self.cols)]
                         for _ in range(self.rows)]
            if self.has_moves():
                log.debug("Tablero lleno en %d intentos", attempt + 1)
                return
        log.warning("No se encontró un tablero con jugadas tras 200 intentos (%d colores)",
                    self.n_colors)

    # --- consultas ---
    def get(self, r: int, c: int) -> int:
        return self.grid[r][c]

    def count(self) -> int:
        return sum(v != EMPTY for row in self.grid for v in row)

    def is_empty(self) -> bool:
        return self.count() == 0

    def height(self) -> int:
        """Altura de la pila más alta (en orbes)."""
        for r in range(self.rows):
            if any(v != EMPTY for v in self.grid[r]):
                return self.rows - r
        return 0

    def group_at(self, r: int, c: int) -> list[Cell]:
        """Orbes conectados (en horizontal, vertical o diagonal) del mismo color que (r, c)."""
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return []
        color = self.grid[r][c]
        if color == EMPTY:
            return []
        seen = {(r, c)}
        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            for dr, dc in NEIGHBOURS:
                nr, nc = cr + dr, cc + dc
                if (0 <= nr < self.rows and 0 <= nc < self.cols
                        and (nr, nc) not in seen and self.grid[nr][nc] == color):
                    seen.add((nr, nc))
                    stack.append((nr, nc))
        return sorted(seen)

    def has_moves(self) -> bool:
        """True si existe algún grupo de al menos ``MIN_GROUP`` orbes."""
        seen: set[Cell] = set()
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) in seen or self.grid[r][c] == EMPTY:
                    continue
                group = self.group_at(r, c)
                if len(group) >= S.MIN_GROUP:
                    return True
                seen.update(group)
        return False

    # --- acciones ---
    def clear_group(self, r: int, c: int) -> Clear | None:
        """Revienta el grupo de (r, c). Devuelve None si no llega al mínimo."""
        group = self.group_at(r, c)
        if len(group) < S.MIN_GROUP:
            return None
        color = self.grid[r][c]
        for gr, gc in group:
            self.grid[gr][gc] = EMPTY
        return Clear(group, color, self.settle())

    def settle(self) -> list[Move]:
        """Gravedad hacia abajo: cada orbe cae dentro de su propia columna."""
        moves: list[Move] = []
        for c in range(self.cols):
            stack = [(self.grid[r][c], r)       # de abajo hacia arriba
                     for r in range(self.rows - 1, -1, -1) if self.grid[r][c] != EMPTY]
            for r in range(self.rows):
                self.grid[r][c] = EMPTY
            for i, (color, sr) in enumerate(stack):
                nr = self.rows - 1 - i
                self.grid[nr][c] = color
                if sr != nr:
                    moves.append(((sr, c), (nr, c)))
        return moves

    def rain(self) -> list[Move]:
        """Llena todos los huecos con orbes nuevos que caen desde encima del tablero.

        En cada columna los huecos están arriba (el tablero está asentado); los orbes nuevos
        caen como un bloque desde justo encima, así que el origen tiene fila negativa.
        """
        moves: list[Move] = []
        for c in range(self.cols):
            empty = sum(1 for r in range(self.rows) if self.grid[r][c] == EMPTY)
            for r in range(empty):
                self.grid[r][c] = self._random_color()
                moves.append(((r - empty, c), (r, c)))
        log.debug("Lluvia: %d orbes nuevos", len(moves))
        return moves
