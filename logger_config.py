"""Configuration centralisee du logging du projet Log Analyser."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_DIRECTORY = Path(__file__).resolve().parent / "logs"
LOG_FORMAT = "%(asctime)s|%(levelname)s|%(name)s|%(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


_LOG_FILES = {
    "__main__": "main.log",
    "main": "main.log",
    "ingestion": "ingestion.log",
    "process": "processing.log",
    "pipeline": "pipeline.log",
    "storage": "storage.log",
    "serving": "serving.log",
}


def get_logger(name: str, log_filename: str | None = None) -> logging.Logger:
    """Retourne un logger avec son propre fichier et une rotation automatique.

    Args:
        name: Nom du module, generalement __name__.
        log_filename: Nom du fichier de log (optionnel).

    Returns:
        Un logger configure. Les appels repetes ne dupliquent pas les handlers.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if log_filename is None:
        module_name = name.split(".")[0]
        log_filename = _LOG_FILES.get(module_name, f"{module_name}.log")

    log_path = LOG_DIRECTORY / log_filename

    # Evite d'ajouter plusieurs fois le meme handler au meme logger.
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler):
            if Path(handler.baseFilename) == log_path.resolve():
                return logger

    try:
        LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=5,
            encoding="utf-8",
        )
    except OSError as error:
        raise RuntimeError(
            f"Impossible de creer le fichier de log '{log_path}': {error}"
        ) from error

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
