"""``agent.error`` names the exception's class and never what it said.

Session 276, closing the ``BACKLOG.md`` item *"The run log records the full text of any exception a
runner raises"* (see ``CHANGELOG.md``). ``make_logged_runner`` used to put ``str(exc)`` in the
event's ``context``. Python's default handler does not print a record's ``context``, but the JSON
formatter ``OPERATIONS.md`` section 3.1 recommends does, and an exception says whatever the code
that raised it put in it: a pydantic ``ValidationError`` quotes the input it refused
(``input_value='...'``), ``httpx.InvalidURL`` quotes a host or a port it refused, a database driver
may echo the connection back, and a gateway's error page can echo a header. (``httpx`` does NOT
quote a project id placed in the URL *path*: the message names the control character and its
position. The first draft of this change, and Session 275's end-to-end case, assumed it did; the
review measured otherwise on httpx 0.28.1 and 0.27.0, and ``TestTheRealExceptionsHoldTheToken``
pins the cases that are real.) A redaction that needs no secret cannot find a bare token, so the
message is not carried at all, and the exception's own text is never read.

A leak is any channel, not only the record the wrapper emits (learning #329): the fixture below
collects every record on every logger at ``DEBUG`` and, when the test ends, checks the screen
(file descriptors 1 and 2) and the warnings for what the exception said.

These tests render the record the way the worst formatter would (every attribute of it, the
traceback if one is attached, JSON-escaped as a real one escapes) and look for what the exception
said. ``tests/orchestrator/test_logging.py`` holds the ordinary behaviour of the wrapper.
"""

from __future__ import annotations

import json
import logging
import subprocess
import traceback
import warnings
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest
from pydantic import TypeAdapter, ValidationError

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

#: What none of the output may contain. A JSON writer escapes a control code (``\\u001b``) and the
#: screen does not (``\x1b``), so each form is listed for the channel that would carry it.
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


def _real_validation_error() -> ValidationError:
    """What a model parse of a reply says: pydantic quotes the input it refused."""
    try:
        TypeAdapter(int).validate_python(HOSTILE)
    except ValidationError as error:
        return error
    raise AssertionError("pydantic accepted the input")


def _real_invalid_port() -> httpx.InvalidURL:
    """What ``httpx`` says about a refused port: it quotes the port."""
    try:
        httpx.URL(f"https://host:{TOKEN}/x")
    except httpx.InvalidURL as error:
        return error
    raise AssertionError("httpx accepted the URL")


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
    pytest.param(_real_validation_error, id="real-pydantic-ValidationError"),
    pytest.param(_real_invalid_port, id="real-httpx-InvalidURL-for-a-port"),
    pytest.param(
        lambda: httpx.InvalidURL(f"a hand-built message: {HOSTILE!r}"),
        id="InvalidURL-with-a-hand-built-message",
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
def log(capfd: pytest.CaptureFixture[str]) -> Iterator[_Capture]:
    """A JSON formatter on EVERY logger, at ``DEBUG``, and a check of the screen at the end.

    ``OPERATIONS.md`` section 3.1 puts the formatter on ``model_project_constructor.orchestrator``;
    this puts it on the root logger, which that logger propagates to, so a record sent through any
    other logger or at any level is collected too. A fixture that watched only the orchestrator
    logger at ``INFO`` let five mutants through (a ``DEBUG`` companion record, the root logger,
    ``sys.stderr``, ``warnings.warn``, ``traceback.print_exc``). When the test ends, what reached
    file descriptors 1 and 2 and what was warned are searched for what the exception said, so a
    channel nobody thought to assert on is still checked.
    """
    capture = _Capture()

    class _Handler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            capture.records.append(record)
            capture.lines.append(self.format(record))

    handler = _Handler()
    handler.setFormatter(_RendersEverything())
    root = logging.getLogger()
    orchestrator = logging.getLogger(ORCHESTRATOR_LOGGER_NAME)
    previous = (root.level, orchestrator.level)
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    orchestrator.setLevel(logging.DEBUG)
    with warnings.catch_warnings(record=True) as warned:
        warnings.simplefilter("always")
        try:
            yield capture
        finally:
            root.removeHandler(handler)
            root.setLevel(previous[0])
            orchestrator.setLevel(previous[1])
    screen = capfd.readouterr()
    _nothing_leaked(screen.out + screen.err)
    _nothing_leaked("".join(str(w.message) for w in warned))


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


class TestTheOriginalExceptionIsUnchanged:
    """The event is emitted outside the ``except`` block, so the exception is re-raised by name
    and not by a bare ``raise``; nothing about it may change on the way out."""

    def test_its_explicit_cause_is_left_as_it_was(self, log: _Capture) -> None:
        cause = ValueError("inner")
        error = RuntimeError("outer")
        error.__cause__ = cause
        with pytest.raises(RuntimeError) as raised:
            _wrap(error)()
        assert raised.value.__cause__ is cause
        assert raised.value.__suppress_context__ is True  # what ``raise ... from cause`` sets

    def test_its_implicit_context_is_left_as_it_was(self, log: _Capture) -> None:
        earlier = KeyError("earlier")
        error = RuntimeError("outer")
        error.__context__ = earlier
        with pytest.raises(RuntimeError) as raised:
            _wrap(error)()
        assert raised.value.__context__ is earlier
        assert raised.value.__cause__ is None
        assert raised.value.__suppress_context__ is False

    def test_its_traceback_still_reaches_the_runner(self, log: _Capture) -> None:
        with pytest.raises(RuntimeError) as raised:
            _wrap(RuntimeError("x"))()
        frames = [f.name for f in traceback.extract_tb(raised.value.__traceback__)]
        assert "runner" in frames  # the function that raised it, not only the wrapper


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
        if name:
            # JSON-escaped, as the formatter wrote it; a prefix long enough that no checkout path
            # (the record carries the path of ``logging.py``) can contain it by accident.
            assert json.dumps(name)[1:51] not in log.rendered

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


class _NameThatRaises(type):
    @property
    def __name__(cls) -> str:  # type: ignore[override]
        raise RuntimeError("the class name cannot be read")


class _HostileText(str):
    """A ``str`` that answers the class-name guard's questions as a plain identifier would."""

    def isascii(self) -> bool:
        return True

    def isidentifier(self) -> bool:
        return True

    def __len__(self) -> int:
        return 5


class _NameThatIsAHostileStr(type):
    @property
    def __name__(cls) -> str:  # type: ignore[override]
        return _HostileText(f"\x1b[2J{TOKEN}")


def _caught(error: BaseException) -> BaseException | None:
    """What the wrapped runner raised. ``pytest.raises`` is not used for these classes: pytest
    formats a failure with ``type.__name__``, which is the property under test, and crashes with
    an ``INTERNALERROR`` instead of reporting the failure."""
    try:
        _wrap(error)()
    except BaseException as caught:
        return caught
    return None


class TestAClassWhoseNameCannotBeTrusted:
    """The class name is read by the wrapper, so reading it must not be a raise site, and a
    ``str`` subclass must not answer the guard's questions for it."""

    def test_a_name_that_raises_does_not_replace_the_runners_exception(
        self, log: _Capture
    ) -> None:
        class Odd(Exception, metaclass=_NameThatRaises):
            pass

        error = Odd(HOSTILE)
        assert _caught(error) is error
        assert log.error_context()["error_type"] == "<unprintable>"

    def test_a_name_that_is_a_str_subclass_is_replaced(self, log: _Capture) -> None:
        class Odd(Exception, metaclass=_NameThatIsAHostileStr):
            pass

        error = Odd(HOSTILE)
        assert _caught(error) is error
        assert log.error_context()["error_type"] == "<unprintable>"
        _nothing_leaked(log.rendered)


class TestAFailingLogSink:
    """When a handler cannot write, ``logging`` prints the failure to the screen, with the
    exception being handled chained to it. Emitting from inside the ``except`` block put the
    runner's exception in that chain, message and all (found by the Session 276 review)."""

    def test_a_handler_that_cannot_write_does_not_print_the_exception(
        self, log: _Capture, capfd: pytest.CaptureFixture[str]
    ) -> None:
        class _DeadStream:
            def write(self, _text: str) -> None:
                raise ValueError("the sink is down")

            def flush(self) -> None:
                pass

        sink = logging.StreamHandler(_DeadStream())
        logger = logging.getLogger(ORCHESTRATOR_LOGGER_NAME)
        logger.addHandler(sink)
        error = RuntimeError(HOSTILE)
        try:
            with pytest.raises(RuntimeError) as raised:
                _wrap(error)()
        finally:
            logger.removeHandler(sink)
        assert raised.value is error
        screen = capfd.readouterr().err
        assert "Logging error" in screen  # the sink did fail, and logging said so
        assert "the sink is down" in screen
        _nothing_leaked(screen)


class TestTheCaptureReachesWhatItGuards:
    def test_it_collects_debug_records_on_any_logger(self, log: _Capture) -> None:
        logging.getLogger("some.other.logger").debug("elsewhere")
        logging.getLogger(ORCHESTRATOR_LOGGER_NAME).debug("detail")
        assert [r.getMessage() for r in log.records] == ["elsewhere", "detail"]

    def test_it_renders_what_it_collects(self, log: _Capture) -> None:
        logging.getLogger("some.other.logger").warning("%s", TOKEN)
        assert TOKEN in log.rendered


class TestTheRealExceptionsHoldTheToken:
    """The premise of the real-exception cases above, so a library release that stops quoting
    fails here with a clear name instead of making them pass vacuously."""

    def test_pydantic_quotes_the_input_it_refused(self) -> None:
        assert TOKEN in str(_real_validation_error())

    def test_httpx_quotes_a_port_it_refused(self) -> None:
        assert TOKEN in str(_real_invalid_port())

    def test_httpx_does_not_quote_a_path(self) -> None:
        """What the first draft of this change assumed, and Session 275's end-to-end case: it is
        not so, on httpx 0.28.1 or 0.27.0."""
        with pytest.raises(httpx.InvalidURL) as raised:
            httpx.URL(f"https://host/api/v4/projects/{TOKEN}\x07 x/repository/commits")
        assert TOKEN not in str(raised.value)


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
