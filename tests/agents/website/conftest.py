"""Shared fixtures for website agent tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from model_project_constructor.agents.website.fake_client import FakeRepoClient
from model_project_constructor.schemas.v1.data import DataReport
from model_project_constructor.schemas.v1.intake import IntakeReport
from model_project_constructor.schemas.v1.repo import RepoTarget
from tests.agents.website.loopback import PROXY_VARIABLES, Loopback, serving

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.fixture(scope="module")
def loopback() -> Iterator[Loopback]:
    """A real socket on 127.0.0.1, with the environment's proxies set aside.

    ``httpx.Client`` honours ``HTTP_PROXY`` and its siblings, which is the normal setup on an
    enterprise machine: without this the requests go to the proxy and a test about a header
    value fails with a ``ConnectError``. The child of a subprocess test inherits the same
    environment, so it is covered too.
    """
    with pytest.MonkeyPatch.context() as env, serving() as server:
        for name in PROXY_VARIABLES:
            env.delenv(name, raising=False)
        env.setenv("NO_PROXY", "127.0.0.1")
        env.setenv("no_proxy", "127.0.0.1")
        yield server


@pytest.fixture
def intake_report_path() -> Path:
    return FIXTURES_DIR / "subrogation_intake.json"


@pytest.fixture
def data_report_path() -> Path:
    return FIXTURES_DIR / "sample_datareport.json"


@pytest.fixture
def intake_report(intake_report_path: Path) -> IntakeReport:
    return IntakeReport.model_validate_json(intake_report_path.read_text())


@pytest.fixture
def data_report(data_report_path: Path) -> DataReport:
    return DataReport.model_validate_json(data_report_path.read_text())


@pytest.fixture
def repo_target() -> RepoTarget:
    return RepoTarget(
        host_url="https://gitlab.example.com",
        namespace="data-science/model-drafts",
        project_name_hint="Subrogation Recovery Model",
        visibility="private",
    )


@pytest.fixture
def fake_client() -> FakeRepoClient:
    return FakeRepoClient()
