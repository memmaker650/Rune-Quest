"""Aplicación: bucle principal y gestión de escenas."""

import logging
import platform
import sqlite3
import sys

import pygame

from . import __version__, gamecenter, translations
from . import settings as S
from .db import Database, default_db_path
from .display import Display
from .log import setup_logging
from .scenes import MenuScene

log = logging.getLogger(__name__)


class App:
    def __init__(self, db_path=None):
        log.info("Iniciando Rune Quest %s (Python %s, pygame-ce %s, %s)", __version__,
                 platform.python_version(), pygame.version.ver, sys.platform)
        passed, failed = pygame.init()
        if failed:
            log.warning("pygame.init(): %d módulos no se pudieron inicializar", failed)
        pygame.display.set_caption("Rune Quest")
        self.display = Display()
        self.db = Database(db_path or default_db_path())
        translations.load()
        translations.set_language(self.db.get_setting("language", translations.current().code))
        self.gamecenter = gamecenter.create()
        self.gamecenter.on_authenticated = self._on_gamecenter_login
        self.gamecenter.authenticate()
        self.clock = pygame.time.Clock()
        self.running = True
        self.scene = MenuScene(self)

    def _on_gamecenter_login(self, gc):
        """Usa el nombre de Game Center para las puntuaciones locales y sube el récord local."""
        try:
            self.db.set_setting("player_name", gc.player_name)
        except sqlite3.Error:
            log.error("No se pudo guardar el nombre de Game Center como nombre del jugador")
        gc.submit_score(self.db.best_score())

    def change_scene(self, scene):
        log.info("Cambio de escena: %s -> %s",
                 type(self.scene).__name__, type(scene).__name__)
        self.scene = scene

    def quit(self):
        log.info("Salida solicitada")
        self.running = False

    def run(self, max_frames=None):
        frames = 0
        try:
            while self.running:
                dt = min(self.clock.tick(S.FPS) / 1000.0, 1 / 30)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        log.info("Evento QUIT recibido")
                        self.running = False
                    else:
                        self.scene.handle_event(event)
                self.scene.update(dt)
                self.scene.draw(self.display.surface)
                self.display.present()
                frames += 1
                if max_frames is not None and frames >= max_frames:
                    break
        except Exception:
            log.exception("Error no controlado en el bucle principal (escena %s)",
                          type(self.scene).__name__)
            raise
        finally:
            log.info("Cerrando la aplicación tras %d frames", frames)
            self.db.close()
            pygame.quit()


def main():
    setup_logging()
    App().run()
