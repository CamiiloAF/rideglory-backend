import logging
import sys

from loguru import logger

from apps.api_gateway.core.request_context import get_request_id
from apps.api_gateway.core.settings import LOG_JSON, LOG_LEVEL


def _patch_request_id(record: dict) -> None:
    rid = get_request_id()
    record["extra"]["request_id"] = rid if rid is not None else "-"

_STD_LEVEL = getattr(logging, LOG_LEVEL, logging.INFO)


def _setup_stdlib_interception() -> None:
    intercept = InterceptHandler()
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        log = logging.getLogger(name)
        log.handlers = [intercept]
        log.setLevel(_STD_LEVEL)
        log.propagate = False

def configure_logging() -> None:
    logger.configure(patcher=_patch_request_id)

    logger.remove()

    if LOG_JSON:
        logger.add(
            sys.stderr,
            level=LOG_LEVEL,
            serialize=True,
        )
    else:
        logger.add(
            sys.stderr,
            level=LOG_LEVEL,
            format=(
                "<green>{time:DD/MM/YYYY HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{extra[request_id]}</cyan> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
        )
    
    _setup_stdlib_interception()


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        depth = 2
        frame = logging.currentframe()
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )