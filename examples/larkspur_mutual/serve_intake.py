"""Serve the intake web UI keyless: the real app, with a scripted model behind it.

Run from the repository root::

    uv run python examples/larkspur_mutual/serve_intake.py

then open http://127.0.0.1:8000/ and play the stakeholder yourself: the answers
to type are the ``qa_pairs`` in ``intake_fixture.yaml``. No API key is read and
nothing leaves your machine. The questions, the draft and the governance block
are replayed from that file, not written by a model (see its header), so this
shows what the screens do, not what Claude would ask.

``drive_interview.py`` imports :func:`build_app` and plays the stakeholder over
real HTTP.
"""

from __future__ import annotations

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FIXTURE = HERE / "intake_fixture.yaml"

# Importing ``model_project_constructor.ui.intake`` builds its module-level default
# app, which opens INTAKE_DB_PATH (``./intake_sessions.db`` in the working
# directory when unset) as a side effect of the import alone. Point it into
# ``out/`` first, so this example leaves no stray database at the repository root.
OUT.mkdir(exist_ok=True)
os.environ.setdefault("INTAKE_DB_PATH", str(OUT / "unused_default_app.db"))

from fastapi import FastAPI  # noqa: E402

from model_project_constructor.agents.intake.fixture import (  # noqa: E402
    FixtureLLMClient,
    load_fixture,
)
from model_project_constructor.ui.intake import create_app  # noqa: E402


def build_app(db_path: Path) -> FastAPI:
    """The shipped intake app, with the fixture standing in for the language model."""
    fixture = load_fixture(FIXTURE)
    return create_app(
        llm_factory=lambda _session_id: FixtureLLMClient(fixture),
        db_path=db_path,
    )


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    app = build_app(OUT / "larkspur_intake.db")
    # 127.0.0.1 on purpose: the UI has no authentication of any kind.
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
