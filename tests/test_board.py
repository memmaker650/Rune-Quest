import random

from orbes import settings as S
from orbes.board import EMPTY, Board


def test_group_is_orthogonal_only():
    b = Board.from_text([
        "10.",
        "01.",
        "..1",
    ])
    # Los '1' están en diagonal: no forman grupo.
    assert b.group_at(0, 0) == [(0, 0)]
    assert b.group_at(1, 1) == [(1, 1)]
    assert b.group_at(2, 0) == []              # celda vacía
    assert b.group_at(-1, 0) == []             # fuera del tablero


def test_group_follows_chains():
    b = Board.from_text([
        "110",
        "010",
        "011",
    ])
    assert b.group_at(0, 0) == [(0, 0), (0, 1), (1, 1), (2, 1), (2, 2)]
    assert b.group_at(1, 0) == [(1, 0), (2, 0)]


def test_single_orb_cannot_be_cleared():
    b = Board.from_text(["01", "10"])
    before = b.to_text()
    assert b.clear_group(0, 0) is None
    assert b.to_text() == before


def test_clear_applies_gravity_and_reports_exact_moves():
    b = Board.from_text([
        "0..",
        "1.1",
        "212",
        "212",
    ])
    result = b.clear_group(2, 0)              # los dos '2' de la columna 0
    assert result.cells == [(2, 0), (3, 0)]
    assert result.color == 2
    assert b.to_text() == [
        "...",
        "..1",
        "012",
        "112",
    ]
    assert result.moves == [((1, 0), (3, 0)), ((0, 0), (2, 0))]
    _assert_settled(b)


def _assert_settled(b):
    seen_empty_col = False
    for c in range(b.cols):
        col = [b.grid[r][c] for r in range(b.rows)]
        if all(v == EMPTY for v in col):
            seen_empty_col = True
            continue
        assert not seen_empty_col, "columna vacía a la izquierda de otra con orbes"
        first = next(i for i, v in enumerate(col) if v != EMPTY)
        assert all(v != EMPTY for v in col[first:]), "hueco bajo un orbe"


def test_settle_reports_moves_from_origin_to_destination():
    b = Board.from_text([
        "0.1",
        "0.2",
        "3.2",
    ])
    # Quitamos la columna del medio (ya vacía) y comprobamos la compactación a la izquierda.
    moves = b.settle()
    assert b.to_text() == [
        "01.",
        "02.",
        "32.",
    ]
    assert sorted(moves) == [((0, 2), (0, 1)), ((1, 2), (1, 1)), ((2, 2), (2, 1))]


def test_gravity_moves():
    b = Board.from_text([
        "0",
        ".",
        "1",
        ".",
    ])
    moves = b.settle()
    assert b.to_text() == [".", ".", "0", "1"]
    assert sorted(moves) == [((0, 0), (2, 0)), ((2, 0), (3, 0))]


def test_has_moves():
    assert Board.from_text(["01", "10"]).has_moves() is False
    assert Board.from_text(["01", "11"]).has_moves() is True
    assert Board.from_text(["..", ".."]).has_moves() is False


def test_push_row_shifts_up_and_inserts_next_row():
    b = Board.from_text([
        "...",
        "...",
        "01.",
    ], rng=random.Random(1))
    expected_new = list(b.next_row)
    moves = b.push_row()
    assert b.grid[2] == expected_new
    assert b.grid[1][:2] == [0, 1]
    assert ((2, 0), (1, 0)) in moves
    assert ((3, 0), (2, 0)) in moves          # el orbe nuevo entra desde debajo del tablero
    assert len(b.next_row) == 3                # se genera una fila nueva para la siguiente subida


def test_push_row_overflow_returns_none():
    b = Board.from_text([
        "0.",
        "1.",
    ])
    before = b.to_text()
    assert b.push_row() is None
    assert b.to_text() == before


def test_height():
    b = Board.from_text([
        "...",
        "0..",
        "01.",
    ])
    assert b.height() == 2
    assert Board.from_text(["..", ".."]).height() == 0


def test_fill_always_leaves_a_move_and_is_deterministic():
    for seed in range(30):
        b = Board(n_colors=3, rng=random.Random(seed))
        b.fill(4)
        assert b.has_moves()
        assert b.count() == 4 * S.COLS
        _assert_settled(b)
    a = Board(rng=random.Random(5)); a.fill(5)
    c = Board(rng=random.Random(5)); c.fill(5)
    assert a.grid == c.grid


def test_random_play_keeps_board_settled():
    rng = random.Random(7)
    b = Board(n_colors=4, rng=rng)
    b.fill(6)
    for _ in range(200):
        cells = [(r, c) for r in range(b.rows) for c in range(b.cols) if b.grid[r][c] != EMPTY]
        if not cells or not b.has_moves():
            break
        r, c = rng.choice(cells)
        b.clear_group(r, c)
        _assert_settled(b)
