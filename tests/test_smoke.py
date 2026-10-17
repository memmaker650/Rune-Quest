"""Pruebas de arranque con pygame real y driver de vídeo 'dummy' (sin ventana)."""

import pygame

from RuneQuest import settings as S
from RuneQuest.app import App
from RuneQuest.scenes import GameScene, MenuScene, NewGameScene, ScoresScene


def _click(app, x, y):
    # La ventana tiene el tamaño lógico (escala 1, sin barras): coordenadas de ventana == lógicas.
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(x, y), button=1))


def test_menu_and_scores_run_headless(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    assert isinstance(app.scene, MenuScene)
    app.run(max_frames=3)

    app = App(db_path=tmp_path / "t.db")
    app.change_scene(ScoresScene(app))
    app.run(max_frames=3)


def test_play_button_opens_new_game_screen_and_starts_a_game(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    _click(app, 100, 350)                       # botón "Jugar"
    app.run(max_frames=3)
    assert isinstance(app.scene, NewGameScene)

    app = App(db_path=tmp_path / "t.db")
    scene = NewGameScene(app)
    app.change_scene(scene)
    _click(app, *scene.start_button.rect.center)       # "Empezar partida"
    app.run(max_frames=3)
    assert isinstance(app.scene, GameScene)
    assert app.scene.game.mode == "classic"


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
    board = scene.game.board                    # baldosas 2x2 de 4 colores: lleno y sin jugadas
    board.grid = [[(r % 2) * 2 + c % 2 for c in range(board.cols)] for r in range(board.rows)]
    scene.game._rain()                          # la lluvia no cabe y no hay jugadas: fin
    assert scene.game.over
    app.run(max_frames=3)
    db = Database(tmp_path / "t.db")
    assert db.top_scores(1)[0]["score"] == 123


def _first_group_center(game):
    board = game.board
    r, c = next((r, c) for r in range(board.rows) for c in range(board.cols)
                if len(board.group_at(r, c)) >= S.MIN_GROUP)
    return S.BOARD_X + c * S.CELL + S.CELL // 2, S.BOARD_Y + r * S.CELL + S.CELL // 2


def test_continue_restores_saved_game(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    assert [name for name, _ in app.scene.buttons][0] == "play"   # sin partida: no hay Continuar
    scene = GameScene(app, seed=5)
    app.change_scene(scene)
    _click(app, *_first_group_center(scene.game))
    app.run(max_frames=3)
    saved_grid = [row[:] for row in scene.game.board.grid]
    saved_score = scene.game.score
    assert saved_score > 0

    app = App(db_path=tmp_path / "t.db")                  # se reabre la app
    assert [name for name, _ in app.scene.buttons][0] == "continue"
    _click(app, 100, 340)                                 # botón "Continuar"
    app.run(max_frames=2)
    assert isinstance(app.scene, GameScene)
    assert app.scene.game.board.grid == saved_grid
    assert app.scene.game.score == saved_score


def test_game_over_removes_saved_game(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    scene = GameScene(app, seed=1)
    app.change_scene(scene)
    app.db.save_game(scene.game.to_state())
    board = scene.game.board
    board.grid = [[(r % 2) * 2 + c % 2 for c in range(board.cols)] for r in range(board.rows)]
    scene.game._rain()
    app.run(max_frames=2)
    from RuneQuest.db import Database
    assert not Database(tmp_path / "t.db").has_saved_game()


def test_menu_button_darkens_while_pressed_and_acts_on_release(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    menu = app.scene
    down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(100, 340), button=1)
    menu.handle_event(down)                                   # pulsa "Jugar"
    assert menu.buttons[0][1].pressed and app.scene is menu   # oscuro, aún no actúa
    menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(100, 600), button=1))
    assert not menu.buttons[0][1].pressed and app.scene is menu   # soltar fuera cancela
    menu.handle_event(down)
    menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(110, 345), button=1))
    assert isinstance(app.scene, NewGameScene)


def _tap(scene, pos):
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))


def test_menu_has_close_button_instead_of_quit(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    menu = app.scene
    assert "quit" not in [name for name, _ in menu.buttons]
    close, flag = menu.close_button.rect, menu.lang_button.rect
    assert close.width == close.height                       # cuadrado
    assert close.left < S.LOGICAL_W // 2 and close.centery == flag.centery   # abajo izq.
    _tap(menu, close.center)
    assert app.running is False


def test_game_mode_cycles_persists_and_reaches_the_game(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    scene = NewGameScene(app)
    app.change_scene(scene)
    assert scene.mode == "classic"
    _tap(scene, scene.mode_button.rect.center)
    assert scene.mode == "fast" and scene.mode_button.label == "Rápido"
    _tap(scene, scene.mode_button.rect.center)
    _tap(scene, scene.mode_button.rect.center)
    assert scene.mode == "classic"                           # Clásico -> Rápido -> Sorpresa -> ...
    _tap(scene, scene.mode_button.rect.center)
    assert NewGameScene(app).mode == "fast"                  # se recuerda
    _tap(scene, scene.start_button.rect.center)
    assert app.scene.game.mode == "fast"


def test_back_button_returns_to_menu(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    scene = NewGameScene(app)
    app.change_scene(scene)
    _tap(scene, scene.back_button.rect.center)
    assert isinstance(app.scene, MenuScene)
