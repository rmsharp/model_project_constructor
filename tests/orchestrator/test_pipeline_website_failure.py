"""A website stage that raises is a recorded failure, so ``--resume`` makes no second project.

``BACKLOG.md``, *"A website stage that raises something other than a ``RepoClientError`` saves no
result"*. The website stage creates a project on the repository host and cannot undo it, so the
only thing standing between a failed run and a duplicate project is the saved
``RepoProjectResult.result.json``: ``determine_resume_point`` reads that one file and, when it is
there, tells the operator to delete it before retrying. A ``RepoClientError`` is turned into a
FAILED result by the agent. Anything else (a ``KeyError`` from a reply with no ``id``, a
``RecursionError``, an interrupt) used to leave the runner as an exception, before the save, and
the next ``--resume`` ran the whole stage again.

These tests drive ``run_pipeline`` with a runner that raises, so they hold whatever the exception
is and whichever runner raises it. ``tests/scripts/test_run_pipeline_website_crash_resume.py``
holds the same behaviour through the real script and a real socket.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from pydantic import BaseModel

from model_project_constructor.orchestrator import (
    CheckpointStore,
    PipelineConfig,
    determine_resume_point,
    run_pipeline,
)
from model_project_constructor.orchestrator.pipeline import WebsiteRunner
from model_project_constructor.schemas.v1.data import DataReport
from model_project_constructor.schemas.v1.intake import IntakeReport
from model_project_constructor.schemas.v1.repo import (
    GovernanceManifest,
    RepoProjectResult,
    RepoTarget,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"

#: What the saved reason says besides the exception's class name. The operator reads this before
#: deleting the result file to retry, so it must say what the retry risks.
MAY_EXIST = "the website stage may already have created a project on the repository host"

#: A message nothing may carry out of the exception: a token, a control code, a second line.
HOSTILE_MESSAGE = "glpat-SECRET9f3kQ7xZ2mW \x1b[2J\x07 sent to https://host.example/x\nsecond line"


class _NobodyHasHeardOfThisOne(Exception):
    """A class the orchestrator has no knowledge of, from a runner it has no knowledge of."""


EXCEPTIONS: list[pytest.ParameterSet] = [
    pytest.param(lambda: KeyError("id"), id="KeyError"),
    pytest.param(lambda: RecursionError(HOSTILE_MESSAGE), id="RecursionError"),
    pytest.param(lambda: TypeError(HOSTILE_MESSAGE), id="TypeError"),
    pytest.param(lambda: httpx.InvalidURL(HOSTILE_MESSAGE), id="InvalidURL"),
    pytest.param(lambda: ValueError(HOSTILE_MESSAGE), id="ValueError"),
    pytest.param(lambda: OSError(28, HOSTILE_MESSAGE), id="OSError"),
    pytest.param(lambda: _NobodyHasHeardOfThisOne(HOSTILE_MESSAGE), id="a-class-it-never-heard-of"),
]

#: What nothing the exception said may leave as: a token, the host's name, a second line, a
#: control code raw and as JSON writes one.
LEAKS = ("glpat-SECRET", "host.example", "second line", "\x1b", "\\u001b")

#: Class names no code would choose, which a class built at run time can have.
ODD_CLASS_NAMES: list[pytest.ParameterSet] = [
    pytest.param("Evil\x1b[2J\x07\nglpat-SECRET9f3kQ7xZ2mW", id="control-codes-and-a-token"),
    pytest.param("A" * 1_000_000, id="a-million-characters"),
    pytest.param("", id="empty"),
    pytest.param("Caf\u00e9Error", id="not-ascii"),
    pytest.param("not an identifier", id="spaces"),
    pytest.param("E" * 101, id="one-too-long"),
]

#: Not ``Exception`` subclasses: ``Ctrl-C`` and ``sys.exit()``. The run must still stop.
INTERRUPTS: list[pytest.ParameterSet] = [
    pytest.param(KeyboardInterrupt, id="KeyboardInterrupt"),
    pytest.param(SystemExit, id="SystemExit"),
]


def _intake() -> IntakeReport:
    return IntakeReport.model_validate_json((FIXTURE_DIR / "subrogation_intake.json").read_text())


def _data() -> DataReport:
    return DataReport.model_validate_json((FIXTURE_DIR / "sample_datareport.json").read_text())


def _config(tmp_path: Path, run_id: str) -> PipelineConfig:
    return PipelineConfig(
        run_id=run_id,
        repo_target=RepoTarget(
            host_url="https://fake.host.test",
            namespace="data-science/model-drafts",
            project_name_hint="subrogation_pilot",
            visibility="private",
        ),
        checkpoint_dir=tmp_path / "checkpoints",
    )


def _raising(error: BaseException) -> WebsiteRunner:
    def website(_i: IntakeReport, _d: DataReport, _t: RepoTarget) -> RepoProjectResult:
        raise error

    return website


def _recording(events: list[tuple[str, str]], runner: WebsiteRunner) -> WebsiteRunner:
    """``runner``, with the moment it is called noted among the store's saves."""

    def website(i: IntakeReport, d: DataReport, t: RepoTarget) -> RepoProjectResult:
        events.append(("run", "website"))
        return runner(i, d, t)

    return website


def _drive(
    config: PipelineConfig,
    website: WebsiteRunner,
    store: CheckpointStore | None = None,
):
    intake, data = _intake(), _data()
    return run_pipeline(
        config,
        intake_runner=lambda: intake,
        data_runner=lambda _request: data,
        website_runner=website,
        store=store,
    )


def _saved(config: PipelineConfig) -> RepoProjectResult:
    path = config.checkpoint_dir / config.run_id / "RepoProjectResult.result.json"
    return RepoProjectResult.model_validate_json(path.read_text())


def _resume_point(config: PipelineConfig) -> str:
    return determine_resume_point(CheckpointStore(config.checkpoint_dir), config.run_id)


def _name(error: BaseException) -> str:
    return type(error).__name__


def _assert_nothing_leaked(
    config: PipelineConfig,
    reason: str,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The exception's message is in no place the run wrote: the reason, the checkpoint
    directory, the screen or the log."""
    assert len(reason.splitlines()) == 1
    assert not any(ord(c) < 0x20 or 0x7F <= ord(c) <= 0x9F for c in reason)
    on_disk = "".join(
        path.read_text(errors="replace")
        for path in sorted(config.checkpoint_dir.rglob("*"))
        if path.is_file()
    )
    screen = capsys.readouterr()
    logged = caplog.text + "".join(record.getMessage() for record in caplog.records)
    for fragment in LEAKS:
        assert fragment not in reason
        assert fragment not in on_disk
        assert fragment not in screen.out + screen.err
        assert fragment not in logged


class _RecordingStore(CheckpointStore):
    """Records the order of ``save`` and ``save_result`` calls."""

    def __init__(self, base_dir: Path, events: list[tuple[str, str]]) -> None:
        super().__init__(base_dir)
        self._events = events

    def save(self, envelope):  # type: ignore[no-untyped-def,override]
        self._events.append(("save", envelope.payload_type))
        return super().save(envelope)

    def save_result(self, run_id: str, name: str, model: BaseModel):  # type: ignore[no-untyped-def]
        self._events.append(("save_result", name))
        return super().save_result(run_id, name, model)


class _FailingResultStore(CheckpointStore):
    """A store that cannot write the terminal result: the disk is full."""

    def save_result(self, run_id: str, name: str, model: BaseModel):  # type: ignore[no-untyped-def]
        raise OSError(28, "No space left on device")


class TestAnExceptionFromTheWebsiteRunner:
    @pytest.mark.parametrize("make_error", EXCEPTIONS)
    def test_halts_the_run_at_the_website_stage_with_a_failed_result(
        self, tmp_path: Path, make_error: Callable[[], BaseException]
    ) -> None:
        error = make_error()
        config = _config(tmp_path, "run_raises")
        result = _drive(config, _raising(error))

        assert result.status == "FAILED_AT_WEBSITE"
        assert result.project_result is not None
        assert result.project_result.status == "FAILED"
        assert result.failure_reason == result.project_result.failure_reason
        assert result.failure_reason == f"unexpected_error: {_name(error)} ({MAY_EXIST})"
        # What the stages before it produced is kept, as on every other halt.
        assert result.intake_report == _intake()
        assert result.data_request is not None
        assert result.data_report == _data()

    @pytest.mark.parametrize("make_error", EXCEPTIONS)
    def test_the_result_is_saved_so_resume_stops_instead_of_creating_a_second_project(
        self, tmp_path: Path, make_error: Callable[[], BaseException]
    ) -> None:
        config = _config(tmp_path, "run_resume")
        result = _drive(config, _raising(make_error()))

        assert _saved(config) == result.project_result
        assert _resume_point(config) == "already_complete"

    @pytest.mark.parametrize("make_error", EXCEPTIONS)
    def test_nothing_the_exception_said_reaches_the_result_the_disk_the_screen_or_the_log(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture,
        make_error: Callable[[], BaseException],
    ) -> None:
        caplog.set_level(logging.DEBUG)
        config = _config(tmp_path, "run_clean")
        result = _drive(config, _raising(make_error()))

        assert result.failure_reason is not None
        _assert_nothing_leaked(config, result.failure_reason, capsys, caplog)

    @pytest.mark.parametrize("class_name", ODD_CLASS_NAMES)
    def test_a_class_name_that_is_not_a_short_ascii_identifier_is_not_carried(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture,
        class_name: str,
    ) -> None:
        """A class created at run time can be named anything; the reason must not be."""
        caplog.set_level(logging.DEBUG)
        config = _config(tmp_path, "run_odd_name")
        result = _drive(config, _raising(type(class_name, (Exception,), {})(HOSTILE_MESSAGE)))

        assert result.failure_reason == f"unexpected_error: <unprintable> ({MAY_EXIST})"
        _assert_nothing_leaked(config, result.failure_reason, capsys, caplog)

    def test_a_class_name_of_exactly_the_longest_allowed_length_is_carried(
        self, tmp_path: Path
    ) -> None:
        name = "E" * 100
        config = _config(tmp_path, "run_longest_name")
        result = _drive(config, _raising(type(name, (Exception,), {})("x")))

        assert result.failure_reason == f"unexpected_error: {name} ({MAY_EXIST})"

    def test_the_saved_manifest_carries_the_intake_governance_not_a_default(
        self, tmp_path: Path
    ) -> None:
        config = _config(tmp_path, "run_governance")
        _drive(config, _raising(KeyError("id")))

        manifest = _saved(config).governance_manifest
        assert manifest.risk_tier == _intake().governance.risk_tier
        assert manifest.cycle_time == _intake().governance.cycle_time
        # The point of choosing a value that is not the default one.
        assert (manifest.risk_tier, manifest.cycle_time) != ("tier_4_low", "tactical")

    def test_the_repo_target_is_saved_before_the_runner_and_the_result_after_it(
        self, tmp_path: Path
    ) -> None:
        events: list[tuple[str, str]] = []
        config = _config(tmp_path, "run_order")
        _drive(
            config,
            _recording(events, _raising(KeyError("id"))),
            _RecordingStore(config.checkpoint_dir, events),
        )

        assert events.index(("save", "RepoTarget")) < events.index(("run", "website"))
        assert events.index(("run", "website")) < events.index(("save_result", "RepoProjectResult"))
        assert events.count(("save_result", "RepoProjectResult")) == 1

    def test_a_result_that_cannot_be_saved_is_not_hidden(self, tmp_path: Path) -> None:
        """If the file cannot be written, resume is unsafe and the run must say so loudly: the
        disk error surfaces. It is raised after the handler, so the exception that started it is
        not its context: a traceback would print that exception's message, and this stage keeps
        the message off the terminal (Session 274, learning 320)."""
        config = _config(tmp_path, "run_disk_full")
        store = _FailingResultStore(config.checkpoint_dir)
        with pytest.raises(OSError, match="No space left") as raised:
            _drive(config, _raising(KeyError(HOSTILE_MESSAGE)), store)

        assert raised.value.__context__ is None


class TestAnInterruptFromTheWebsiteRunner:
    @pytest.mark.parametrize("make_interrupt", INTERRUPTS)
    def test_stops_the_run_and_saves_a_failed_result_first(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture,
        make_interrupt: type[BaseException],
    ) -> None:
        caplog.set_level(logging.DEBUG)
        config = _config(tmp_path, "run_interrupt")
        with pytest.raises(make_interrupt):
            _drive(config, _raising(make_interrupt(HOSTILE_MESSAGE)))

        saved = _saved(config)
        assert saved.status == "FAILED"
        assert saved.failure_reason == f"interrupted: {make_interrupt.__name__} ({MAY_EXIST})"
        assert (saved.project_url, saved.project_id, saved.initial_commit_sha) == ("", "", "")
        assert saved.files_created == []
        assert _resume_point(config) == "already_complete"
        _assert_nothing_leaked(config, saved.failure_reason, capsys, caplog)

    def test_an_interrupt_whose_class_name_is_odd_is_saved_without_it(
        self, tmp_path: Path
    ) -> None:
        odd = type("Evil\x1b[2J\nglpat-SECRET", (BaseException,), {})
        config = _config(tmp_path, "run_odd_interrupt")
        with pytest.raises(odd):
            _drive(config, _raising(odd(HOSTILE_MESSAGE)))

        assert _saved(config).failure_reason == f"interrupted: <unprintable> ({MAY_EXIST})"

    @pytest.mark.parametrize("make_interrupt", INTERRUPTS)
    def test_the_interrupt_is_the_exception_that_leaves_not_a_replacement(
        self, tmp_path: Path, make_interrupt: type[BaseException]
    ) -> None:
        """Swallowing a ``Ctrl-C`` would let the pipeline carry on and exit 1 as if the operator
        had not pressed it; the same instance must come out."""
        config = _config(tmp_path, "run_same_instance")
        interrupt = make_interrupt()
        with pytest.raises(make_interrupt) as raised:
            _drive(config, _raising(interrupt))

        assert raised.value is interrupt

    @pytest.mark.parametrize("make_interrupt", INTERRUPTS)
    def test_the_result_is_saved_after_the_runner_and_exactly_once(
        self, tmp_path: Path, make_interrupt: type[BaseException]
    ) -> None:
        events: list[tuple[str, str]] = []
        config = _config(tmp_path, "run_interrupt_order")
        with pytest.raises(make_interrupt):
            _drive(
                config,
                _recording(events, _raising(make_interrupt())),
                _RecordingStore(config.checkpoint_dir, events),
            )

        assert events.index(("save", "RepoTarget")) < events.index(("run", "website"))
        assert events.index(("run", "website")) < events.index(("save_result", "RepoProjectResult"))
        assert events.count(("save_result", "RepoProjectResult")) == 1


    def test_a_result_that_cannot_be_saved_does_not_hide_the_interrupt_either(
        self, tmp_path: Path
    ) -> None:
        """Here the save runs inside the handler, so the disk error surfaces WITH the interrupt
        as its context: the operator who pressed Ctrl-C sees both, and the run still stops."""
        config = _config(tmp_path, "run_interrupt_disk_full")
        interrupt = KeyboardInterrupt()
        store = _FailingResultStore(config.checkpoint_dir)
        with pytest.raises(OSError, match="No space left") as raised:
            _drive(config, _raising(interrupt), store)

        assert raised.value.__context__ is interrupt


class TestWhatDoesNotChange:
    def test_a_runner_that_returns_a_failed_result_is_saved_as_it_returned_it(
        self, tmp_path: Path
    ) -> None:
        returned = RepoProjectResult(
            status="FAILED",
            project_url="https://fake.host.test/p",
            project_id="42",
            initial_commit_sha="",
            files_created=[],
            governance_manifest=GovernanceManifest(
                model_registry_entry={},
                artifacts_created=[],
                risk_tier="tier_2_high",
                cycle_time="strategic",
                regulatory_mapping={},
            ),
            failure_reason="repo_error: the runner's own words",
        )
        config = _config(tmp_path, "run_returns_failed")
        result = _drive(config, lambda _i, _d, _t: returned)

        assert result.status == "FAILED_AT_WEBSITE"
        assert result.failure_reason == "repo_error: the runner's own words"
        assert _saved(config) == returned

    def test_an_exception_before_the_website_stage_is_not_caught(self, tmp_path: Path) -> None:
        """Only the website stage has a side effect it cannot undo; the catch must not widen."""
        config = _config(tmp_path, "run_data_raises")
        intake = _intake()

        def data_runner(_request):  # type: ignore[no-untyped-def]
            raise KeyError("id")

        with pytest.raises(KeyError):
            run_pipeline(
                config,
                intake_runner=lambda: intake,
                data_runner=data_runner,
                website_runner=_raising(AssertionError("must not be reached")),
            )
        saved = config.checkpoint_dir / config.run_id / "RepoProjectResult.result.json"
        assert not saved.exists()

