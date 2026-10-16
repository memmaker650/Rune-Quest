import random

from RuneQuest import settings as S
from RuneQuest.board import Board
from RuneQuest.game import Game, clear_points, level_params, level_threshold


def game_with(lines, n_colors=3, level=1, seed=1):
    """Partida con un tablero fijo (para probar reglas concretas)."""
    g = Game(seed=seed, level=level)
    g.board = Board.from_text(lines, n_colors=n_colors, rng=g.rng)
    g.pop_events()
    return g


def test_points_grow_with_chain_length():
    assert clear_points(3) == 60
    assert clear_points(5) == 200
    assert clear_points(10) == 900


def test_new_game_starts_with_a_full_board():
    g = Game(seed=1)
    assert g.board.count() == S.ROWS * S.COLS
    assert g.board.has_moves()


def test_tap_on_a_pair_does_nothing():
    g = game_with(["002", "121"])
    assert g.tap(0, 0) is False
    assert g.score == 0 and g.taps == 0
    assert g.pop_events() == []


def test_tap_scores_and_emits_clear_event():
    g = game_with([
        "..1",
        "001",
        "011",
    ])
    # grupo de '0': (1,0), (1,1), (2,0) -> 3 orbes; quedan unos conectados, así que no llueve
    assert g.tap(1, 0) is True
    assert g.score == clear_points(3)
    assert g.best_chain == 3 and g.taps == 1
    events = g.pop_events()
    assert [e.kind for e in events] == ["clear"]
    assert events[0].data["points"] == clear_points(3)
    assert len(events[0].data["cells"]) == 3


def test_rain_refills_the_board_when_no_moves_are_left():
    # Al reventar los '0' quedan 1, 2 y 3 sueltos: llueve hasta llenar el tablero.
    g = game_with(["000", "123"], n_colors=1)   # con un solo color la lluvia deja jugadas
    assert g.tap(0, 0)
    kinds = [e.kind for e in g.pop_events()]
    assert kinds == ["clear", "rain"]
    assert g.board.count() == 6
    assert g.rains == 1 and not g.over


def test_game_over_when_rain_leaves_no_moves():
    g = game_with(["01", "10"])                 # lleno y sin grupos de 3
    g._rain()
    assert g.over
    assert [e.kind for e in g.pop_events()] == ["rain", "over"]
    score = g.score
    assert g.tap(0, 0) is False
    assert g.score == score


def test_level_up_by_points_adds_colors():
    g = game_with(["..1", "001", "011"])
    g.score = level_threshold(1) - clear_points(3)
    assert g.tap(1, 0)
    assert g.level == 2
    assert "level" in [e.kind for e in g.pop_events()]
    assert g.board.n_colors == level_params(2)["colors"]


def test_level_params_get_harder_and_stay_in_bounds():
    prev = level_params(1)
    assert prev["colors"] == S.START_COLORS
    for lvl in range(2, 40):
        p = level_params(lvl)
        assert prev["colors"] <= p["colors"] <= S.MAX_COLORS
        assert level_threshold(lvl) > level_threshold(lvl - 1)
        prev = p


def test_random_playthrough_always_has_moves_or_ends():
    for seed in range(20):
        g = Game(seed=seed)
        rng = random.Random(seed)
        for _ in range(500):
            if g.over:
                break
            cells = [(r, c) for r in range(g.board.rows) for c in range(g.board.cols)
                     if len(g.board.group_at(r, c)) >= S.MIN_GROUP]
            assert cells, "sin jugadas y sin terminar la partida"
            assert g.board.count() > 0
            g.tap(*rng.choice(cells))
            g.pop_events()
        assert g.score >= 0 and g.level >= 1


def test_state_round_trip_restores_the_exact_board():
    g = Game(seed=4)
    cells = [(r, c) for r in range(g.board.rows) for c in range(g.board.cols)
             if len(g.board.group_at(r, c)) >= S.MIN_GROUP]
    g.tap(*cells[0])
    state = g.to_state()
    assert {"score", "level", "balls"} <= state.keys()
    h = Game.from_state(state)
    assert h.board.grid == g.board.grid
    assert (h.score, h.level, h.taps, h.rains, h.best_chain) == \
        (g.score, g.level, g.taps, g.rains, g.best_chain)
    assert h.board.n_colors == level_params(g.level)["colors"]


def test_invalid_state_is_rejected():
    import pytest

    state = Game(seed=1).to_state()
    with pytest.raises(ValueError):
        Game.from_state({**state, "rows": 3})
    with pytest.raises(ValueError):
        Game.from_state({**state, "balls": [[99, 0, 1]]})
