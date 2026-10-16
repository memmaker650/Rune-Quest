"""Escenas: menú, partida y puntuaciones."""

import logging
import math
import random
import sqlite3
import sys

import pygame

from . import translations
from . import settings as S
from .controls import is_confirm, is_real_mouse_motion, tap_position
from .game import Game, clear_points
from .sprites import orb_sprite
from .translations import t
from .ui import Button, FlagButton, draw_text

log = logging.getLogger(__name__)

IS_IOS = sys.platform == "ios"
BOARD_RECT = pygame.Rect(S.BOARD_X, S.BOARD_Y, S.BOARD_W, S.BOARD_H)


class Scene:
    def __init__(self, app):
        self.app = app

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass


# --------------------------------------------------------------------------- menú
class MenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.title_font = pygame.font.Font(None, 96)
        self.font = pygame.font.Font(None, 36)
        self.small = pygame.font.Font(None, 22)
        self.t = 0.0
        self._build_buttons()
        self.best = app.db.best_score()

    def _build_buttons(self):
        """(Re)crea los botones con los textos del idioma activo."""
        entries = []
        if self.app.db.has_saved_game():
            entries.append(("continue", t("menu.continue")))
        entries += [
            ("play", t("menu.play")),
            ("scores", t("menu.scores")),
            ("assist", self._assist_label()),
        ]
        if not IS_IOS:  # en iOS no se "sale" de una app
            entries.append(("quit", t("menu.quit")))
        self.buttons = [(name, Button((60, 316 + i * 62, 240, 52), label))
                        for i, (name, label) in enumerate(entries)]
        self.lang_button = FlagButton((S.LOGICAL_W - 66, S.LOGICAL_H - 52, 54, 38),
                                      translations.current().flag)

    def _assist_label(self) -> str:
        on = self.app.db.get_setting("color_assist", "0") == "1"
        return t("menu.assist", state=t("common.yes") if on else t("common.no"))

    def _next_language(self):
        lang = translations.next_language()
        translations.set_language(lang.code)
        try:
            self.app.db.set_setting("language", lang.code)
        except sqlite3.Error:
            log.error("No se pudo guardar el idioma %s; solo se aplica a esta sesión", lang.code)
        self._build_buttons()

    def _continue_game(self):
        state = self.app.db.load_game()
        try:
            game = Game.from_state(state) if state else None
        except (KeyError, TypeError, ValueError):
            log.exception("La partida guardada no es válida; se descarta")
            game = None
        if game is None:
            self.app.db.delete_game()
            self._build_buttons()          # ya no hay nada que continuar
            return
        self.app.change_scene(GameScene(self.app, game=game))

    def _activate(self, name):
        if name == "continue":
            self._continue_game()
        elif name == "play":
            self.app.change_scene(GameScene(self.app))
        elif name == "scores":
            self.app.change_scene(ScoresScene(self.app))
        elif name == "assist":
            on = self.app.db.get_setting("color_assist", "0") == "1"
            try:
                self.app.db.set_setting("color_assist", "0" if on else "1")
            except sqlite3.Error:
                log.error("No se pudo cambiar la ayuda de color; se mantiene como estaba")
            self._build_buttons()
        elif name == "quit":
            self.app.quit()
        else:
            log.warning("Botón de menú desconocido: %r", name)

    def handle_event(self, event):
        pos = tap_position(event, self.app.display)
        if pos is not None:
            if self.lang_button.hit(pos):
                self._next_language()
                return
            for name, button in self.buttons:
                if button.hit(pos):
                    self._activate(name)
                    return
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._activate(self.buttons[0][0])   # "Continuar" si existe; si no, "Jugar"
            elif event.key == pygame.K_ESCAPE and not IS_IOS:
                self.app.quit()

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        surf.fill(S.BG)
        assist = self.app.db.get_setting("color_assist", "0") == "1"
        for i in range(S.MAX_COLORS):  # orbes decorativos flotando
            x = 30 + i * 60 + math.sin(self.t * 1.3 + i) * 10
            y = 210 + math.sin(self.t * 1.7 + i * 1.1) * 14
            sprite = orb_sprite(i, 52, assist)
            surf.blit(sprite, sprite.get_rect(center=(x, y)))
        draw_text(surf, self.title_font, "ORBES", S.ACCENT, center=(S.LOGICAL_W // 2, 120))
        draw_text(surf, self.small, t("menu.subtitle"), S.WHITE,
                  center=(S.LOGICAL_W // 2, 290))
        for _, button in self.buttons:
            button.draw(surf, self.font)
        self.lang_button.draw(surf)
        if self.best:
            draw_text(surf, self.small, t("menu.record", score=self.best), S.WHITE,
                      center=(S.LOGICAL_W // 2, S.LOGICAL_H - 40))


# --------------------------------------------------------------------------- puntuaciones
class ScoresScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.title = pygame.font.Font(None, 56)
        self.font = pygame.font.Font(None, 30)
        self.rows = app.db.top_scores(10)

    def handle_event(self, event):
        if is_confirm(event, self.app.display) or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            self.app.change_scene(MenuScene(self.app))

    def draw(self, surf):
        surf.fill(S.BG)
        draw_text(surf, self.title, t("scores.title"), S.ACCENT, center=(S.LOGICAL_W // 2, 70))
        if not self.rows:
            draw_text(surf, self.font, t("scores.empty"), S.WHITE,
                      center=(S.LOGICAL_W // 2, 200))
        for i, row in enumerate(self.rows):
            y = 130 + i * 40
            draw_text(surf, self.font, f"{i + 1:>2}.  {row['player']}", S.WHITE, topleft=(30, y))
            draw_text(surf, self.font, f"{row['score']}  ({t('scores.level', level=row['level'])})",
                      S.BUTTON_EDGE,
                      topleft=(215, y))
        draw_text(surf, self.font, t("scores.back"), S.WHITE,
                  center=(S.LOGICAL_W // 2, S.LOGICAL_H - 60))


# --------------------------------------------------------------------------- partida
class GameScene(Scene):
    def __init__(self, app, seed=None, game=None):
        """Partida nueva, o la ``game`` restaurada de la base de datos."""
        super().__init__(app)
        self.game = game or Game(seed=seed)
        self.assist = app.db.get_setting("color_assist", "0") == "1"
        self.best = app.db.best_score()
        self.hud = pygame.font.Font(None, 28)
        self.small = pygame.font.Font(None, 22)
        self.big = pygame.font.Font(None, 56)
        self.offsets: dict = {}      # (fila, col) -> [dx, dy] en píxeles; decae a 0 (animación)
        self.particles: list = []    # [x, y, vx, vy, vida, color]
        self.floaters: list = []     # [texto, x, y, vida]
        self.banner = None           # [texto, vida]
        self.hover = None
        self.saved = False
        self.over_t = 0.0
        self.t = 0.0
        self.rng = random.Random()

    # --- entrada ---
    def _cell_at(self, pos):
        x, y = pos
        c = int((x - S.BOARD_X) // S.CELL)
        r = int((y - S.BOARD_Y) // S.CELL)
        if 0 <= r < S.ROWS and 0 <= c < S.COLS:
            return r, c
        return None

    def handle_event(self, event):
        if is_real_mouse_motion(event):
            self.hover = self.app.display.event_pos(event)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.change_scene(MenuScene(self.app))
            return
        pos = tap_position(event, self.app.display)
        confirm_key = (event.type == pygame.KEYDOWN
                       and event.key in (pygame.K_RETURN, pygame.K_SPACE))
        if self.game.over:
            if (pos is not None or confirm_key) and self.over_t > 0.6:
                self.app.change_scene(MenuScene(self.app))
            return
        if pos is not None:
            cell = self._cell_at(pos)
            if cell is not None:
                if self.game.tap(*cell):
                    self._consume_events()
                    self._save_progress()

    # --- eventos del juego -> efectos visuales ---
    def _cell_center(self, r, c):
        return (S.BOARD_X + c * S.CELL + S.CELL / 2, S.BOARD_Y + r * S.CELL + S.CELL / 2)

    def _apply_moves(self, moves, cleared=()):
        old = self.offsets
        moved_src = {src for src, _ in moves}
        moved_dst = {dst for _, dst in moves}
        new = {cell: off for cell, off in old.items()
               if cell not in moved_src and cell not in moved_dst and cell not in cleared}
        for (sr, sc), (dr, dc) in moves:
            ox, oy = old.get((sr, sc), (0.0, 0.0))
            new[(dr, dc)] = [ox + (sc - dc) * S.CELL, oy + (sr - dr) * S.CELL]
        self.offsets = new

    def _consume_events(self):
        for ev in self.game.pop_events():
            d = ev.data
            if ev.kind == "clear":
                color = S.PALETTE[d["color"] % len(S.PALETTE)]
                for r, c in d["cells"]:
                    cx, cy = self._cell_center(r, c)
                    for _ in range(6):
                        ang = self.rng.uniform(0, math.tau)
                        speed = self.rng.uniform(60, 220)
                        self.particles.append([cx, cy, math.cos(ang) * speed,
                                               math.sin(ang) * speed - 80,
                                               self.rng.uniform(0.35, 0.7), color])
                mx = sum(self._cell_center(r, c)[0] for r, c in d["cells"]) / len(d["cells"])
                my = sum(self._cell_center(r, c)[1] for r, c in d["cells"]) / len(d["cells"])
                self.floaters.append([f"+{d['points']}", mx, my, 0.9])
                self._apply_moves(d["moves"], cleared=set(d["cells"]))
                self.best = max(self.best, self.game.score)
            elif ev.kind == "rain":
                self._apply_moves(d["moves"])
                if self.banner is None:  # el aviso de nivel tiene prioridad
                    self.banner = [t("game.rain"), 1.2]
            elif ev.kind == "level":
                self.banner = [t("game.level_banner", level=d["level"]), 1.6]
            elif ev.kind == "over":
                self._save_score()
                self._save_progress()      # borra la partida guardada
            else:
                log.warning("Evento de juego desconocido: %r", ev.kind)

    def _save_progress(self):
        """Guarda la partida tras cada jugada (así sobrevive aunque se cierre la app);
        al terminar se borra para que no aparezca "Continuar"."""
        try:
            if self.game.over:
                self.app.db.delete_game()
            else:
                self.app.db.save_game(self.game.to_state())
        except sqlite3.Error:
            log.error("No se pudo actualizar la partida guardada")

    def _save_score(self):
        if self.saved:
            return
        self.saved = True
        if self.game.score > 0:
            name = self.app.db.get_setting("player_name", t("player.default"))
            try:
                self.app.db.add_score(name, self.game.score, self.game.level)
            except sqlite3.Error:
                # Ya registrado en db.py: no tumbamos la partida por no poder guardar.
                log.error("La puntuación %d no se ha guardado", self.game.score)

    # --- ciclo ---
    def update(self, dt):
        self.t += dt
        self._consume_events()     # por si el juego generó eventos fuera de un toque
        if self.game.over:
            self.over_t += dt
        k = math.exp(-dt * 12.0)
        for cell in list(self.offsets):
            off = self.offsets[cell]
            off[0] *= k
            off[1] *= k
            if abs(off[0]) < 0.5 and abs(off[1]) < 0.5:
                del self.offsets[cell]
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 700 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for f in self.floaters:
            f[2] -= 40 * dt
            f[3] -= dt
        self.floaters = [f for f in self.floaters if f[3] > 0]
        if self.banner:
            self.banner[1] -= dt
            if self.banner[1] <= 0:
                self.banner = None

    # --- dibujo ---
    def draw(self, surf):
        g = self.game
        surf.fill(S.BG)
        pygame.draw.rect(surf, S.PANEL, BOARD_RECT)

        # Orbes (recortados al tablero para que la lluvia entre "desde fuera").
        surf.set_clip(BOARD_RECT)
        for r in range(S.ROWS):
            for c in range(S.COLS):
                v = g.board.get(r, c)
                if v < 0:
                    continue
                cx, cy = self._cell_center(r, c)
                ox, oy = self.offsets.get((r, c), (0.0, 0.0))
                sprite = orb_sprite(v, S.CELL, self.assist)
                surf.blit(sprite, sprite.get_rect(center=(round(cx + ox), round(cy + oy))))

        hover_info = None
        if self.hover is not None and not g.over:
            cell = self._cell_at(self.hover)
            if cell is not None:
                group = g.board.group_at(*cell)
                if len(group) >= S.MIN_GROUP:
                    for r, c in group:
                        cx, cy = self._cell_center(r, c)
                        pygame.draw.circle(surf, S.WHITE, (round(cx), round(cy)),
                                           S.CELL // 2 - 1, 3)
                    hover_info = (len(group), clear_points(len(group)))
        surf.set_clip(None)

        for x, y, _, _, life, color in self.particles:
            pygame.draw.circle(surf, color, (round(x), round(y)), max(1, int(life * 7)))
        for text, x, y, life in self.floaters:
            draw_text(surf, self.hud, text, S.WHITE, center=(round(x), round(y)))

        self._draw_hud(surf, hover_info)
        if self.banner:
            draw_text(surf, self.big, self.banner[0], S.ACCENT,
                      center=(S.LOGICAL_W // 2, S.BOARD_Y + S.BOARD_H // 2))
        if g.over:
            self._draw_over(surf)

    def _draw_hud(self, surf, hover_info):
        g = self.game
        draw_text(surf, self.hud, t("game.points", score=g.score), S.WHITE, topleft=(12, 12))
        draw_text(surf, self.hud, t("game.level", level=g.level), S.WHITE,
                  topright=(S.LOGICAL_W - 12, 12))
        draw_text(surf, self.small, t("game.record", score=self.best), S.BUTTON_EDGE,
                  topleft=(12, 44))
        if hover_info:
            n, pts = hover_info
            draw_text(surf, self.small, t("game.hover", count=n, points=pts), S.ACCENT,
                      topright=(S.LOGICAL_W - 12, 44))
        # Mejor cadena
        draw_text(surf, self.small, t("game.best_chain", count=g.best_chain), S.WHITE,
                  topleft=(12, 70))
        draw_text(surf, self.small, t("game.next_level", score=g.next_level_at), S.BUTTON_EDGE,
                  topright=(S.LOGICAL_W - 12, 70))

    def _draw_over(self, surf):
        g = self.game
        dim = pygame.Surface((S.LOGICAL_W, S.LOGICAL_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        surf.blit(dim, (0, 0))
        cx = S.LOGICAL_W // 2
        draw_text(surf, self.big, t("over.title"), S.ACCENT, center=(cx, 290))
        draw_text(surf, self.hud, t("over.points", score=g.score), S.WHITE, center=(cx, 350))
        draw_text(surf, self.hud, t("over.stats", level=g.level, chain=g.best_chain),
                  S.WHITE, center=(cx, 385))
        if g.score and g.score >= self.best:
            draw_text(surf, self.hud, t("over.new_record"), S.BUTTON_EDGE, center=(cx, 425))
        if self.over_t > 0.6:
            draw_text(surf, self.small, t("over.back"), S.WHITE, center=(cx, 480))
