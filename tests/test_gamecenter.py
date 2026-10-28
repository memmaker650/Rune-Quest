"""Game Center con un doble de pruebas: no hace falta GameKit ni una app firmada."""

import pygame

from RuneQuest import gamecenter
from RuneQuest.app import App
from RuneQuest.db import Database
from RuneQuest.scenes import GameScene, ScoresScene


class FakeGameCenter(gamecenter.GameCenter):
    available = True

    def __init__(self):
        super().__init__()
        self.submitted = []
        self.opened = 0

    def login(self, name):
        self.authenticated, self.player_name = True, name
        self.on_authenticated(self)

    def submit_score(self, score):
        self.submitted.append(score)

    def show_leaderboards(self):
        self.opened += 1


def _app(tmp_path, monkeypatch):
    fake = FakeGameCenter()
    monkeypatch.setattr(gamecenter, "create", lambda: fake)
    return App(db_path=tmp_path / "t.db"), fake


def test_disabled_or_unsupported_platform_uses_null_center(monkeypatch):
    gc = gamecenter.create()                     # conftest pone RUNEQUEST_GAMECENTER=0
    assert type(gc) is gamecenter.GameCenter and not gc.available
    monkeypatch.setenv("RUNEQUEST_GAMECENTER", "1")
    monkeypatch.setattr(gamecenter.sys, "platform", "win32")
    assert type(gamecenter.create()) is gamecenter.GameCenter


def test_login_sets_player_name_and_uploads_local_best(tmp_path, monkeypatch):
    app, gc = _app(tmp_path, monkeypatch)
    app.db.add_score("Anon", 800, 2)
    gc.login("Jorge")
    assert app.db.get_setting("player_name") == "Jorge"
    assert gc.submitted == [800]


def test_finished_game_is_sent_to_game_center(tmp_path, monkeypatch):
    app, gc = _app(tmp_path, monkeypatch)
    gc.login("Jorge")
    scene = GameScene(app, seed=1)
    app.change_scene(scene)
    scene.game.score = 4321
    board = scene.game.board
    board.grid = [[(r % 2) * 2 + c % 2 for c in range(board.cols)] for r in range(board.rows)]
    scene.game._rain()                           # fin de partida
    app.run(max_frames=2)
    assert 4321 in gc.submitted
    assert Database(tmp_path / "t.db").top_scores(1)[0]["player"] == "Jorge"


def test_scores_button_opens_game_center_only_when_logged_in(tmp_path, monkeypatch):
    app, gc = _app(tmp_path, monkeypatch)
    scene = ScoresScene(app)
    app.change_scene(scene)
    x, y = scene.gc_button.rect.center
    down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1)
    up = pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(x, y), button=1)
    scene.handle_event(down)                     # sin sesión: no hay botón, vuelve al menú
    assert app.scene is not scene and gc.opened == 0

    gc.login("Jorge")
    scene = ScoresScene(app)
    app.change_scene(scene)
    scene.handle_event(down)
    assert scene.gc_button.pressed
    scene.handle_event(up)
    assert gc.opened == 1 and app.scene is scene
