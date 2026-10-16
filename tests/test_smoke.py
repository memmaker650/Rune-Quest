"""Pruebas de arranque con pygame real y driver de vídeo 'dummy' (sin ventana)."""

import pygame

from RuneQuest import settings as S
from RuneQuest.app import App
from RuneQuest.scenes import GameScene, MenuScene, ScoresScene


def _click(app, x, y):
    # La ventana tiene el tamaño lógico (escala 1, sin barras): coordenadas de ventana == lógicas.
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1))


def test_menu_and_scores_run_headless(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    assert isinstance(app.scene, MenuScene)
    app.run(max_frames=3)

    app = App(db_path=tmp_path / "t.db")
    app.change_scene(ScoresScene(app))
    app.run(max_frames=3)


def test_play_button_starts_a_game(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    _click(app, 100, 350)                       # botón "Jugar"
    app.run(max_frames=3)
    assert isinstance(app.scene, GameScene)


def test_clicking_a_group_scores_points(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    app.change_scene(GameScene(app, seed=3))
    board = app.scene.game.board
    r, c = next((r, c) for r in range(board.rows) for c in range(board.cols)
                if len(board.group_at(r, c)) >= S.MIN_GROUP)
    _click(app, S.BOARD_X + c * S.CELL + S.CELL // 2, S.BOARD_Y + r * S.CELL + S.CELL // 2)
    app.run(max_frames=30)
    assert app.scene.game.score > 0
    assert app.scene.game.taps == 1


def test_finished_game_saves_score_in_db(tmp_path):
    from RuneQuest.db import Database

    app = App(db_path=tmp_path / "t.db")
    scene = GameScene(app, seed=1)
    app.change_scene(scene)
    scene.game.score = 123
    board = scene.game.board                    # tablero en damero: lleno y sin jugadas
    board.grid = [[(r + c) % 2 for c in range(board.cols)] for r in range(board.rows)]
    scene.game._rain()                          # la lluvia no cabe y no hay jugadas: fin
    assert scene.game.over
    app.run(max_frames=3)
    db = Database(tmp_path / "t.db")
    assert db.top_scores(1)[0]["score"] == 123
