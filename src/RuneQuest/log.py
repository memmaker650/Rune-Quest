"""Configuración central de logging: consola + fichero rotativo en la carpeta de logs del usuario.

Cada módulo crea su propio logger con ``logging.getLogger(__name__)``; aquí solo se configura
el logger raíz del paquete una vez, al arrancar la app. El nivel se puede cambiar con la
variable de entorno ``RUNEQUEST_LOG_LEVEL`` (DEBUG, INFO, WARNING, ERROR).
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
PACKAGE = __name__.rpartition(".")[0] or "RuneQuest"


def default_log_dir() -> Path:
    """Carpeta de logs del usuario (sandbox en iOS, ~/Library/Logs en macOS)."""
    try:
        from platformdirs import user_log_dir

        return Path(user_log_dir("Orbes", "Orbes"))
    except Exception:  # platformdirs ausente o plataforma no soportada
        return Path.home() / ".orbes" / "logs"


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
        file_handler = RotatingFileHandler(
            log_dir / "runequest.log", maxBytes=512 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        logger.warning("No se pudo crear el fichero de log en %s; solo consola", log_dir,
                       exc_info=True)
    else:
        logger.info("Log en fichero: %s", log_dir / "runequest.log")
    return logger
