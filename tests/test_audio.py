import array

import pygame

from RuneQuest import settings as S
from RuneQuest.app import App
from RuneQuest.audio import Audio, synth_pop
from RuneQuest.scenes import GameScene


def test_pop_is_short_soft_and_starts_silent():
    data = array.array("h", synth_pop(44100, -16, 1))
    assert 0.1 < len(data) / 44100 < 0.25            # menos de un cuarto de segundo
    assert abs(data[0]) < 200                          # entrada suave, sin chasquido
    assert max(abs(v) for v in data) <= 32767
    assert abs(data[-1]) < 0.05 * max(abs(v) for v in data)   # se apaga al final
    stereo = synth_pop(44100, -16, 2)
    assert len(stereo) == 2 * len(synth_pop(44100, -16, 1))


class SpySound:
    def __init__(self):
        self.plays = 0

    def play(self):
        self.plays += 1


def test_play_pop_respects_fx_switch():
    audio = Audio()
    audio._pop = SpySound()
    audio.play_pop()
    audio.set_fx(False)
    audio.play_pop()
    assert audio._pop.plays == 1


def _press(scene, pos):
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))


def test_sound_icons_toggle_and_persist(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    scene = GameScene(app, seed=1)
    assert scene.fx_button.on and scene.music_button.on
    assert scene.fx_button.rect.right < scene.music_button.rect.left      # FX a la izquierda
    _press(scene, scene.fx_button.rect.center)
    _press(scene, scene.music_button.rect.center)
    assert not app.audio.fx_enabled and not app.audio.music_enabled
    assert app.db.get_setting("sfx") == "0" and app.db.get_setting("music") == "0"
    scene = GameScene(app, seed=1)
    assert not scene.fx_button.on and not scene.music_button.on
    assert scene.game.taps == 0                       # tocar un icono no es una jugada


def test_pop_sounds_on_a_valid_combination(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    spy = SpySound()
    app.audio._pop = spy
    scene = GameScene(app, seed=1)
    board = scene.game.board
    r, c = next((r, c) for r in range(board.rows) for c in range(board.cols)
                if len(board.group_at(r, c)) >= S.MIN_GROUP)
    _press(scene, scene._cell_center(r, c))
    assert spy.plays == 1
