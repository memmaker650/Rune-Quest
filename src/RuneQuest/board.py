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
SURPRISE = 99                     # orbe sorpresa (modo Sorpresa): no forma grupos con nadie
# Vecinos de una celda: ortogonales y diagonales.


def neighbours(r: int, c: int) -> list:
    """Vecinos de (r, c) en la rejilla escalonada: las columnas impares están desplazadas media
    celda hacia abajo, así que cada orbe toca 6 orbes: arriba, abajo y dos en cada columna de al
    lado (en una columna par, la fila de arriba y la misma; en una impar, la misma y la de abajo).
    """
    side_rows = (r - 1, r) if c % 2 == 0 else (r, r + 1)
    return [(r - 1, c), (r + 1, c)] + [(sr, c + dc) for dc in (-1, 1) for sr in side_rows]
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
        self.next_color = self._random_color()   # color del próximo orbe que caerá con la lluvia

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
        """Orbes conectados (ver ``neighbours``) del mismo color que el de (r, c)."""
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return []
        color = self.grid[r][c]
        if color == EMPTY:
            return []
        seen = {(r, c)}
        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            for nr, nc in neighbours(cr, cc):
                if (0 <= nr < self.rows and 0 <= nc < self.cols
                        and (nr, nc) not in seen and self.grid[nr][nc] == color):
                    seen.add((nr, nc))
                    stack.append((nr, nc))
        return sorted(seen)

    def has_moves(self) -> bool:
        """True si existe algún grupo de al menos ``MIN_GROUP`` orbes. El orbe sorpresa no
        cuenta: aunque lo haya, sin grupos llueve igual (se pulsa cuando el jugador quiera)."""
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

    def find(self, value: int) -> Cell | None:
        """Primera celda con ``value`` (p. ej. el orbe sorpresa), o None."""
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == value:
                    return r, c
        return None

    def cells_within(self, r: int, c: int, depth: int) -> list[Cell]:
        """Celdas con orbe a ``depth`` pasos o menos de (r, c) en la rejilla escalonada,
        incluida (r, c). Cuenta los pasos aunque haya huecos por medio."""
        frontier, seen = [(r, c)], {(r, c)}
        for _ in range(depth):
            nxt = []
            for cell in frontier:
                for nr, nc in neighbours(*cell):
                    if 0 <= nr < self.rows and 0 <= nc < self.cols and (nr, nc) not in seen:
                        seen.add((nr, nc))
                        nxt.append((nr, nc))
            frontier = nxt
        return sorted(cell for cell in seen if self.grid[cell[0]][cell[1]] != EMPTY)

    def remove(self, cells) -> list[Move]:
        """Quita los orbes de ``cells`` y deja caer los de encima. Devuelve los movimientos."""
        for r, c in cells:
            self.grid[r][c] = EMPTY
        return self.settle()

    def rain(self) -> list[Move]:
        """Llena todos los huecos con orbes nuevos que caen desde encima del tablero.

        En cada columna los huecos están arriba (el tablero está asentado); los orbes nuevos
        caen como un bloque desde justo encima, así que el origen tiene fila negativa.
        """
        moves: list[Move] = []
        for c in range(self.cols):
            empty = sum(1 for r in range(self.rows) if self.grid[r][c] == EMPTY)
            for r in range(empty):
                self.grid[r][c] = self.next_color
                self.next_color = self._random_color()
                moves.append(((r - empty, c), (r, c)))
        log.debug("Lluvia: %d orbes nuevos", len(moves))
        return moves
