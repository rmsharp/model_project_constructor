"""Automated data-source discovery via ``information_schema`` reflection.

Reference producer for the data-source-inventory contract (plan §5.2). Given
a :class:`ReadOnlyDB`, walks the database's ``information_schema`` (via
SQLAlchemy's dialect-agnostic Inspector) and builds a
:class:`DataSourceInventory` with one :class:`DataSourceEntry` per
discovered table or view. The resulting JSON is a valid input for any
downstream consumer that accepts the contract.

Phase 2 scope per ``docs/architecture-history/data-source-inventory-contract-plan.md``:

- PostgreSQL + SQLite tested against fake DBs.
- Other dialects: SQLAlchemy inspector handles most. Anything that raises
  during reflection *or while an entry is built from it* surfaces as an empty
  inventory with ``ProducerMetadata.notes`` naming the error.
- Optional LLM ranking via the caller-supplied ``llm`` (opt-in through the
  ``--rank-with-llm`` CLI flag). When the ``llm`` object exposes a
  ``rank_candidate_tables`` method, discovery invokes it and assigns
  ``relevance_score`` / ``relevance_reason`` per entry; otherwise those
  fields stay ``None``. They also stay ``None`` when ranking **fails** — the
  reflected entries are kept and ``notes`` says the ranking failed.

The producer emits ``producer_type="automated"`` with a stable
``producer_id="information_schema_probe_v1"``.
"""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime
from typing import Any

from model_project_constructor_data_agent.db import ReadOnlyDB, redact_secrets
from model_project_constructor_data_agent.schemas import (
    ColumnMetadata,
    DataSourceEntry,
    DataSourceInventory,
    ProducerMetadata,
)

_LOG = logging.getLogger(__name__)

PRODUCER_ID = "information_schema_probe_v1"
PRODUCER_VERSION = "1.0"

#: How ``ProducerMetadata.notes`` begins for each degradation. The two must stay
#: distinguishable by text: an empty inventory and an unranked one are different
#: outcomes, and ``cli.discover`` — which exits non-zero on either (operator
#: ruling, Session 261) — tells the operator which. Compare with ``startswith``.
PROBE_FAILED_NOTE_PREFIX = "information_schema probe failed"
RANKING_FAILED_NOTE_PREFIX = "LLM relevance ranking failed"


class RankingMatchedNoEntryError(ValueError):
    """The ranker returned, but named no entry's ``fully_qualified_name`` exactly.

    Raised by :func:`_ranked`, so it becomes an ordinary ranking failure. The
    ranking note persists the exception's type only, so this name IS the
    note's explanation — which is why it is a class of its own.
    """


class InvalidRelevanceScoreError(ValueError):
    """A score the ranker applied to an entry is not a finite number in [0.0, 1.0].

    Rejected, never clamped (operator ruling, Session 264): a reply on the
    wrong scale would clamp to all 1.0 and lose the order ranking exists for.
    """


def _safe_message(e: Exception) -> str:
    """``str(e)`` made safe to log and to persist.

    Runs inside the ``except`` blocks that deliver "never raises", so it must
    not be a raise site itself. The whole body is guarded, not just ``str(e)``:
    a broken ``__str__`` raises there, and one returning a ``str`` *subclass*
    raises later, from that subclass's own ``encode`` / ``split`` (measured).

    Lone surrogates are scrubbed because a note holding one makes
    ``model_dump_json`` raise and the written file fail to reload (measured).
    An OS-raised ``OSError`` repr-escapes its filename, so it carries none; a
    message built by formatting an ``os.fsdecode``-d path into text does.

    Redaction is **best-effort**. :func:`db.redact_secrets` masks URL userinfo,
    a wide `key=value`/`key: value`/quoted/braced key list (Session 262), and
    a secret percent-encoded inside `odbc_connect=`; it still does not see a
    bare-key, header, ``Bearer``, or SigV4-signature shape with no `key=`/
    `key:` form at all, nor a key outside its fixed list. Flattened with the
    same idiom as ``agent.py`` so the WARNING is one log record: SQLAlchemy
    puts its help URL after a newline on every ``DBAPIError``.
    """
    try:
        raw = str(e).encode("utf-8", "replace").decode("utf-8")
        return " ".join(redact_secrets(raw).split())
    except Exception:
        return "<unprintable>"


def probe_information_schema(
    db: ReadOnlyDB,
    *,
    include_schemas: list[str] | None = None,
    llm: Any | None = None,
    request_context: str | None = None,
) -> DataSourceInventory:
    """Produce a :class:`DataSourceInventory` from a live database.

    Arguments:
        db: A connected :class:`ReadOnlyDB`. The caller owns the connection
            lifecycle — this function does not call ``connect`` or ``close``.
        include_schemas: Optional allow-list of schema names. When ``None``
            (default), every accessible schema except the system schemas
            (``information_schema``, ``pg_catalog``) is discovered.
        llm: Optional LLM client. If provided AND the object exposes a
            ``rank_candidate_tables`` method, the method is invoked with
            copies of the candidate entries and ``request_context``; the
            returned rankings populate ``DataSourceEntry.relevance_score`` and
            ``relevance_reason``. Clients that do not support ranking are
            ignored here (no error).
        request_context: Free-text description of what the request is about,
            fed to the LLM for relevance ranking. Unused when ``llm`` is
            ``None`` or does not support ranking.

    Returns a valid :class:`DataSourceInventory`. **No** ``Exception`` **raised
    by** ``db`` **or by** ``llm`` **escapes** — each stage degrades to a labelled
    result and logs one WARNING on this module's logger. Three limits, all
    measured: only ``Exception`` is absorbed, never ``KeyboardInterrupt`` /
    ``SystemExit``; a non-``str`` ``request_context`` still raises, because it is
    validated while the *result* is built (a bad ``db`` or ``include_schemas``
    does not — it surfaces as a probe failure); and an exception class hostile
    enough that reading its ``__name__`` raises is out of scope.

    - **Reflection, or building an entry from it, fails** (permission denied,
      unsupported dialect, a reflection dict missing a key, a table that fails
      schema validation or has a name that cannot be written as UTF-8):
      ``entries=[]`` and ``notes`` begins
      :data:`PROBE_FAILED_NOTE_PREFIX`, then the exception's type and its
      message — redacted best-effort, on one line. One bad table fails the
      whole probe: a partial inventory is never returned unlabelled.
    - **Ranking fails** (no credentials, a malformed or truncated reply, a
      ranking that fails schema validation, names no entry, applies a score that
      is not a finite number in [0.0, 1.0], or carries a reason that cannot be
      written as UTF-8): the reflected entries are **kept,
      all unranked** — ranking is applied all-or-nothing — and ``notes`` begins
      :data:`RANKING_FAILED_NOTE_PREFIX` and names the exception's **type
      only**. The message goes to the WARNING and is never persisted: the
      inventory is published downstream, and an LLM-side error can carry a
      gateway's echo of a header or an environment variable in shapes no
      redactor here can see (measured Session 261).

    ``notes`` is ``None`` exactly when neither happened. That is **not** the
    same as "every entry is ranked": a partial ranking is legal, so an entry the
    ranker returns no ranking for keeps ``relevance_score=None``. When a ranker
    ran, it does mean at least one entry is ranked (Session 264), and every
    applied score is a finite number in [0.0, 1.0].

    Why there is no upper bound on what is absorbed, when the sibling
    ``db.sql_dialect_from_url`` deliberately has one: that function degrades to
    a bare ``None``, so an unexpected error must stay loud; this one's degraded
    result says what happened, in the artifact and on stderr.
    """
    produced_at = datetime.now(UTC)

    def _inventory(entries: list[DataSourceEntry], notes: str | None) -> DataSourceInventory:
        return DataSourceInventory(
            entries=entries,
            producers=[
                ProducerMetadata(
                    producer_id=PRODUCER_ID,
                    producer_type="automated",
                    produced_at=produced_at,
                    producer_version=PRODUCER_VERSION,
                    notes=notes,
                )
            ],
            created_at=produced_at,
            request_context=request_context,
        )

    try:
        tables = db.get_information_schema(schemas=include_schemas)
        entries = [_entry_from_reflection(t) for t in tables]
        for entry in entries:
            # A lone surrogate in a reflected name validates as a ``str`` but
            # cannot be written as UTF-8: the file would be written and then fail
            # to reload. Checked HERE so it is blamed on reflection, not ranking.
            entry.model_dump_json()
    except Exception as e:
        cause = f"{type(e).__name__}: {_safe_message(e)}"
        _LOG.warning(
            "probe_information_schema: reflection failed; returning an EMPTY inventory: %s",
            cause,
        )
        return _inventory([], f"{PROBE_FAILED_NOTE_PREFIX}: {cause}")

    notes: str | None = None
    if llm is not None and entries:
        try:
            # Looked up INSIDE the try: ``hasattr`` swallows only AttributeError,
            # so a lazy client whose property raises would escape from the ``if``.
            ranker = getattr(llm, "rank_candidate_tables", None)
            if ranker is not None:
                entries = _ranked(entries, ranker, request_context)
        except Exception as e:
            type_name = type(e).__name__
            _LOG.warning(
                "probe_information_schema: LLM relevance ranking failed; returning "
                "%d entries UNRANKED: %s: %s",
                len(entries),
                type_name,
                _safe_message(e),
            )
            notes = (
                f"{RANKING_FAILED_NOTE_PREFIX} ({type_name}); all {len(entries)} "
                "entries are unranked. The cause was logged as a WARNING when "
                "this inventory was produced."
            )

    return _inventory(entries, notes)


def _ranked(
    entries: list[DataSourceEntry], ranker: Any, request_context: str | None
) -> list[DataSourceEntry]:
    """Return NEW entries carrying the ranker's scores — or raise, changing nothing.

    All-or-nothing is the contract the caller's note depends on ("all N entries
    are unranked"), and two things deliver it. The ranker gets deep copies, so
    one that scores in place and then fails cannot half-rank the real entries.
    And the result is built completely before the caller assigns it.

    Each entry is rebuilt through ``model_validate`` **from a dict**.
    ``model_copy(update=...)`` skips validation, and so does
    ``model_validate(<instance>)`` — pydantic's ``revalidate_instances`` defaults
    to ``"never"`` — so either would let a duck-typed client's
    ``relevance_score="high"`` into an inventory that then fails to reload.

    Three rankings return normally and are still failures (Session 264), each
    of which used to leave ``notes=None``: one that names **no** entry
    (:class:`RankingMatchedNoEntryError` — a partial ranking stays legal, and a
    name matching no entry is ignored); a score, on an entry it is applied to,
    that is not a finite number in [0.0, 1.0] (:class:`InvalidRelevanceScoreError`);
    and a reason that cannot be written as UTF-8 (pydantic's serialization
    error), which would otherwise write a file that fails to reload.
    """
    rankings = ranker(
        entries=[e.model_copy(deep=True) for e in entries],
        request_context=request_context,
    )
    ranking_map = {
        r.fully_qualified_name: (r.relevance_score, r.relevance_reason) for r in rankings
    }
    if not any(e.fully_qualified_name in ranking_map for e in entries):
        raise RankingMatchedNoEntryError(
            f"{len(ranking_map)} distinct name(s) returned and none is an entry's "
            f"fully_qualified_name exactly; returned {list(ranking_map)[:3]!r}, "
            f"expected names like {[e.fully_qualified_name for e in entries[:3]]!r}"
        )
    ranked: list[DataSourceEntry] = []
    for entry in entries:
        score, reason = ranking_map.get(entry.fully_qualified_name, (None, None))
        rebuilt = DataSourceEntry.model_validate(
            {**entry.model_dump(), "relevance_score": score, "relevance_reason": reason}
        )
        if entry.fully_qualified_name in ranking_map:
            # Checked AFTER validation, so the score is a float (or None) by now.
            applied = rebuilt.relevance_score
            if applied is None or not (math.isfinite(applied) and 0.0 <= applied <= 1.0):
                raise InvalidRelevanceScoreError(
                    f"relevance_score {applied!r} for {entry.fully_qualified_name!r} "
                    "is not a finite number in [0.0, 1.0]"
                )
            rebuilt.model_dump_json()  # a lone surrogate in the reason raises here
        ranked.append(rebuilt)
    return ranked


def _entry_from_reflection(table: dict[str, Any]) -> DataSourceEntry:
    namespace = table.get("namespace")
    name = table["name"]
    fqn = f"{namespace}.{name}" if namespace else name

    columns = [
        ColumnMetadata(
            name=c["name"],
            data_type=c["data_type"],
            nullable=c.get("nullable"),
            is_primary_key=bool(c.get("is_primary_key", False)),
            is_foreign_key=bool(c.get("is_foreign_key", False)),
            foreign_key_target=c.get("foreign_key_target"),
        )
        for c in table.get("columns", [])
    ]

    return DataSourceEntry(
        name=name,
        namespace=namespace,
        fully_qualified_name=fqn,
        entity_kind=table["entity_kind"],
        columns=columns,
        primary_key_columns=list(table.get("primary_key_columns", [])),
        producer_id=PRODUCER_ID,
    )
