"""Tablero de orbes. Lógica pura: no importa pygame, se prueba sin ventana.

El tablero es una rejilla ``grid[fila][columna]`` (fila 0 = arriba). Cada celda guarda el índice
de color del orbe o ``EMPTY``. Los orbes siempre forman pilas apoyadas en el fondo y las columnas
vacías se compactan hacia la izquierda.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from . import settings as S

EMPTY = -1
Cell = tuple[int, int]            # (fila, columna)
Move = tuple[Cell, Cell]          # (origen, destino); una fila == ROWS está bajo el tablero


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
        self.next_row = self._random_row()

    # --- construcción ---
    @classmethod
    def from_text(cls, lines, n_colors=S.START_COLORS, rng=None) -> "Board":
        """Crea un tablero desde texto: dígito = color, '.' = vacío (útil en tests)."""
        board = cls(len(lines[0]), len(lines), n_colors, rng)
        for r, line in enumerate(lines):
            for c, ch in enumerate(line):
                board.grid[r][c] = EMPTY if ch == "." else int(ch)
        return board

    def to_text(self) -> list[str]:
        return ["".join("." if v == EMPTY else str(v) for v in row) for row in self.grid]

    def _random_row(self) -> list[int]:
        return [self.rng.randrange(self.n_colors) for _ in range(self.cols)]

    def fill(self, n_rows: int) -> None:
        """Rellena las ``n_rows`` filas inferiores al azar, asegurando que haya jugadas."""
        n_rows = min(n_rows, self.rows - 1)
        for _ in range(200):
            self.grid = [[EMPTY] * self.cols for _ in range(self.rows)]
            for r in range(self.rows - n_rows, self.rows):
                self.grid[r] = self._random_row()
            if self.has_moves():
                return

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
        """Orbes conectados (ortogonalmente) del mismo color que el de (r, c)."""
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return []
        color = self.grid[r][c]
        if color == EMPTY:
            return []
        seen = {(r, c)}
        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            for nr, nc in ((cr - 1, cc), (cr + 1, cc), (cr, cc - 1), (cr, cc + 1)):
                if (0 <= nr < self.rows and 0 <= nc < self.cols
                        and (nr, nc) not in seen and self.grid[nr][nc] == color):
                    seen.add((nr, nc))
                    stack.append((nr, nc))
        return sorted(seen)

    def has_moves(self) -> bool:
        for r in range(self.rows):
            for c in range(self.cols):
                v = self.grid[r][c]
                if v == EMPTY:
                    continue
                if c + 1 < self.cols and self.grid[r][c + 1] == v:
                    return True
                if r + 1 < self.rows and self.grid[r + 1][c] == v:
                    return True
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
        """Gravedad hacia abajo y compactación de columnas hacia la izquierda."""
        stacks = []
        for c in range(self.cols):
            stack = [(self.grid[r][c], r, c)
                     for r in range(self.rows - 1, -1, -1) if self.grid[r][c] != EMPTY]
            if stack:                       # de abajo hacia arriba
                stacks.append(stack)
        self.grid = [[EMPTY] * self.cols for _ in range(self.rows)]
        moves: list[Move] = []
        for nc, stack in enumerate(stacks):
            for i, (color, sr, sc) in enumerate(stack):
                nr = self.rows - 1 - i
                self.grid[nr][nc] = color
                if (sr, sc) != (nr, nc):
                    moves.append(((sr, sc), (nr, nc)))
        return moves

    def push_row(self) -> list[Move] | None:
        """Sube todo una fila y entra ``next_row`` por abajo. None si desborda (fin de partida)."""
        if any(v != EMPTY for v in self.grid[0]):
            return None
        moves: list[Move] = []
        for r in range(self.rows - 1):
            for c in range(self.cols):
                v = self.grid[r + 1][c]
                self.grid[r][c] = v
                if v != EMPTY:
                    moves.append(((r + 1, c), (r, c)))
        for c in range(self.cols):
            self.grid[self.rows - 1][c] = self.next_row[c]
            moves.append(((self.rows, c), (self.rows - 1, c)))
        self.next_row = self._random_row()
        return moves
