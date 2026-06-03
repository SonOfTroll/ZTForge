"""
Structured logging with structlog.

Why structlog over stdlib logging:
- JSON output for machine parsing in production
- Console output with colors for local dev
- Request-id propagation without threading hacks
- Processors pipeline is composable

Audit logging is separated into its own logger so it can be routed
to a dedicated sink (file, SIEM, etc.) without noise from app logs.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict

from app.core.config import get_settings


def _add_app_context(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    """Inject app name and version into every log entry."""
    settings = get_settings()
    event_dict["app"] = settings.app_name
    event_dict["version"] = settings.app_version
    return event_dict


def setup_logging() -> None:
    """Configure structlog + stdlib logging bridge."""
    settings = get_settings()
    is_debug = settings.log_level == "DEBUG"

    # Shared processors
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        _add_app_context,
    ]

    if is_debug:
        # Pretty console output for local dev
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # JSON for production log aggregation
        shared_processors.append(structlog.processors.format_exc_info)
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level)

    # Quiet noisy libraries
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a named logger. Use this instead of structlog.get_logger() directly."""
    return structlog.get_logger(name)


# ── Audit Logger ─────────────────────────────────────────────
# Separate logger for security-relevant events: auth, policy changes,
# simulation runs. These should never be filtered out by log level.

_audit_logger = None


def get_audit_logger() -> structlog.stdlib.BoundLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = structlog.get_logger("ztforge.audit")
    return _audit_logger


async def audit_log(
    action: str,
    user_id: str,
    resource_type: str,
    resource_id: str = "",
    details: dict[str, Any] | None = None,
) -> None:
    """
    Emit a structured audit log entry.

    Every state mutation in the system should call this. The audit log
    is the source of truth for security investigations.
    """
    logger = get_audit_logger()
    logger.info(
        "audit_event",
        action=action,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
    )
