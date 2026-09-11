import logging
import logging.handlers
from pathlib import Path

from .config import get_settings


def configure_logging() -> logging.Logger:
    s = get_settings()
    p = Path(s.log_file)
    p.parent.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger("pit_fundamentals_store")
    if log.handlers:
        return log
    log.setLevel(s.log_level.upper())
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(module)s %(message)s")
    fh = logging.handlers.RotatingFileHandler(
        p, maxBytes=10_000_000, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    log.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    log.addHandler(sh)
    log.propagate = False
    return log
