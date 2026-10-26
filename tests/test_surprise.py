"""Modo sorpresa: aparición del orbe sorpresa y sus 5 efectos."""

import pygame
import pytest

from RuneQuest import settings as S
from RuneQuest.board import EMPTY, SURPRISE, Board
from RuneQuest.game import SURPRISE_EFFECTS, Game, clear_points, level_threshold


def _level_to(g, level):
    g.score = level_threshold(level - 1)
    g._after_move()


def test_surprise_orb_appears_at_levels_4_6_8_only_in_surprise_mode():
    g = Game(seed=1, mode="surprise")
    for level in (2, 3):
        _level_to(g, level)
        assert g.board.find(SURPRISE) is None
    _level_to(g, 4)
    assert g.board.find(SURPRISE) is not None
    assert "surprise_spawn" in [e.kind for e in g.pop_events()]

    g.board.grid[g.board.find(SURPRISE)[0]][g.board.find(SURPRISE)[1]] = 0   # lo "gastamos"
    _level_to(g, 5)
    assert g.board.find(SURPRISE) is None                   # 5: no toca
    _level_to(g, 6)
    assert g.board.find(SURPRISE) is not None               # 6: sí

    classic = Game(seed=1, mode="classic")
    _level_to(classic, 6)
    assert classic.board.find(SURPRISE) is None


def test_only_one_surprise_orb_at_a_time():
    g = Game(seed=2, mode="surprise")
    _level_to(g, 4)
    _level_to(g, 6)
    assert sum(v == SURPRISE for row in g.board.grid for v in row) == 1


def _game(lines, n_colors=3):
    g = Game(seed=3, mode="surprise")
    g.board = Board.from_text(lines, n_colors=n_colors, rng=g.rng)
    return g


def _put_surprise(g, r, c):
    g.board.grid[r][c] = SURPRISE
    g.pop_events()


BOARD = [
    "0120",
    "1201",
    "2012",
    "0120",
    "1201",
]


def test_surprise_never_groups():
    g = _game(["01", "10"])
    _put_surprise(g, 0, 0)
    assert g.board.group_at(0, 0) == [(0, 0)]
    assert not g.board.has_moves()              # no cuenta como jugada


def test_it_rains_even_with_a_surprise_orb_on_the_board():
    # Al reventar los '0' no quedan grupos: llueve aunque esté el orbe sorpresa.
    g = _game(["000", "12" + "1"])
    g.board.grid[1][2] = SURPRISE
    assert g.tap(0, 0)
    kinds = [e.kind for e in g.pop_events()]
    assert "rain" in kinds
    assert g.board.count() == 6
    assert g.board.find(SURPRISE) == (1, 2)      # sigue ahí, para pulsarlo cuando se quiera


def test_game_is_not_over_while_the_surprise_orb_remains():
    g = _game(["01", "10"])                      # lleno y sin grupos
    _put_surprise(g, 0, 0)
    g._rain()
    assert not g.over
    g2 = _game(["01", "10"])
    g2._rain()
    assert g2.over


def test_vanish_removes_only_the_surprise_orb():
    g = _game(BOARD)
    _put_surprise(g, 3, 1)
    g.open_surprise(3, 1, "vanish")
    ev = g.pop_events()[0]
    assert ev.kind == "surprise" and ev.data["cells"] == [(3, 1)]
    assert g.board.count() == 19
    # columna 1 era 1,2,0,?,2: los de encima bajan una posición
    assert [g.board.grid[r][1] for r in range(5)] == [EMPTY, 1, 2, 0, 2]
    assert g.score == 0


def test_explode_destroys_the_six_neighbours():
    g = _game(BOARD)
    _put_surprise(g, 2, 2)
    g.open_surprise(2, 2, "explode")
    ev = g.pop_events()[0]
    assert len(ev.data["cells"]) == 7                       # el sorpresa + 6 vecinos
    assert g.score >= clear_points(6)
    assert g.board.find(SURPRISE) is None


def test_mega_destroys_three_rings():
    g = Game(seed=4, mode="surprise")                       # tablero lleno de 14x8
    _put_surprise(g, 7, 4)
    before = g.board.count()
    g.open_surprise(7, 4, "mega")
    ev = [e for e in g.pop_events() if e.kind == "surprise"][0]
    assert len(ev.data["cells"]) == 1 + 6 + 12 + 18         # 3 anillos hexagonales completos
    assert all(abs(r - 7) <= S.SURPRISE_MEGA_DEPTH + 1 for r, _ in ev.data["cells"])
    assert ev.data["points"] == clear_points(36)
    assert before - 37 <= g.board.count() or g.rains        # o ha llovido después


def test_neighbour_takes_a_colour_from_around():
    g = _game(BOARD)
    _put_surprise(g, 2, 2)
    g.open_surprise(2, 2, "neighbour")
    around = {g.board.get(r, c) for r, c in [(1, 2), (3, 2), (1, 1), (2, 1), (1, 3), (2, 3)]}
    assert g.board.get(2, 2) in around
    assert g.board.count() == 20                            # no se destruye nada


def test_next_takes_the_colour_of_the_next_orb_to_fall():
    g = _game(BOARD)
    g.board.next_color = 2
    _put_surprise(g, 0, 0)
    g.open_surprise(0, 0, "next")
    assert g.board.get(0, 0) == 2


def test_random_effect_is_one_of_the_five_and_tap_opens_it():
    seen = set()
    for seed in range(40):
        g = Game(seed=seed, mode="surprise")
        _put_surprise(g, 5, 5)
        assert g.tap(5, 5)
        seen.add([e for e in g.pop_events() if e.kind == "surprise"][0].data["effect"])
    assert seen == set(SURPRISE_EFFECTS)


def test_saved_game_keeps_the_surprise_orb():
    g = Game(seed=1, mode="surprise")
    _put_surprise(g, 4, 3)
    h = Game.from_state(g.to_state())
    assert h.board.get(4, 3) == SURPRISE and h.mode == "surprise"


def test_unknown_effect_is_rejected():
    g = _game(BOARD)
    _put_surprise(g, 0, 0)
    with pytest.raises(ValueError):
        g.open_surprise(0, 0, "teleport")


def test_surprise_orb_sprite_is_white():
    pygame.init()
    from RuneQuest.sprites import orb_sprite
    sprite = orb_sprite(SURPRISE, 45)
    r, g, b, a = sprite.get_at((14, 30))
    assert min(r, g, b) > 200 and a == 255
