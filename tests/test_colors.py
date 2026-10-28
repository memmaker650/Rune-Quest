import pygame

from RuneQuest import settings as S
from RuneQuest.game import level_params
from RuneQuest.sprites import orb_sprite
from RuneQuest.ui import contrast, readable


def test_new_colours_unlock_at_the_requested_levels():
    expected = {1: 3, 4: 3, 5: 4, 7: 4, 8: 5, 11: 5, 12: 6, 16: 6, 17: 7,
                22: 7, 23: 8, 29: 8, 30: 9, 37: 9, 38: 10, 99: 10}
    for level, colors in expected.items():
        assert level_params(level)["colors"] == colors, level
    assert S.MAX_COLORS == len(S.PALETTE) == 10


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
