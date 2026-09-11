from pathlib import Path


class ArelleUnavailable(RuntimeError):
    pass


def validate_instance(path: str | Path) -> int:
    try:
        from arelle import Cntlr, ModelManager
    except ImportError as exc:
        raise ArelleUnavailable("Install the xbrl extra to use Arelle validation.") from exc
    ctl = Cntlr.Cntlr(logFileName="logToPrint")
    mm = ModelManager.initialize(ctl)
    model = mm.load(str(path))
    if model is None:
        raise ValueError(f"Arelle could not load {path}")
    try:
        return len(model.facts)
    finally:
        model.close()
