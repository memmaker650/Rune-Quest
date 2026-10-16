"""Configuración central de logging: consola + un fichero por día en la carpeta de logs.

Cada módulo crea su propio logger con ``logging.getLogger(__name__)``; aquí solo se configura
el logger raíz del paquete una vez, al arrancar la app. El nivel se puede cambiar con la
variable de entorno ``RUNEQUEST_LOG_LEVEL`` (DEBUG, INFO, WARNING, ERROR).

Los ficheros se llaman ``RuneQuest_AAAAMMDD.log``; si la app sigue abierta al cambiar de día
se pasa al fichero nuevo. Se borran los de más de ``KEEP_DAYS`` días.
"""

import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

from . import settings as S

FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
PACKAGE = __name__.rpartition(".")[0] or "RuneQuest"
FILE_PREFIX = "RuneQuest_"
DATE_FORMAT = "%Y%m%d"
KEEP_DAYS = 7


def default_log_dir() -> Path:
    """Carpeta de logs del usuario (sandbox en iOS, ~/Library/Logs en macOS)."""
    try:
        from platformdirs import user_log_dir

        return Path(user_log_dir(S.APP_NAME, S.APP_NAME))
    except Exception:  # platformdirs ausente o plataforma no soportada
        return Path.home() / f".{S.APP_NAME.lower()}" / "logs"


def log_file_for(log_dir: Path, day: date) -> Path:
    return Path(log_dir) / f"{FILE_PREFIX}{day.strftime(DATE_FORMAT)}.log"


def remove_old_logs(log_dir: Path, today: date, keep_days: int = KEEP_DAYS) -> list[Path]:
    """Borra los ``RuneQuest_AAAAMMDD.log`` con más de ``keep_days`` días. Devuelve los borrados."""
    removed = []
    for path in Path(log_dir).glob(f"{FILE_PREFIX}*.log"):
        try:
            day = datetime.strptime(path.stem[len(FILE_PREFIX):], DATE_FORMAT).date()
        except ValueError:
            continue  # no es un log diario nuestro
        if (today - day).days > keep_days:
            try:
                path.unlink()
            except OSError:
                continue
            removed.append(path)
    return removed


class DailyFileHandler(logging.FileHandler):
    """Escribe en el fichero del día del registro y cambia de fichero al cambiar de día."""

    def __init__(self, log_dir, keep_days: int = KEEP_DAYS):
        self.log_dir = Path(log_dir)
        self.keep_days = keep_days
        self.day = date.today()
        super().__init__(log_file_for(self.log_dir, self.day), encoding="utf-8")

    def emit(self, record):
        day = date.fromtimestamp(record.created)
        if day != self.day:
            self.day = day
            if self.stream:
                self.stream.close()
                self.stream = None  # FileHandler.emit lo vuelve a abrir con el nombre nuevo
            self.baseFilename = os.path.abspath(log_file_for(self.log_dir, day))
            remove_old_logs(self.log_dir, day, self.keep_days)
        super().emit(record)


def setup_logging(level=None, log_dir=None) -> logging.Logger:
    """Configura el logger del paquete. Llamar una sola vez desde ``main()``."""
    level = level or os.environ.get("RUNEQUEST_LOG_LEVEL", "INFO")
    logger = logging.getLogger(PACKAGE)
    logger.setLevel(level.upper() if isinstance(level, str) else level)
    if logger.handlers:  # ya configurado
        return logger

    formatter = logging.Formatter(FORMAT)
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    logger.addHandler(console)

    log_dir = Path(log_dir) if log_dir else default_log_dir()
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        removed = remove_old_logs(log_dir, date.today())
        file_handler = DailyFileHandler(log_dir)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        logger.warning("No se pudo crear el fichero de log en %s; solo consola", log_dir,
                       exc_info=True)
    else:
        logger.info("Log en fichero: %s", file_handler.baseFilename)
        if removed:
            logger.info("Borrados %d logs de más de %d días: %s", len(removed), KEEP_DAYS,
                        ", ".join(p.name for p in removed))
    return logger
