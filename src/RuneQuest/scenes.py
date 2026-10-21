"""Escenas: menú, nueva partida, partida y puntuaciones."""

import logging
import math
import random
import sqlite3
import sys

import pygame

from . import translations
from . import settings as S
from .controls import is_confirm, is_real_mouse_motion, release_position, tap_position
from .board import neighbours
from .game import Game, clear_points
from .sprites import orb_sprite
from .translations import t
from .ui import Button, CloseButton, FlagButton, ModeButton, draw_text, draw_text_outlined

log = logging.getLogger(__name__)

IS_IOS = sys.platform == "ios"


def format_points(n: int) -> str:
    """5000 -> "5.000" (es), "5,000" (en), "5 000" (fr): separador de miles del idioma."""
    return f"{n:,}".replace(",", t("format.thousands"))


def links_enabled(db) -> bool:
    """Si se dibujan los enlaces que unen los orbes de cada combinación (activado por defecto)."""
    return db.get_setting("links", "1") == "1"


def assist_mode(db) -> str:
    """Ayuda visual elegida ("none", "geo" o "runes"). Hereda el ajuste antiguo "color_assist"
    (sí/no) de versiones anteriores, que equivale a "geo"."""
    mode = db.get_setting("assist")
    if mode in S.ASSIST_MODES:
        return mode
    if mode is not None:
        log.warning("Ayuda visual desconocida %r en los ajustes; se usa 'none'", mode)
        return "none"
    return "geo" if db.get_setting("color_assist", "0") == "1" else "none"
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


class ButtonScene(Scene):
    """Escena con botones que se oscurecen al pulsar y actúan al soltar encima
    (soltar fuera cancela). Las subclases definen ``_button_at`` y ``_on_click``."""

    def __init__(self, app):
        super().__init__(app)
        self.pressed = None          # (nombre, botón) pulsado y aún sin soltar

    def _button_at(self, pos):
        return None

    def _on_click(self, name):
        pass

    def handle_pointer(self, event) -> bool:
        """Procesa pulsar/soltar. True si el evento era de puntero (ya consumido)."""
        pos = tap_position(event, self.app.display)
        if pos is not None:
            self.pressed = self._button_at(pos)
            if self.pressed:
                self.pressed[1].pressed = True
            return True
        pos = release_position(event, self.app.display)
        if pos is not None:
            pressed, self.pressed = self.pressed, None
            if pressed is not None:
                name, button = pressed
                button.pressed = False
                if button.hit(pos):
                    self._on_click(name)
            return True
        return False


# --------------------------------------------------------------------------- menú
class MenuScene(ButtonScene):
    def __init__(self, app):
        super().__init__(app)
        self.title_font = pygame.font.Font(None, 96)
        self.font = pygame.font.Font(None, 36)
        self.small = pygame.font.Font(None, 22)
        self.t = 0.0
        # Salir: botón cuadrado abajo a la izquierda, alineado con la bandera (en iOS no se sale).
        self.close_button = None if IS_IOS else CloseButton((12, S.LOGICAL_H - 52, 38, 38))
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
        ]
        self.buttons = []
        y = 312
        for name, label in entries:
            self.buttons.append((name, Button((60, y, 240, 50), label)))
            y += 58
        assist = assist_mode(self.app.db)
        self.buttons.append(("assist", ModeButton(
            (60, y, 240, 66), t("menu.assist"), t(f"assist.{assist}"),
            S.ASSIST_MODES.index(assist), len(S.ASSIST_MODES), self.small)))
        y += 74
        links = "menu.links_on" if links_enabled(self.app.db) else "menu.links_off"
        self.buttons.append(("links", Button((60, y, 240, 50), t(links))))
        self.lang_button = FlagButton((S.LOGICAL_W - 66, S.LOGICAL_H - 52, 54, 38),
                                      translations.current().flag)

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
            self.app.change_scene(NewGameScene(self.app))
        elif name == "scores":
            self.app.change_scene(ScoresScene(self.app))
        elif name == "links":
            on = links_enabled(self.app.db)
            try:
                self.app.db.set_setting("links", "0" if on else "1")
            except sqlite3.Error:
                log.error("No se pudo cambiar la opción de enlaces; se mantiene como estaba")
            else:
                log.info("Enlaces entre orbes: %s", "no" if on else "sí")
            self._build_buttons()
        elif name == "assist":
            current = S.ASSIST_MODES.index(assist_mode(self.app.db))
            mode = S.ASSIST_MODES[(current + 1) % len(S.ASSIST_MODES)]
            try:
                self.app.db.set_setting("assist", mode)
            except sqlite3.Error:
                log.error("No se pudo cambiar la ayuda visual; se mantiene como estaba")
            else:
                log.info("Ayuda visual: %s", mode)
            self._build_buttons()
        elif name == "quit":
            self.app.quit()
        else:
            log.warning("Botón de menú desconocido: %r", name)

    def _button_at(self, pos):
        if self.lang_button.hit(pos):
            return "lang", self.lang_button
        if self.close_button and self.close_button.hit(pos):
            return "quit", self.close_button
        for name, button in self.buttons:
            if button.hit(pos):
                return name, button
        return None

    def _on_click(self, name):
        if name == "lang":
            self._next_language()
        else:
            self._activate(name)

    def handle_event(self, event):
        if self.handle_pointer(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._activate(self.buttons[0][0])   # "Continuar" si existe; si no, "Jugar"
            elif event.key == pygame.K_ESCAPE and not IS_IOS:
                self.app.quit()

    def update(self, dt):
        self.t += dt

    def _draw_title(self, surf):
        """"Rune" arriba y "Quest" debajo empezando justo bajo la "n": el bloque escalonado
        queda centrado en conjunto, con "Rune" desplazado a la izquierda."""
        font = self.title_font
        first, second = "Rune", "Quest"
        indent = font.size("Ru")[0]                  # x de la "n" dentro de "Rune"
        width = max(font.size(first)[0], indent + font.size(second)[0])
        left = (S.LOGICAL_W - width) // 2
        line_gap = font.get_ascent()                 # sin interlineado extra: bloque compacto
        top = 44
        for text, x, y in ((first, left, top), (second, left + indent, top + line_gap)):
            shadow = font.render(text, True, S.BLACK)
            shadow.set_alpha(110)
            surf.blit(shadow, (x + 3, y + 4))
            surf.blit(font.render(text, True, S.ACCENT), (x, y))

    def draw(self, surf):
        surf.fill(S.BG)
        assist = assist_mode(self.app.db)
        for i in range(S.MAX_COLORS):  # orbes decorativos flotando
            x = 30 + i * 60 + math.sin(self.t * 1.3 + i) * 10
            y = 210 + math.sin(self.t * 1.7 + i * 1.1) * 14
            sprite = orb_sprite(i, 52, assist)
            surf.blit(sprite, sprite.get_rect(center=(x, y)))
        self._draw_title(surf)
        draw_text(surf, self.small, t("menu.subtitle"), S.WHITE,
                  center=(S.LOGICAL_W // 2, 290))
        for _, button in self.buttons:
            button.draw(surf, self.font)
        self.lang_button.draw(surf)
        if self.close_button:
            self.close_button.draw(surf)
        if self.best:
            draw_text(surf, self.small, t("menu.record", score=self.best), S.WHITE,
                      center=(S.LOGICAL_W // 2, S.LOGICAL_H - 40))
        gc = self.app.gamecenter
        if gc.authenticated:
            draw_text(surf, self.small, t("menu.gc_player", name=gc.player_name), S.ACCENT,
                      center=(S.LOGICAL_W // 2, S.LOGICAL_H - 70))


# --------------------------------------------------------------------------- nueva partida
class NewGameScene(ButtonScene):
    """Segunda pantalla al pulsar "Jugar": empezar partida y elegir el modo de juego."""

    def __init__(self, app):
        super().__init__(app)
        self.title = pygame.font.Font(None, 56)
        self.font = pygame.font.Font(None, 36)
        self.small = pygame.font.Font(None, 22)
        saved = app.db.get_setting("game_mode", S.GAME_MODES[0])
        self.mode = saved if saved in S.GAME_MODES else S.GAME_MODES[0]
        self._build_buttons()

    def _build_buttons(self):
        self.start_button = Button((60, 300, 240, 56), t("play.start"))
        self.mode_button = ModeButton((60, 372, 240, 84), t("play.mode"),
                                      t(f"mode.{self.mode}"), S.GAME_MODES.index(self.mode),
                                      len(S.GAME_MODES), self.small)
        self.back_button = Button((60, 540, 240, 52), t("play.back"))

    def _next_mode(self):
        i = S.GAME_MODES.index(self.mode)
        self.mode = S.GAME_MODES[(i + 1) % len(S.GAME_MODES)]
        log.info("Modo de juego seleccionado: %s", self.mode)
        try:
            self.app.db.set_setting("game_mode", self.mode)
        except sqlite3.Error:
            log.error("No se pudo guardar el modo de juego; solo se aplica a esta sesión")
        self._build_buttons()

    def _button_at(self, pos):
        for name, button in (("start", self.start_button), ("mode", self.mode_button),
                             ("back", self.back_button)):
            if button.hit(pos):
                return name, button
        return None

    def _on_click(self, name):
        if name == "start":
            self.app.change_scene(GameScene(self.app, mode=self.mode))
        elif name == "mode":
            self._next_mode()
        elif name == "back":
            self.app.change_scene(MenuScene(self.app))

    def handle_event(self, event):
        if self.handle_pointer(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._on_click("start")
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                self._next_mode()
            elif event.key == pygame.K_ESCAPE:
                self._on_click("back")

    def draw(self, surf):
        surf.fill(S.BG)
        draw_text(surf, self.title, t("play.title"), S.ACCENT, center=(S.LOGICAL_W // 2, 200))
        self.start_button.draw(surf, self.font)
        self.mode_button.draw(surf, self.font)
        self.back_button.draw(surf, self.font)


# --------------------------------------------------------------------------- puntuaciones
class ScoresScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.title = pygame.font.Font(None, 56)
        self.font = pygame.font.Font(None, 30)
        self.rows = app.db.top_scores(10)
        self.gc_button = Button((60, S.LOGICAL_H - 140, 240, 52), t("scores.gamecenter"))

    def _gc_button_visible(self) -> bool:
        return self.app.gamecenter.authenticated

    def handle_event(self, event):
        # El botón de Game Center se oscurece al pulsarlo y actúa al soltar (como en el menú);
        # tocar en cualquier otro sitio vuelve al menú.
        pos = tap_position(event, self.app.display)
        if pos is not None and self._gc_button_visible() and self.gc_button.hit(pos):
            self.gc_button.pressed = True
            return
        up = release_position(event, self.app.display)
        if up is not None and self.gc_button.pressed:
            self.gc_button.pressed = False
            if self.gc_button.hit(up):
                self.app.gamecenter.show_leaderboards()
            return
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
        if self._gc_button_visible():
            self.gc_button.draw(surf, self.font)
        draw_text(surf, self.font, t("scores.back"), S.WHITE,
                  center=(S.LOGICAL_W // 2, S.LOGICAL_H - 60))


# --------------------------------------------------------------------------- partida
class GameScene(Scene):
    def __init__(self, app, seed=None, game=None, mode=S.GAME_MODES[0]):
        """Partida nueva en el modo ``mode``, o la ``game`` restaurada de la base de datos."""
        super().__init__(app)
        self.game = game or Game(seed=seed, mode=mode)
        self.assist = assist_mode(app.db)
        self.links = links_enabled(app.db)
        self._links_cache = (None, [], [])  # (tablero, pares, triángulos) de los enlaces
        # Los enlaces se ocultan mientras llueve y vuelven LINKS_DELAY_AFTER_RAIN segundos
        # después de que caiga el último orbe, con un fundido.
        self.rain_falling = False
        self.links_wait = 0.0
        self.links_alpha = 1.0       # 0 = ocultos, 1 = visibles
        self.best = app.db.best_score()
        self.hud = pygame.font.Font(None, 28)
        self.small = pygame.font.Font(None, 22)
        self.big = pygame.font.Font(None, 56)
        self.bonus_font = pygame.font.Font(None, 46)
        self.score_font = pygame.font.Font(None, 52)     # puntuación final
        self.offsets: dict = {}      # (fila, col) -> [dx, dy, velocidad]; dx, dy decaen a 0
        self.particles: list = []    # [x, y, vx, vy, vida, color]
        self.floaters: list = []     # [texto, x, y, vida]
        self.banners: list = []      # avisos en cola; se muestra el primero (ver _queue_banner)
        self.hover = None
        self.saved = False
        self.over_t = 0.0
        self.t = 0.0
        self.rng = random.Random()

    # --- entrada ---
    def _cell_at(self, pos):
        x, y = pos
        c = int((x - S.BOARD_X) // S.CELL)
        shift = S.COL_SHIFT if c % 2 else 0        # columnas impares: media celda más abajo
        r = int((y - S.BOARD_Y - shift) // S.CELL)
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
        shift = S.COL_SHIFT if c % 2 else 0        # columnas impares: media celda más abajo
        return (S.BOARD_X + c * S.CELL + S.CELL / 2, S.BOARD_Y + r * S.CELL + S.CELL / 2 + shift)

    def _apply_moves(self, moves, cleared=(), rate=S.ANIM_RATE):
        old = self.offsets
        moved_src = {src for src, _ in moves}
        moved_dst = {dst for _, dst in moves}
        new = {cell: off for cell, off in old.items()
               if cell not in moved_src and cell not in moved_dst and cell not in cleared}
        for (sr, sc), (dr, dc) in moves:
            ox, oy = old.get((sr, sc), (0.0, 0.0))[:2]
            new[(dr, dc)] = [ox + (sc - dc) * S.CELL, oy + (sr - dr) * S.CELL, rate]
        self.offsets = new

    def _queue_banner(self, lines, life):
        """Encola un aviso: ``lines`` = [(texto, fuente, color), ...] durante ``life`` segundos."""
        self.banners.append([lines, life])

    def _bonus_banner(self, title, color, bonus):
        lines = [(part, self.bonus_font, color) for part in title.split("|")]
        lines.append((t("bonus.points", points=format_points(bonus)), self.hud, S.WHITE))
        self._queue_banner(lines, 2.2)

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
            elif ev.kind == "color_clear":
                name = t(f"color.{d['color'] % len(S.PALETTE)}")
                self._bonus_banner(t("bonus.color", color=name),
                                   S.PALETTE[d["color"] % len(S.PALETTE)], d["bonus"])
            elif ev.kind == "board_clear":
                self._bonus_banner(t("bonus.board"), S.ACCENT, d["bonus"])
            elif ev.kind == "rain":
                self._apply_moves(d["moves"], rate=S.RAIN_ANIM_RATE)
                self.rain_falling = True
                self.links_alpha = 0.0
                self._queue_banner([(t("game.rain"), self.big, S.ACCENT)], 1.2)
            elif ev.kind == "level":
                self._queue_banner([(t("game.level_banner", level=d["level"]), self.big,
                                     S.ACCENT)], 1.6)
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
            self.app.gamecenter.submit_score(self.game.score)
            name = (self.app.gamecenter.player_name
                    or self.app.db.get_setting("player_name", t("player.default")))
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
        for cell in list(self.offsets):
            off = self.offsets[cell]
            k = math.exp(-dt * (off[2] if len(off) > 2 else S.ANIM_RATE))
            off[0] *= k
            off[1] *= k
            if abs(off[0]) < 0.5 and abs(off[1]) < 0.5:
                del self.offsets[cell]
        self._update_links_visibility(dt)
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
        if self.banners:
            self.banners[0][1] -= dt
            if self.banners[0][1] <= 0:
                self.banners.pop(0)

    # --- dibujo ---
    def draw(self, surf):
        g = self.game
        surf.fill(S.BG)
        pygame.draw.rect(surf, S.PANEL, BOARD_RECT)

        # Orbes (recortados al tablero para que la lluvia entre "desde fuera").
        surf.set_clip(BOARD_RECT)
        if self.links and self.links_alpha > 0:
            self._draw_links(surf)
        for r in range(S.ROWS):
            for c in range(S.COLS):
                v = g.board.get(r, c)
                if v < 0:
                    continue
                cx, cy = self._cell_center(r, c)
                ox, oy = self.offsets.get((r, c), (0.0, 0.0))[:2]
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
        if self.banners:
            self._draw_banner(surf, self.banners[0][0])
        if g.over:
            self._draw_over(surf)

    def _rain_still_falling(self) -> bool:
        return any(len(off) > 2 and off[2] == S.RAIN_ANIM_RATE for off in self.offsets.values())

    def _update_links_visibility(self, dt):
        if self.rain_falling:
            if not self._rain_still_falling():   # acaba de caer el último orbe
                self.rain_falling = False
                self.links_wait = S.LINKS_DELAY_AFTER_RAIN
        elif self.links_wait > 0:
            self.links_wait -= dt
        elif self.links_alpha < 1:
            self.links_alpha = min(1.0, self.links_alpha + dt / S.LINKS_FADE_IN)

    def _link_pairs(self):
        """Pares de orbes vecinos que pertenecen a una misma combinación jugable."""
        return self._link_shapes()[0]

    def _link_shapes(self):
        """(pares, triángulos) de orbes vecinos de una misma combinación jugable. Los triángulos
        (tres orbes que se tocan entre sí) se rellenan para que no queden huecos en las uniones.
        Se recalcula solo cuando cambia el tablero."""
        grid = self.game.board.grid
        snapshot = tuple(map(tuple, grid))
        if self._links_cache[0] == snapshot:
            return self._links_cache[1:]
        pairs, triangles, seen = [], [], set()
        board = self.game.board
        for r in range(board.rows):
            for c in range(board.cols):
                if (r, c) in seen or grid[r][c] < 0:
                    continue
                group = board.group_at(r, c)
                seen.update(group)
                if len(group) < S.MIN_GROUP:
                    continue
                members = set(group)
                for cell in group:
                    near = [o for o in neighbours(*cell) if o in members and cell < o]
                    for other in near:
                        pairs.append((cell, other, grid[r][c]))
                        for third in near:
                            if other < third and third in neighbours(*other):
                                triangles.append((cell, other, third, grid[r][c]))
        self._links_cache = (snapshot, pairs, triangles)
        return pairs, triangles

    def _orb_pos(self, cell):
        cx, cy = self._cell_center(*cell)
        ox, oy = self.offsets.get(cell, (0.0, 0.0))[:2]
        return cx + ox - BOARD_RECT.left, cy + oy - BOARD_RECT.top

    def _draw_links(self, surf):
        """Bandas translúcidas del color del grupo que unen sus orbes (bajo los orbes)."""
        pairs, triangles = self._link_shapes()
        if not pairs:
            return
        layer = pygame.Surface(BOARD_RECT.size, pygame.SRCALPHA)

        def tint(color):  # el color del orbe, algo aclarado (como en un cristal)
            base = S.PALETTE[color % len(S.PALETTE)]
            return (*(v + (255 - v) * 0.2 for v in base), S.LINK_ALPHA)

        for a, b, c, color in triangles:
            pygame.draw.polygon(layer, tint(color), [self._orb_pos(p) for p in (a, b, c)])
        for a, b, color in pairs:
            rgba = tint(color)
            pa, pb = self._orb_pos(a), self._orb_pos(b)
            pygame.draw.line(layer, rgba, pa, pb, S.LINK_WIDTH)
            for p in (pa, pb):  # extremos redondeados para que las uniones queden limpias
                pygame.draw.circle(layer, rgba, (round(p[0]), round(p[1])), S.LINK_WIDTH // 2)
        if self.links_alpha < 1:
            layer.set_alpha(round(255 * self.links_alpha))
        surf.blit(layer, BOARD_RECT.topleft)

    def _draw_banner(self, surf, lines):
        """Aviso centrado sobre el tablero, con un panel translúcido para que se lea bien."""
        heights = [font.get_linesize() for _, font, _ in lines]
        width = max(font.size(text)[0] for text, font, _ in lines) + 40
        panel = pygame.Rect(0, 0, min(S.LOGICAL_W - 16, width), sum(heights) + 28)
        panel.center = (S.LOGICAL_W // 2, S.BOARD_Y + S.BOARD_H // 2)
        shade = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(shade, (10, 12, 28, 215), shade.get_rect(), border_radius=16)
        pygame.draw.rect(shade, (*S.BUTTON_EDGE, 200), shade.get_rect(), width=2, border_radius=16)
        surf.blit(shade, panel)
        y = panel.top + 14
        for (text, font, color), h in zip(lines, heights):
            draw_text(surf, font, text, color, center=(S.LOGICAL_W // 2, y + h // 2))
            y += h

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
        panel = pygame.Rect(16, 236, S.LOGICAL_W - 32, 300)
        pygame.draw.rect(surf, S.OVER_PANEL, panel, border_radius=18)
        pygame.draw.rect(surf, S.BUTTON_EDGE, panel, width=2, border_radius=18)
        draw_text(surf, self.big, t("over.title"), S.ACCENT, center=(cx, 280))
        points = t("over.points", score=format_points(g.score))
        # La letra más grande que quepa en el panel (puntuaciones de muchas cifras).
        font = next((f for f in (self.score_font, self.bonus_font)
                     if f.size(points)[0] <= panel.width - 24), self.hud)
        draw_text_outlined(surf, font, points, S.GOLD, S.GOLD_OUTLINE, center=(cx, 345))
        draw_text(surf, self.hud, t("over.level", level=g.level), S.WHITE, center=(cx, 397))
        draw_text(surf, self.hud, t("over.best_combo", count=g.best_chain), S.WHITE,
                  center=(cx, 430))
        if g.score and g.score >= self.best:
            draw_text(surf, self.hud, t("over.new_record"), S.BUTTON_EDGE, center=(cx, 470))
        if self.over_t > 0.6:
            draw_text(surf, self.small, t("over.back"), S.WHITE, center=(cx, 510))
