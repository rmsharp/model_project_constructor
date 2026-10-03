"""``agent.error`` names the exception's class and never what it said.

Session 276, closing the ``BACKLOG.md`` item *"The run log records the full text of any exception a
runner raises"* (see ``CHANGELOG.md``). ``make_logged_runner`` used to put ``str(exc)`` in the
event's ``context``. Python's default handler does not print a record's ``context``, but the JSON
formatter ``OPERATIONS.md`` section 3.1 recommends does, and an exception can say anything the
repository host, a database driver or a model's client said to it: ``httpx.InvalidURL`` quotes the
URL it refused, and a host that echoes the access token as a project id puts the token in that
URL. A redaction that needs no secret cannot find a bare token, so the message is not carried at
all, and the exception's own text is never read.

These tests render the record the way the worst formatter would (every attribute of it, the
traceback if one is attached, JSON-escaped as a real one escapes) and look for what the exception
said. ``tests/orchestrator/test_logging.py`` holds the ordinary behaviour of the wrapper.
"""

from __future__ import annotations

import json
import logging
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest

from model_project_constructor.orchestrator import (
    CheckpointStore,
    MetricsRegistry,
    PipelineConfig,
    make_logged_runner,
    make_measured_runner,
    run_pipeline,
)
from model_project_constructor.orchestrator.logging import (
    EVENT_AGENT_ERROR,
    ORCHESTRATOR_LOGGER_NAME,
)
from model_project_constructor.orchestrator.pipeline import _website_failure
from model_project_constructor.schemas.v1.data import DataReport
from model_project_constructor.schemas.v1.intake import IntakeReport
from model_project_constructor.schemas.v1.repo import RepoProjectResult, RepoTarget

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"

TOKEN = "glpat-SECRET9f3kQ7xZ2mW"

#: A message nothing may carry out of the exception: a token, a host, a second line, a control code.
HOSTILE = f"{TOKEN} \x1b[2J\x07 sent to https://host.example/x\nsecond line"

#: What none of the log's output may contain: raw, and as a JSON writer escapes a control code.
LEAKS = (TOKEN, "host.example", "second line", "\x1b", "\\u001b")

#: Exactly the fields an ``agent.error`` context may carry.
ERROR_FIELDS = {"agent", "run_id", "correlation_id", "duration_ms", "error_type"}


class _SaysItself(Exception):
    """An exception whose text, repr and arguments are all the hostile message."""

    def __init__(self) -> None:
        super().__init__(HOSTILE)

    def __str__(self) -> str:
        return HOSTILE

    def __repr__(self) -> str:
        return HOSTILE


class _CannotBePrinted(Exception):
    """An exception that fails when anything asks it for its text."""

    def __str__(self) -> str:
        raise AssertionError("the wrapper read the exception's message")

    def __repr__(self) -> str:
        raise AssertionError("the wrapper read the exception's repr")


class _Enormous(Exception):
    """An exception whose text is two million characters."""

    def __str__(self) -> str:
        return HOSTILE + "x" * 2_000_000


def _chained() -> BaseException:
    error = RuntimeError("outer")
    error.__cause__ = ValueError(HOSTILE)
    return error


def _in_context() -> BaseException:
    error = RuntimeError("outer")
    error.__context__ = ValueError(HOSTILE)
    return error


#: Every way an exception can hold text, and one that holds none of it where ``str`` looks.
EXCEPTIONS: list[pytest.ParameterSet] = [
    pytest.param(lambda: RuntimeError(HOSTILE), id="RuntimeError"),
    pytest.param(lambda: KeyError(HOSTILE), id="KeyError"),
    pytest.param(
        lambda: httpx.InvalidURL(f"Invalid non-printable ASCII character in URL, {HOSTILE!r}"),
        id="InvalidURL-quoting-the-url",
    ),
    pytest.param(lambda: OSError(2, HOSTILE, HOSTILE), id="OSError-with-a-filename"),
    pytest.param(
        lambda: UnicodeDecodeError("utf-8", HOSTILE.encode(), 0, 1, HOSTILE),
        id="UnicodeDecodeError",
    ),
    pytest.param(
        lambda: subprocess.CalledProcessError(
            1, ["opencode", HOSTILE], output=HOSTILE, stderr=HOSTILE
        ),
        id="CalledProcessError",
    ),
    pytest.param(lambda: ExceptionGroup("group", [ValueError(HOSTILE)]), id="ExceptionGroup"),
    pytest.param(_chained, id="the-text-is-in-the-cause"),
    pytest.param(_in_context, id="the-text-is-in-the-context"),
    pytest.param(_SaysItself, id="text-repr-and-args-all-hostile"),
]

#: Class names no code would choose, which a class built at run time can have.
ODD_CLASS_NAMES: list[pytest.ParameterSet] = [
    pytest.param(f"Evil\x1b[2J\x07\n{TOKEN}", id="control-codes-and-a-token"),
    pytest.param("A" * 1_000_000, id="a-million-characters"),
    pytest.param("", id="empty"),
    pytest.param("CaféError", id="not-ascii"),
    pytest.param("not an identifier", id="spaces"),
    pytest.param("E" * 101, id="one-too-long"),
]


class _RendersEverything(logging.Formatter):
    """A JSON formatter as thorough as the worst one a deployment could install.

    ``OPERATIONS.md`` section 3.1 recommends ``python-json-logger``, which writes every field of
    the record and the ``context`` extra. This one writes every attribute the record has, and the
    traceback when one is attached, so a fragment of the exception's text anywhere on the record
    (the context, the arguments, the exception itself) comes out.
    """

    def format(self, record: logging.LogRecord) -> str:
        fields = dict(vars(record))
        fields["message"] = record.getMessage()
        if record.exc_info:
            fields["traceback"] = self.formatException(record.exc_info)
        return json.dumps(fields, default=repr)


class _Capture:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.records: list[logging.LogRecord] = []

    @property
    def rendered(self) -> str:
        return "\n".join(self.lines)

    def error_records(self) -> list[logging.LogRecord]:
        return [r for r in self.records if r.getMessage() == EVENT_AGENT_ERROR]

    def error_context(self) -> dict:
        (record,) = self.error_records()
        return record.context  # type: ignore[attr-defined,no-any-return]


@pytest.fixture
def log() -> Iterator[_Capture]:
    """The documented recipe: a JSON formatter on ``model_project_constructor.orchestrator``."""
    capture = _Capture()

    class _Handler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            capture.records.append(record)
            capture.lines.append(self.format(record))

    handler = _Handler()
    handler.setFormatter(_RendersEverything())
    logger = logging.getLogger(ORCHESTRATOR_LOGGER_NAME)
    previous = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        yield capture
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous)


def _raising(error: BaseException) -> Callable[[], None]:
    def runner() -> None:
        raise error

    return runner


def _wrap(error: BaseException, name: str = "website"):
    return make_logged_runner(
        _raising(error), agent_name=name, run_id="run_276", correlation_id="corr_276"
    )


def _nothing_leaked(text: str) -> None:
    for fragment in LEAKS:
        assert fragment not in text


class TestWhatTheErrorEventCarries:
    def test_the_context_is_the_five_fields_and_no_message(self, log: _Capture) -> None:
        with pytest.raises(RuntimeError):
            _wrap(RuntimeError("boom"))()
        context = log.error_context()
        assert set(context) == ERROR_FIELDS
        assert "error_message" not in context
        assert context["error_type"] == "RuntimeError"
        assert context["agent"] == "website"
        assert isinstance(context["duration_ms"], float)

    @pytest.mark.parametrize("make", EXCEPTIONS)
    def test_nothing_the_exception_said_is_rendered(
        self, log: _Capture, make: Callable[[], BaseException]
    ) -> None:
        error = make()
        with pytest.raises(type(error)) as raised:
            _wrap(error)()
        assert raised.value is error  # the original, unchanged, still propagates
        assert log.error_context().keys() == ERROR_FIELDS
        _nothing_leaked(log.rendered)

    @pytest.mark.parametrize("make", EXCEPTIONS)
    def test_the_record_carries_no_exception_object_or_traceback(
        self, log: _Capture, make: Callable[[], BaseException]
    ) -> None:
        """A formatter that prints ``exc_info`` prints the exception's message, and its chain."""
        error = make()
        with pytest.raises(type(error)):
            _wrap(error)()
        (record,) = log.error_records()
        assert record.exc_info is None
        assert record.exc_text is None
        assert record.stack_info is None
        assert record.args in ((), None)
        assert record.getMessage() == EVENT_AGENT_ERROR


class TestTheMessageIsNeverRead:
    def test_an_exception_that_cannot_print_still_propagates_unchanged(
        self, log: _Capture
    ) -> None:
        """Reading the text inside the ``except`` block replaced the runner's exception with
        whatever the text's own code raised."""
        error = _CannotBePrinted()
        with pytest.raises(_CannotBePrinted) as raised:
            _wrap(error)()
        assert raised.value is error
        assert log.error_context()["error_type"] == "_CannotBePrinted"

    def test_two_million_characters_of_message_are_not_in_the_log(self, log: _Capture) -> None:
        with pytest.raises(_Enormous):
            _wrap(_Enormous())()
        assert len(log.rendered) < 5_000
        _nothing_leaked(log.rendered)


class TestTheClassName:
    def test_an_ordinary_class_name_is_carried(self, log: _Capture) -> None:
        class RepoClientError(Exception):
            pass

        with pytest.raises(RepoClientError):
            _wrap(RepoClientError(HOSTILE))()
        assert log.error_context()["error_type"] == "RepoClientError"

    @pytest.mark.parametrize("name", ODD_CLASS_NAMES)
    def test_a_class_name_that_is_not_a_short_identifier_is_replaced(
        self, log: _Capture, name: str
    ) -> None:
        odd = type(name, (Exception,), {})
        with pytest.raises(odd):
            _wrap(odd(HOSTILE))()
        assert log.error_context()["error_type"] == "<unprintable>"
        assert len(log.rendered) < 5_000
        _nothing_leaked(log.rendered)
        assert "Caf" not in log.rendered
        assert "AAAA" not in log.rendered

    def test_the_longest_name_carried_is_one_hundred_characters(self, log: _Capture) -> None:
        longest = type("E" * 100, (Exception,), {})
        with pytest.raises(longest):
            _wrap(longest())()
        assert log.error_context()["error_type"] == "E" * 100

    @pytest.mark.parametrize(
        "name",
        [pytest.param(p.values[0], id=p.id) for p in ODD_CLASS_NAMES] + ["KeyError", "E" * 100],
    )
    def test_it_is_the_name_the_website_stage_saves(self, log: _Capture, name: str) -> None:
        """Two copies of one rule: the log's and ``_website_failure``'s agree on every class."""
        error = type(name, (Exception,), {})(HOSTILE)
        saved = _website_failure(_intake(), "unexpected_error", error).failure_reason
        saved_name = saved.removeprefix("unexpected_error: ").split(" (", 1)[0]
        with pytest.raises(type(error)):
            _wrap(error)()
        assert log.error_context()["error_type"] == saved_name


class TestThePipelineAsTheScriptBuildsIt:
    """``scripts/run_pipeline.py`` wraps a runner in ``make_measured_runner`` and then
    ``make_logged_runner``; the website stage's crash is saved by the orchestrator (Session 275)."""

    @pytest.mark.parametrize("make", EXCEPTIONS)
    def test_a_crash_in_the_website_stage_is_logged_by_class_and_saved_as_failed(
        self, log: _Capture, tmp_path: Path, make: Callable[[], BaseException]
    ) -> None:
        error = make()
        metrics = MetricsRegistry()
        website = make_logged_runner(
            make_measured_runner(_website_raising(error), agent_name="website", registry=metrics),
            agent_name="website",
            run_id="run_276",
            correlation_id="corr_276",
        )
        config = PipelineConfig(
            run_id="run_276",
            repo_target=RepoTarget(
                host_url="https://fake.host.test",
                namespace="data-science/model-drafts",
                project_name_hint="subrogation_pilot",
                visibility="private",
            ),
            checkpoint_dir=tmp_path / "checkpoints",
        )
        intake, data = _intake(), _data()
        result = run_pipeline(
            config,
            intake_runner=lambda: intake,
            data_runner=lambda _request: data,
            website_runner=website,
            store=CheckpointStore(config.checkpoint_dir),
        )
        assert result.status == "FAILED_AT_WEBSITE"
        saved = (config.checkpoint_dir / "run_276" / "RepoProjectResult.result.json").read_text()
        assert RepoProjectResult.model_validate_json(saved).status == "FAILED"
        assert log.error_context()["error_type"] == type(error).__name__
        _nothing_leaked(log.rendered)
        _nothing_leaked(saved)


def _intake() -> IntakeReport:
    return IntakeReport.model_validate_json((FIXTURE_DIR / "subrogation_intake.json").read_text())


def _data() -> DataReport:
    return DataReport.model_validate_json((FIXTURE_DIR / "sample_datareport.json").read_text())


def _website_raising(error: BaseException) -> Callable[..., RepoProjectResult]:
    def website(_i: IntakeReport, _d: DataReport, _t: RepoTarget) -> RepoProjectResult:
        raise error

    return website
