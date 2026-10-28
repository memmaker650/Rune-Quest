import pygame

from RuneQuest import settings as S
from RuneQuest.app import App
from RuneQuest.runes import RUNES, rune_for_color
from RuneQuest.scenes import GameScene, assist_mode
from RuneQuest.sprites import orb_sprite


def test_distinct_runes_inside_the_box_one_per_colour():
    assert len(RUNES) >= S.MAX_COLORS
    assert len({r.name for r in RUNES}) == len(RUNES) == len({r.char for r in RUNES})
    for rune in RUNES:
        assert rune.strokes
        for stroke in rune.strokes:
            assert len(stroke) >= 2
            assert all(-1 <= x <= 1 and -1 <= y <= 1 for x, y in stroke)


def test_every_colour_gets_its_own_rune():
    used = [rune_for_color(i).name for i in range(S.MAX_COLORS)]
    assert len(set(used)) == S.MAX_COLORS


def test_assist_modes_draw_different_orbs():
    pygame.init()
    for color in range(S.MAX_COLORS):
        none, geo, runes = (pygame.image.tobytes(orb_sprite(color, 45, m), "RGBA")
                            for m in S.ASSIST_MODES)
        assert len({none, geo, runes}) == 3


def _tap(scene, pos):
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))


def _assist_button(menu):
    return dict(menu.buttons)["assist"]


def test_assist_button_cycles_none_geo_runes_and_reaches_the_game(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    menu = app.scene
    assert _assist_button(menu).label == "No" and _assist_button(menu).subtitle == "Ayuda"
    _tap(menu, _assist_button(menu).rect.center)
    assert assist_mode(app.db) == "geo" and _assist_button(menu).label == "Geo"
    _tap(menu, _assist_button(menu).rect.center)
    assert assist_mode(app.db) == "runes" and _assist_button(menu).label == "Runas"
    assert GameScene(app, seed=1).assist == "runes"
    _tap(menu, _assist_button(menu).rect.center)
    assert assist_mode(app.db) == "none"


def test_old_colour_assist_setting_becomes_geo(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    app.db.set_setting("color_assist", "1")
    assert assist_mode(app.db) == "geo"
    app.db.set_setting("assist", "runes")          # el ajuste nuevo manda
    assert assist_mode(app.db) == "runes"
