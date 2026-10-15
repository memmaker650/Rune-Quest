import random

from orbes import settings as S
from orbes.board import Board
from orbes.game import Game, clear_points, level_params


def game_with(lines, n_colors=3, level=1, interval=5, seed=1):
    """Partida con un tablero fijo (para probar reglas concretas)."""
    g = Game(seed=seed, level=level)
    g.board = Board.from_text(lines, n_colors=n_colors, rng=g.rng)
    g.interval = interval
    g.taps_since_push = 0
    g.pop_events()
    return g


def test_points_grow_with_chain_length():
    assert clear_points(2) == 20
    assert clear_points(5) == 200
    assert clear_points(10) == 900
    assert clear_points(3) > 2 * clear_points(2)


def test_tap_on_single_orb_does_nothing():
    g = game_with(["01", "10"])
    assert g.tap(0, 0) is False
    assert g.score == 0 and g.taps == 0 and g.taps_since_push == 0
    assert g.pop_events() == []


def test_tap_scores_and_emits_clear_event():
    g = game_with([
        "..1",
        "001",
        "011",
    ])
    # grupo de '0': (1,0), (1,1), (2,0) -> 3 orbes
    assert g.tap(1, 0) is True
    assert g.score == clear_points(3)
    assert g.best_chain == 3 and g.taps == 1
    events = g.pop_events()
    assert [e.kind for e in events] == ["clear"]
    assert events[0].data["points"] == clear_points(3)
    assert len(events[0].data["cells"]) == 3


def test_row_is_pushed_every_interval_taps():
    g = game_with(["000", "111", "222"], interval=2)
    assert g.tap(2, 0) and g.pushes_in == 1       # queda "000" y "111"
    assert g.tap(2, 0)                            # queda "000" -> toca subir fila
    kinds = [e.kind for e in g.pop_events()]
    assert kinds == ["clear", "clear", "push"]
    assert g.taps_since_push == 0
    assert g.board.count() == 6                    # "000" + la fila nueva de 3 columnas


def test_clearing_the_board_levels_up_with_bonus():
    g = game_with(["00", "00"])
    assert g.tap(0, 0)
    kinds = [e.kind for e in g.pop_events()]
    assert kinds == ["clear", "level"]
    assert g.level == 2
    assert g.score == clear_points(4) + S.LEVEL_BONUS * 1
    assert g.board.count() > 0 and g.board.has_moves()
    assert not g.over


def test_stuck_board_pushes_rows_until_moves_exist():
    # Al reventar los '1' solo quedan 0, 2 y 3 (sin parejas): sube fila sin esperar al intervalo.
    g = game_with([
        "...",
        "...",
        "0..",
        "2..",
        "311",
    ], interval=99)
    assert g.tap(4, 1)
    kinds = [e.kind for e in g.pop_events()]
    assert kinds[0] == "clear"
    assert "push" in kinds
    assert g.over or g.board.has_moves()


def test_game_over_when_screen_fills_and_no_more_taps_count():
    g = game_with(["0.", "1."], interval=99)   # la columna 0 ya toca el techo
    g._push()
    assert g.over
    kinds = [e.kind for e in g.pop_events()]
    assert kinds == ["over"]
    score = g.score
    assert g.tap(0, 0) is False
    assert g.score == score


def test_level_params_get_harder_and_stay_in_bounds():
    prev = level_params(1)
    assert prev["colors"] == S.START_COLORS
    assert prev["interval"] == S.START_PUSH_INTERVAL
    for lvl in range(2, 40):
        p = level_params(lvl)
        assert p["colors"] >= prev["colors"] and p["rows"] >= prev["rows"]
        assert p["interval"] <= prev["interval"]
        assert S.START_COLORS <= p["colors"] <= S.MAX_COLORS
        assert p["rows"] <= S.MAX_START_ROWS
        assert p["interval"] >= S.MIN_PUSH_INTERVAL
        prev = p


def test_random_playthrough_always_terminates_cleanly():
    for seed in range(20):
        g = Game(seed=seed)
        rng = random.Random(seed)
        for _ in range(2000):
            if g.over:
                break
            cells = [(r, c) for r in range(g.board.rows) for c in range(g.board.cols)
                     if g.board.group_at(r, c) and len(g.board.group_at(r, c)) >= 2]
            assert cells or g.over, "sin jugadas y sin terminar la partida"
            g.tap(*rng.choice(cells))
            g.pop_events()
        assert g.score >= 0 and g.level >= 1
