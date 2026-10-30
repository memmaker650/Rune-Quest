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


def test_tap_hits_the_staggered_cell(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    scene = GameScene(app, seed=1)
    for r, c in [(0, 0), (0, 1), (5, 3), (13, 6), (13, 7)]:
        assert scene._cell_at(scene._cell_center(r, c)) == (r, c)
    # La media celda vacía sobre una columna impar no es ninguna casilla.
    assert scene._cell_at((S.CELL * 1.5, S.BOARD_Y + 5)) is None


def test_links_join_playable_groups_and_can_be_switched_off(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    scene = GameScene(app, seed=1)
    board = scene.game.board
    board.grid = [[(r % 2) * 2 + c % 2 for c in range(board.cols)] for r in range(board.rows)]
    board.grid[0][0] = board.grid[0][1] = board.grid[1][2] = 5    # un único grupo de 3
    pairs = scene._link_pairs()
    assert sorted((a, b) for a, b, _ in pairs) == [((0, 0), (0, 1)), ((0, 1), (1, 2))]
    assert all(color == 5 for _, _, color in pairs)
    scene.draw(app.display.surface)

    menu = MenuScene(app)
    links = dict(menu.buttons)["links"]
    assert links.label == "Enlaces: sí"
    _tap(menu, links.rect.center)
    assert dict(menu.buttons)["links"].label == "Enlaces: no"
    assert GameScene(app, seed=1).links is False


def test_links_appear_half_a_second_after_the_rain_lands(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    scene = GameScene(app, seed=1)
    assert scene.links_alpha == 1.0                     # al empezar se ven ya
    board = scene.game.board
    for c in range(board.cols):                          # vacía media columna por columna
        for r in range(6):
            board.grid[r][c] = -1
    scene._apply_moves(board.rain(), rate=S.RAIN_ANIM_RATE)
    scene.rain_falling, scene.links_alpha = True, 0.0    # lo que hace el evento "rain"

    dt, t, landed, shown = 1 / 60, 0.0, None, None
    while t < 5 and shown is None:
        scene.update(dt)
        t += dt
        if landed is None and not scene._rain_still_falling():
            landed = t
        if scene.links_alpha > 0:
            shown = t
    assert landed is not None and shown is not None
    assert abs((shown - landed) - S.LINKS_DELAY_AFTER_RAIN) < 2 * dt
    for _ in range(round(S.LINKS_FADE_IN / dt) + 2):
        scene.update(dt)
    assert scene.links_alpha == 1.0
    print(f"lluvia en el suelo a {landed:.2f}s, enlaces a {shown:.2f}s")


def test_record_stays_fixed_during_the_game_and_a_star_marks_a_new_one(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    app.db.add_score("Ana", 100, 1)
    scene = GameScene(app, seed=1)
    app.change_scene(scene)
    assert not scene.is_new_record()
    board = scene.game.board
    r, c = next((r, c) for r in range(board.rows) for c in range(board.cols)
                if len(board.group_at(r, c)) >= S.MIN_GROUP)
    scene.game.score = 90
    _click(app, *scene._cell_center(r, c))
    app.run(max_frames=3)
    assert scene.game.score > 100
    assert scene.best == 100                     # el récord del marcador no se sustituye
    assert scene.is_new_record()                 # pero se marca con la estrella


def test_record_and_saved_score_are_per_mode(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    app.db.add_score("Ana", 5000, 3, "classic")
    scene = GameScene(app, seed=1, mode="fast")
    assert scene.best == 0                      # el récord de Clásico no cuenta en Rápido
    scene.game.score = 10
    assert scene.is_new_record()
    scene._save_score()
    assert app.db.best_score("fast") == 10 and app.db.best_score("classic") == 5000


def test_scores_screen_tabs_switch_mode(tmp_path):
    from RuneQuest.scenes import ScoresScene
    app = App(db_path=tmp_path / "t.db")
    for i in range(18):
        app.db.add_score(f"C{i}", 100 + i, 1, "classic")
    app.db.add_score("Rapida", 42, 1, "surprise")
    scene = ScoresScene(app)
    app.change_scene(scene)
    assert scene.mode == "classic" and len(scene.rows) == S.TOP_SCORES
    surprise_tab = scene.tabs.segments[2]
    _tap(scene, surprise_tab.center)
    assert app.scene is scene and scene.mode == "surprise"
    assert [r["player"] for r in scene.rows] == ["Rapida"]
    scene.draw(app.display.surface)
    _tap(scene, (S.LOGICAL_W // 2, 600))        # fuera de los botones: vuelve al menú
    assert isinstance(app.scene, MenuScene)


def test_hud_shows_game_mode_letter(tmp_path):
    from RuneQuest import translations
    app = App(db_path=tmp_path / "t.db")
    assert [translations.t(f"mode_short.{m}") for m in S.GAME_MODES] == ["C", "R", "S"]
    for mode in S.GAME_MODES:
        GameScene(app, seed=1, mode=mode).draw(app.display.surface)


def _finish(app, score, mode="classic"):
    scene = GameScene(app, seed=1, mode=mode)
    scene.game.score = score
    scene._save_score()
    scene.game.over, scene.over_t = True, 1.0
    scene.draw(app.display.surface)
    return scene


def test_game_over_shows_top3_and_top10(tmp_path):
    app = App(db_path=tmp_path / "t.db")
    for s in range(1000, 11000, 1000):                  # 10 puntuaciones de 1000 a 10000
        app.db.add_score("X", s, 1, "classic")
    first = _finish(app, 20000)                         # 1.º: solo "¡Nuevo récord!"
    assert first.rank == 1 and first.is_new_record() and first.rank_badge() is None
    third = _finish(app, 9500)                          # 3.º (tras 20000 y 10000): TOP 3
    assert third.rank == 3 and third.rank_badge() == "top3"
    fifth = _finish(app, 8500)                          # 5.º: TOP 10
    assert fifth.rank == 5 and fifth.rank_badge() == "top10"
    assert _finish(app, 500).rank_badge() is None       # fuera del TOP 10
    assert _finish(app, 500, mode="fast").rank == 1     # cada modo tiene su propio TOP
