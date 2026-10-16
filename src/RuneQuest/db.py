"""Persistencia con sqlite3: puntuaciones y ajustes."""

import logging
import sqlite3
from pathlib import Path

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


def default_db_path() -> Path:
    """Carpeta de datos de usuario (sandbox en iOS, Application Support en macOS)."""
    try:
        from platformdirs import user_data_dir

        base = Path(user_data_dir("Orbes", "Orbes"))
    except Exception:  # platformdirs ausente o plataforma no soportada
        log.warning("platformdirs no disponible; se usa ~/.orbes para los datos", exc_info=True)
        base = Path.home() / ".orbes"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        log.error("No se pudo crear la carpeta de datos %s", base, exc_info=True)
        raise
    return base / "orbes.db"


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
        # Futuras migraciones: if version < 2: ...

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

    # --- estadísticas ---
    def best_score(self) -> int:
        row = self.conn.execute("SELECT MAX(score) AS best FROM scores").fetchone()
        return int(row["best"] or 0)
