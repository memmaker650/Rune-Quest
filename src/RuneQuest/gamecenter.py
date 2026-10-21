"""Game Center (iOS y macOS) mediante GameKit y rubicon-objc.

Hace tres cosas: identifica al jugador (nombre y id de Game Center), envía las puntuaciones a la
clasificación ``settings.GAMECENTER_LEADERBOARD_ID`` y abre la clasificación de Game Center.

En el resto de plataformas, sin rubicon-objc, con ``RUNEQUEST_GAMECENTER=0`` o si GameKit falla
(p. ej. app sin firmar o sin la capacidad Game Center), se usa ``GameCenter``, que no hace nada:
el juego funciona igual, solo que sin Game Center. Ningún error de aquí debe tumbar la app.

Los callbacks de GameKit llegan por el hilo principal mientras SDL procesa eventos, así que solo
actualizan atributos que las escenas leen al dibujar.
"""

import logging
import os
import sys

from . import settings as S

log = logging.getLogger(__name__)

GK_STATE_LEADERBOARDS = 0      # GKGameCenterViewControllerStateLeaderboards


class GameCenter:
    """Implementación vacía: plataformas sin Game Center o Game Center desactivado."""

    available = False

    def __init__(self):
        self.authenticated = False
        self.player_name: str | None = None
        self.player_id: str | None = None
        self.on_authenticated = None     # callback(GameCenter) al iniciar sesión

    def authenticate(self) -> None:
        pass

    def submit_score(self, score: int) -> None:
        pass

    def show_leaderboards(self) -> None:
        pass


class GameKitCenter(GameCenter):
    """Game Center real (iOS 14+ / macOS 11+)."""

    available = True

    def __init__(self):
        super().__init__()
        from rubicon.objc import Block, ObjCClass, ObjCInstance, ns_from_py, objc_id
        from rubicon.objc.runtime import load_library

        load_library("GameKit")
        self._ObjCInstance = ObjCInstance
        self._ns_from_py = ns_from_py
        self._ObjCClass = ObjCClass
        self._player = ObjCClass("GKLocalPlayer").localPlayer
        self._leaderboard = ObjCClass("GKLeaderboard")
        self._pending_score = 0          # mejor puntuación pendiente de enviar
        # Hay que conservar los bloques: si Python los libera, GameKit llamaría a memoria muerta.
        self._auth_block = Block(self._on_auth, None, objc_id, objc_id)
        self._submit_block = Block(self._on_submitted, None, objc_id)
        self._noop_block = Block(lambda: None, None)

    # --- inicio de sesión ---
    def authenticate(self) -> None:
        log.info("Game Center: iniciando sesión")
        self._player.authenticateHandler = self._auth_block

    def _on_auth(self, view_controller, error) -> None:
        try:
            if view_controller:
                # Game Center pide al jugador que inicie sesión: hay que mostrar su pantalla.
                self._present(self._ObjCInstance(view_controller))
                return
            if error:
                err = self._ObjCInstance(error)
                log.warning("Game Center no disponible: %s (código %s)",
                            err.localizedDescription, err.code)
                self.authenticated = False
                return
            if not self._player.isAuthenticated:
                log.info("Game Center: el jugador no ha iniciado sesión")
                self.authenticated = False
                return
            self.authenticated = True
            self.player_name = str(self._player.displayName or self._player.alias)
            self.player_id = str(self._player.gamePlayerID)
            log.info("Game Center: sesión iniciada como %s", self.player_name)
            if self._pending_score:
                self.submit_score(self._pending_score)
            if self.on_authenticated:
                self.on_authenticated(self)
        except Exception:
            log.exception("Error procesando la respuesta de Game Center")

    def _present(self, view_controller) -> None:
        if sys.platform == "ios":
            app = self._ObjCClass("UIApplication").sharedApplication
            root = app.keyWindow.rootViewController
            root.presentViewController_animated_completion_(view_controller, True, None)
        else:
            dialog = self._ObjCClass("GKDialogController").sharedDialogController
            dialog.parentWindow = self._ObjCClass("NSApplication").sharedApplication.keyWindow
            dialog.presentViewController_(view_controller)
        log.info("Game Center: mostrando la pantalla de inicio de sesión")

    # --- puntuaciones ---
    def submit_score(self, score: int) -> None:
        score = int(score)
        if score <= 0:
            return
        if not self.authenticated:
            self._pending_score = max(self._pending_score, score)
            log.info("Game Center sin sesión: la puntuación %d se enviará al iniciar sesión", score)
            return
        try:
            self._leaderboard.submitScore_context_player_leaderboardIDs_completionHandler_(
                score, 0, self._player, self._ns_from_py([S.GAMECENTER_LEADERBOARD_ID]),
                self._submit_block)
        except Exception:
            log.exception("No se pudo enviar la puntuación %d a Game Center", score)
            return
        self._pending_score = 0
        log.info("Game Center: enviando %d a la clasificación %s",
                 score, S.GAMECENTER_LEADERBOARD_ID)

    def _on_submitted(self, error) -> None:
        if error:
            err = self._ObjCInstance(error)
            log.error("Game Center rechazó la puntuación: %s (código %s)",
                      err.localizedDescription, err.code)
        else:
            log.info("Game Center: puntuación registrada")

    # --- clasificación ---
    def show_leaderboards(self) -> None:
        try:
            access_point = self._ObjCClass("GKAccessPoint").shared
            access_point.triggerAccessPointWithState_handler_(GK_STATE_LEADERBOARDS,
                                                               self._noop_block)
        except Exception:
            log.exception("No se pudo abrir la clasificación de Game Center")
        else:
            log.info("Game Center: abriendo la clasificación")


def create() -> GameCenter:
    """Game Center real si la plataforma lo permite; si no, la implementación vacía."""
    if os.environ.get("RUNEQUEST_GAMECENTER", "1") == "0":
        log.info("Game Center desactivado (RUNEQUEST_GAMECENTER=0)")
        return GameCenter()
    if sys.platform not in ("ios", "darwin"):
        log.info("Game Center no existe en %s", sys.platform)
        return GameCenter()
    try:
        return GameKitCenter()
    except ImportError:
        log.warning("rubicon-objc no está instalado: Game Center desactivado")
    except Exception:
        log.exception("No se pudo cargar GameKit: Game Center desactivado")
    return GameCenter()
