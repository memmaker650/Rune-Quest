import random

from RuneQuest import settings as S
from RuneQuest.board import EMPTY, Board


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


def test_groups_below_minimum_cannot_be_cleared():
    assert S.MIN_GROUP == 3
    b = Board.from_text(["01", "10"])
    before = b.to_text()
    assert b.clear_group(0, 0) is None         # orbe suelto
    b = Board.from_text(["00", "12"])
    before = b.to_text()
    assert b.clear_group(0, 0) is None         # pareja: no llega a 3
    assert b.to_text() == before


def test_clear_applies_gravity_and_reports_exact_moves():
    b = Board.from_text([
        "0..",
        "2.1",
        "212",
        "212",
    ])
    result = b.clear_group(1, 0)              # los tres '2' de la columna 0
    assert result.cells == [(1, 0), (2, 0), (3, 0)]
    assert result.color == 2
    assert b.to_text() == [
        "...",
        "..1",
        ".12",
        "012",
    ]
    assert result.moves == [((0, 0), (3, 0))]
    _assert_settled(b)


def _assert_settled(b):
    for c in range(b.cols):
        col = [b.grid[r][c] for r in range(b.rows)]
        if all(v == EMPTY for v in col):
            continue
        first = next(i for i, v in enumerate(col) if v != EMPTY)
        assert all(v != EMPTY for v in col[first:]), "hueco bajo un orbe"


def test_empty_column_is_not_compacted():
    b = Board.from_text([
        "0.1",
        "0.2",
        "3.2",
    ])
    # La columna del medio está vacía: los orbes de la derecha no se desplazan a la izquierda.
    before = b.to_text()
    assert b.settle() == []
    assert b.to_text() == before


def test_clearing_a_whole_column_leaves_it_empty():
    b = Board.from_text([
        "010",
        "212",
        "212",
    ])
    result = b.clear_group(0, 1)               # toda la columna de '1'
    assert result.moves == []
    assert b.to_text() == ["0.0", "2.2", "2.2"]


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
    assert Board.from_text(["00", "12"]).has_moves() is False    # solo una pareja
    assert Board.from_text(["01", "11"]).has_moves() is True     # grupo de 3 en "L"
    assert Board.from_text(["..", ".."]).has_moves() is False


def test_rain_fills_every_gap_from_above():
    b = Board.from_text([
        "...",
        "0..",
        "01.",
    ], rng=random.Random(1))
    moves = b.rain()
    assert b.count() == 9
    assert b.grid[1][0] == 0 and b.grid[2][:2] == [0, 1]    # los orbes existentes no se mueven
    assert sorted(moves) == sorted([
        ((-1, 0), (0, 0)),
        ((-2, 1), (0, 1)), ((-1, 1), (1, 1)),
        ((-3, 2), (0, 2)), ((-2, 2), (1, 2)), ((-1, 2), (2, 2)),
    ])
    assert Board.from_text(["01", "10"]).rain() == []      # tablero lleno: no llueve nada


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
        b.fill()
        assert b.has_moves()
        assert b.count() == S.ROWS * S.COLS        # empieza lleno
        _assert_settled(b)
    a = Board(rng=random.Random(5)); a.fill()
    c = Board(rng=random.Random(5)); c.fill()
    assert a.grid == c.grid


def test_random_play_keeps_board_settled():
    rng = random.Random(7)
    b = Board(n_colors=4, rng=rng)
    b.fill()
    for _ in range(200):
        cells = [(r, c) for r in range(b.rows) for c in range(b.cols) if b.grid[r][c] != EMPTY]
        if not cells or not b.has_moves():
            break
        r, c = rng.choice(cells)
        b.clear_group(r, c)
        _assert_settled(b)
