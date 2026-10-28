"""Persistencia con sqlite3: puntuaciones y ajustes."""

import json
import logging
import shutil
import sqlite3
from pathlib import Path

from . import settings as S

log = logging.getLogger(__name__)

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS scores (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    player     TEXT    NOT NULL,
    score      INTEGER NOT NULL,
    level      INTEGER NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_scores_score ON scores(score DESC);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
PRAGMA user_version = 1;
"""

# Partida sin terminar (como mucho una). ``bolas`` es JSON: [[fila, columna, color], ...].
SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS EstadoPartida (
    id           INTEGER PRIMARY KEY CHECK (id = 1),
    puntuacion   INTEGER NOT NULL,
    nivel        INTEGER NOT NULL,
    toques       INTEGER NOT NULL DEFAULT 0,
    lluvias      INTEGER NOT NULL DEFAULT 0,
    mejor_cadena INTEGER NOT NULL DEFAULT 0,
    filas        INTEGER NOT NULL,
    columnas     INTEGER NOT NULL,
    bolas        TEXT    NOT NULL,
    actualizado  TEXT    NOT NULL DEFAULT (datetime('now'))
);
PRAGMA user_version = 2;
"""

# Modo de juego de la partida guardada ("classic", "fast" o "surprise").
SCHEMA_V3 = """
ALTER TABLE EstadoPartida ADD COLUMN modo TEXT NOT NULL DEFAULT 'classic';
PRAGMA user_version = 3;
"""


DB_NAME = "RuneQuest_database.db"
LEGACY_DB_NAME = "orbes.db"


def _data_dir(app_name: str) -> Path:
    try:
        from platformdirs import user_data_dir

        return Path(user_data_dir(app_name, app_name))
    except Exception:  # platformdirs ausente o plataforma no soportada
        log.warning("platformdirs no disponible; se usa ~/.%s para los datos", app_name.lower(),
                    exc_info=True)
        return Path.home() / f".{app_name.lower()}"


def default_db_path() -> Path:
    """Carpeta de datos de usuario (sandbox en iOS, Application Support en macOS)."""
    base = _data_dir(S.APP_NAME)
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        log.error("No se pudo crear la carpeta de datos %s", base, exc_info=True)
        raise
    path = base / DB_NAME
    _migrate_legacy_db(path)
    return path


def _migrate_legacy_db(path: Path) -> None:
    """Copia la BDD antigua (``orbes.db``, en la carpeta nueva o en "Orbes") si aún no hay una."""
    if path.exists():
        return
    candidates = [path.with_name(LEGACY_DB_NAME),
                  _data_dir(S.LEGACY_APP_NAME) / LEGACY_DB_NAME]
    legacy = next((p for p in candidates if p.exists()), None)
    if legacy is None:
        return
    try:
        shutil.copy2(legacy, path)
    except OSError:
        log.error("No se pudo copiar la base de datos antigua %s a %s", legacy, path,
                  exc_info=True)
    else:
        log.info("Base de datos migrada de %s a %s (la antigua se conserva)", legacy, path)


class Database:
    def __init__(self, path=":memory:"):
        log.info("Abriendo base de datos: %s", path)
        try:
            self.conn = sqlite3.connect(str(path))
            self.conn.row_factory = sqlite3.Row
            self._migrate()
        except sqlite3.Error:
            log.exception("No se pudo abrir o migrar la base de datos %s", path)
            raise

    def _migrate(self):
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version < 1:
            log.info("Migrando esquema de la base de datos: v%d -> v1", version)
            self.conn.executescript(SCHEMA_V1)
        if version < 2:
            log.info("Migrando esquema de la base de datos: v%d -> v2 (EstadoPartida)",
                     max(version, 1))
            self.conn.executescript(SCHEMA_V2)
        if version < 3:
            log.info("Migrando esquema de la base de datos: v%d -> v3 (modo de juego)",
                     max(version, 2))
            self.conn.executescript(SCHEMA_V3)
        # Futuras migraciones: if version < 4: ...

    def close(self):
        try:
            self.conn.close()
        except sqlite3.Error:
            log.warning("Error al cerrar la base de datos", exc_info=True)

    # --- puntuaciones ---
    def add_score(self, player: str, score: int, level: int) -> int:
        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO scores (player, score, level) VALUES (?, ?, ?)",
                    (player, int(score), int(level)),
                )
        except sqlite3.Error:
            log.exception("No se pudo guardar la puntuación (%s, %s, nivel %s)",
                          player, score, level)
            raise
        log.info("Puntuación guardada: %s = %d (nivel %d)", player, score, level)
        return cur.lastrowid

    def top_scores(self, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT player, score, level, created_at FROM scores "
            "ORDER BY score DESC, id ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    # --- ajustes ---
    def get_setting(self, key: str, default=None):
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value) -> None:
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, str(value)),
                )
        except sqlite3.Error:
            log.exception("No se pudo guardar el ajuste %r = %r", key, value)
            raise
        log.info("Ajuste guardado: %s = %s", key, value)

    # --- partida sin terminar ---
    def save_game(self, state: dict) -> None:
        """Guarda (sustituyendo la anterior) la partida en curso. Ver ``Game.to_state``."""
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO EstadoPartida (id, puntuacion, nivel, toques, "
                    "lluvias, mejor_cadena, modo, filas, columnas, bolas, actualizado) "
                    "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                    (state["score"], state["level"], state["taps"], state["rains"],
                     state["best_chain"], state.get("mode", "classic"), state["rows"],
                     state["cols"], json.dumps(state["balls"])),
                )
        except sqlite3.Error:
            log.exception("No se pudo guardar la partida en curso")
            raise
        log.debug("Partida guardada: %d puntos, nivel %d, %d bolas",
                  state["score"], state["level"], len(state["balls"]))

    def load_game(self) -> dict | None:
        """La partida guardada, o None si no hay ninguna (o está corrupta)."""
        row = self.conn.execute("SELECT * FROM EstadoPartida WHERE id = 1").fetchone()
        if row is None:
            return None
        try:
            balls = json.loads(row["bolas"])
        except ValueError:
            log.error("Partida guardada corrupta (bolas no es JSON válido); se descarta")
            self.delete_game()
            return None
        return {
            "score": row["puntuacion"], "level": row["nivel"], "taps": row["toques"],
            "rains": row["lluvias"], "best_chain": row["mejor_cadena"], "mode": row["modo"],
            "rows": row["filas"], "cols": row["columnas"], "balls": balls,
        }

    def has_saved_game(self) -> bool:
        return self.conn.execute("SELECT 1 FROM EstadoPartida WHERE id = 1").fetchone() is not None

    def delete_game(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM EstadoPartida")
        log.info("Partida guardada eliminada")

    # --- estadísticas ---
    def best_score(self) -> int:
        row = self.conn.execute("SELECT MAX(score) AS best FROM scores").fetchone()
        return int(row["best"] or 0)
