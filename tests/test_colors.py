import pygame

from RuneQuest import settings as S
from RuneQuest.game import level_params
from RuneQuest.sprites import orb_sprite
from RuneQuest.ui import contrast, readable


def test_new_colours_unlock_at_the_requested_levels():
    expected = {1: 3, 4: 3, 5: 4, 7: 4, 8: 5, 11: 5, 12: 6, 16: 6, 17: 7,
                22: 7, 23: 8, 29: 8, 30: 9, 37: 9, 38: 10, 46: 10, 47: 11, 56: 11, 57: 12,
                67: 12, 68: 13, 99: 13}
    for level, colors in expected.items():
        assert level_params(level)["colors"] == colors, level
    assert S.MAX_COLORS == len(S.PALETTE) == 13


def test_palette_colours_are_all_different():
    assert len(set(S.PALETTE)) == len(S.PALETTE)


def test_black_orb_has_a_light_rim_to_stand_out():
    pygame.init()
    black = S.PALETTE.index((31, 24, 24))
    sprite = orb_sprite(black, 45)
    rim = sprite.get_at((45 // 2, 3))                 # anillo del borde, arriba
    assert contrast(rim[:3], S.PANEL) > 3


def test_colour_names_stay_readable_on_the_banner():
    for color in S.PALETTE:
        assert contrast(readable(color), S.OVER_PANEL) >= 4.5


from RuneQuest.board import Board, SURPRISE
from RuneQuest.game import Game


def _no_moves_board(g):
    """Tablero lleno y sin grupos, así el siguiente movimiento provoca una lluvia."""
    b = g.board
    b.grid = [[(r % 2) * 2 + c % 2 for c in range(b.cols)] for r in range(b.rows)]


def test_classic_and_surprise_unlock_colours_by_level_not_by_rain():
    for mode in ("classic", "surprise"):
        g = Game(seed=1, mode=mode)
        for _ in range(4):
            _no_moves_board(g)
            g.board.grid[0][0] = -1                # un hueco para que llueva algo
            g.board.settle()
            g._rain()
        assert g.board.n_colors == S.START_COLORS


def test_fast_mode_adds_a_new_colour_with_every_rain():
    g = Game(seed=2, mode="fast")
    assert g.board.n_colors == S.START_COLORS
    for i in range(1, 6):
        b = g.board
        for r in range(6):                        # vacía las 6 filas de arriba
            for c in range(b.cols):
                b.grid[r][c] = -1
        g.pop_events()
        g._rain()
        new = S.START_COLORS + i - 1
        assert g.board.n_colors == S.START_COLORS + i
        rain = [e for e in g.pop_events() if e.kind == "rain"][0]
        assert rain.data["new_color"] == new
        rained = [dst for _, dst in rain.data["moves"]]
        assert sum(g.board.get(*cell) == new for cell in rained) >= S.FAST_MIN_NEW_COLOR_ORBS


def test_fast_mode_levels_do_not_change_colours_and_restore_keeps_them():
    g = Game(seed=3, mode="fast")
    g.rains = 4
    g.board.n_colors = g.color_count()
    g.score = 10 ** 7                             # muchos niveles de golpe
    g._after_move()
    assert g.level > 20 and g.board.n_colors == S.START_COLORS + 4
    h = Game.from_state(g.to_state())
    assert h.board.n_colors == S.START_COLORS + 4


def test_surprise_orb_has_a_gold_ring_unlike_a_white_orb():
    pygame.init()
    white = orb_sprite(10, 45)
    surprise = orb_sprite(SURPRISE, 45)
    assert surprise.get_at((45 // 2, 3))[:3] == S.GOLD
    assert white.get_at((45 // 2, 3))[:3] != S.GOLD
