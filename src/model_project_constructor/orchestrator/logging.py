"""Structured logging helpers for the orchestrator pipeline.

Phase 6 scope (architecture-plan §14): structured logging with
``run_id`` / ``correlation_id`` threaded through each agent call.

The implementation uses the stdlib ``logging`` module and emits
structured events by attaching a ``context`` dict to every record via
``extra=``. Downstream handlers (JSON formatters, log aggregators) can
parse the structured fields without scraping the message string. This
keeps the orchestrator free of any third-party logging dependency while
still producing machine-readable output.

The public surface:

- :func:`get_logger` — returns the orchestrator's named stdlib logger.
- :func:`make_logged_runner` — wraps a pipeline runner callable so every
  invocation emits ``agent.start`` / ``agent.end`` / ``agent.error``
  events with ``run_id`` + ``correlation_id`` + ``agent`` bound, plus the
  call's ``duration_ms``. The wrapper preserves the runner's signature.

The orchestrator's ``pipeline.py`` does **not** import this module. The
caller wraps runners before passing them to :func:`run_pipeline`, so the
pipeline driver stays dependency-free and the observability layer is
opt-in per deployment.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

ORCHESTRATOR_LOGGER_NAME = "model_project_constructor.orchestrator"

EVENT_AGENT_START = "agent.start"
EVENT_AGENT_END = "agent.end"
EVENT_AGENT_ERROR = "agent.error"


def get_logger(name: str = ORCHESTRATOR_LOGGER_NAME) -> logging.Logger:
    """Return the orchestrator's named stdlib logger."""

    return logging.getLogger(name)


def _emit(
    logger: logging.Logger,
    level: int,
    event: str,
    context: dict[str, Any],
) -> None:
    logger.log(level, event, extra={"context": context})


def _class_name(error: BaseException) -> str:
    """The exception's class name, or ``<unprintable>`` when it is not a short ASCII identifier.

    A class name is chosen by code, never by the repository host or a database driver, so it is
    safe to carry; a class built at run time (``type(name, ...)``) can be named anything, and a
    name that is not a plain identifier is replaced rather than carried. The same rule
    ``orchestrator.pipeline._website_failure`` applies to the reason it saves; a test holds the
    two in step for every ordinary class.

    It has a second caller, ``scripts/run_pipeline.py::_draft_incomplete_from_exception``, which
    names the scripted intake's failure in the report it saves and the line it prints; moving or
    renaming this function breaks that import.

    It fails closed, and is stricter than that copy in one respect. The wrapper reads the name for
    an exception it is about to re-raise, so reading it must not be a raise site: a metaclass whose
    ``__name__`` raises would otherwise replace the runner's exception. And the name must be an
    exact ``str``: a subclass can answer ``isascii`` and ``len`` however it likes. (The website
    stage's copy still reads the name unguarded; ``BACKLOG.md`` files it.)
    """

    try:
        name = type(error).__name__
        if type(name) is str and name.isascii() and name.isidentifier() and len(name) <= 100:
            return name
    except Exception:
        pass
    return "<unprintable>"


def make_logged_runner(
    runner: Callable[..., T],
    *,
    agent_name: str,
    run_id: str,
    correlation_id: str,
    logger: logging.Logger | None = None,
) -> Callable[..., T]:
    """Wrap ``runner`` so each call emits start / end / error events.

    The wrapper:

    - Emits ``agent.start`` at level ``INFO`` immediately before the call.
    - Emits ``agent.end`` at level ``INFO`` on success, with ``duration_ms``
      and (if the result carries a ``status`` attribute) the result's
      status.
    - Emits ``agent.error`` at level ``ERROR`` if the runner raises,
      capturing ``error_type`` (the exception's class name) and
      ``duration_ms``, then re-raises the original exception.

    All records include the bound context ``{"agent", "run_id",
    "correlation_id"}`` on the ``context`` extra.

    ``agent.error`` never carries what the exception said. An exception's
    text is whatever the code that raised it put in it (a pydantic
    ``ValidationError`` quotes the input it refused, a database driver may
    echo the connection back, a gateway's error page can echo a header),
    and a JSON formatter renders the whole ``context``. Nothing that needs
    no secret can find a bare token in free text, so the message is not
    read at all: the record has no ``error_message``, no ``exc_info`` (a
    traceback prints the message and the chain behind it), and the wrapper
    cannot be replaced by an exception whose own ``__str__`` raises. The
    event is emitted after the ``except`` block, not inside it: a handler
    that fails while writing has the exception being handled chained to its
    own, and ``logging`` prints that chain, message included, to the
    screen. To see the text, catch the exception where it is raised and
    scrub it with what that code knows (the adapters do, for the
    ``RepoClientError`` they raise).
    """

    log = logger or get_logger()

    def wrapped(*args: Any, **kwargs: Any) -> T:
        base_ctx: dict[str, Any] = {
            "agent": agent_name,
            "run_id": run_id,
            "correlation_id": correlation_id,
        }
        _emit(log, logging.INFO, EVENT_AGENT_START, base_ctx)
        start = time.perf_counter()
        try:
            result = runner(*args, **kwargs)
        except Exception as exc:
            failure = exc
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
        else:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            end_ctx: dict[str, Any] = {
                **base_ctx,
                "duration_ms": duration_ms,
                "status": getattr(result, "status", None),
            }
            _emit(log, logging.INFO, EVENT_AGENT_END, end_ctx)
            return result
        # Outside the ``except`` block on purpose: a handler that fails inside it has the runner's
        # exception chained to its own, and ``logging`` prints the chain (message included).
        _emit(
            log,
            logging.ERROR,
            EVENT_AGENT_ERROR,
            {
                **base_ctx,
                "duration_ms": duration_ms,
                "error_type": _class_name(failure),
            },
        )
        raise failure

    return wrapped


__all__ = [
    "EVENT_AGENT_END",
    "EVENT_AGENT_ERROR",
    "EVENT_AGENT_START",
    "ORCHESTRATOR_LOGGER_NAME",
    "get_logger",
    "make_logged_runner",
]
