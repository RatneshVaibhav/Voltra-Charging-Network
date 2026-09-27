import logging
from pathlib import Path


def build_logger(log_path: Path, level: str = "INFO") -> logging.Logger:
    """Console + file logger. Messages start with the stage name, e.g. 'EXTRACT | source=R2 ...'."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("voltra_pipeline")
    logger.setLevel(getattr(logging, level, logging.INFO))
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    for handler in (logging.StreamHandler(), logging.FileHandler(log_path, mode="w")):
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    return logger
