"""A report name never chooses the path of a file (BACKLOG (7)(a), Session 296).

The real ``WebsiteAgent`` runs on a client that refuses what a git tree, a checkout or a host
would (``path_checks``), with the names of ``PATH_NAMES`` as primary query names and as check
names. Before ``_file_stems`` Session 296's scouts ran this and saw: a datasheet written over
``governance/model_card.md`` while the generated project's own check said "0 problems"; a check
named ``../../primary/beta`` written over a primary query; two queries of one name written as one
file; ``Foo`` and ``foo`` as two entries in a commit and one file on macOS; a name of 243 to
251 characters that made the generated governance check crash (a name of 252 or more could not
be written to disk at all, and the old check then reported no problem for the tree it was given).
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from model_project_constructor.agents.website import _governance_check as gc
from model_project_constructor.agents.website.agent import WebsiteAgent
from model_project_constructor.agents.website.governance_templates import render_datasheet
from model_project_constructor.agents.website.graph import build_website_graph
from model_project_constructor.agents.website.protocol import RepoClientError
from model_project_constructor.agents.website.templates import (
    derive_project_name,
    derive_project_slug,
    render_primary_query_files,
    render_quality_check_files,
)
from model_project_constructor.schemas.v1.data import DataReport
from model_project_constructor.schemas.v1.intake import IntakeReport
from model_project_constructor.schemas.v1.repo import RepoProjectResult, RepoTarget
from tests.agents.website.hostile_names import PATH_NAMES_FOR_THE_AGENT
from tests.agents.website.path_checks import (
    PathCheckingRepoClient,
    collision,
    unsafe_reason,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
E_ACUTE = chr(0xE9)  # a precomposed letter; its decomposed twin is the letter and the mark below
COMBINING_ACUTE = chr(0x301)
LONE_SURROGATE = chr(0xD800)
EM_DASH = chr(0x2014)  # the dash in the datasheet's title
SUPERSCRIPT_ONE = chr(0xB9)
HINT = "Hostile Names"
SLUG = derive_project_slug(derive_project_name(HINT))
TARGET = RepoTarget(
    host_url="https://gitlab.example.com",
    namespace="ns",
    project_name_hint=HINT,
    visibility="private",
)
# The names the fixture report holds; a file that shows none of them cannot depend on the names.
BASELINE_NAMES = ["subrogation_training_set", "row_count_sanity", "target_nullability"]

# Names the notebooks' neutraliser changes the text of; the stem must come from the raw name.
QUARTO_NAMES = [
    ("quarto_shortcode", "{{< env HOME >}}"),
    ("quarto_fence", "```{python}"),
    ("markdown_heading", "# x"),
    ("backtick", "a`b"),
]
AGENT_NAMES = PATH_NAMES_FOR_THE_AGENT + QUARTO_NAMES
NAMES = [value for _, value in AGENT_NAMES]
IDS = [ident for ident, _ in AGENT_NAMES]


def _load(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return loaded


def _report(
    names: list[str],
    *,
    checks: list[str] | None = None,
    checks_by_query: list[list[str]] | None = None,
) -> dict[str, Any]:
    """The fixture report with one query per name, each with SQL of its own, and its checks.

    Everything a renderer prints about a query carries the query's number (its SQL, its purpose,
    its datasheet's motivation, its checks' SQL), so a test can tell which query a file or a
    paragraph came from even when two queries have one name.
    """

    data = _load("sample_datareport.json")
    template = data["primary_queries"][0]
    queries = []
    for index, name in enumerate(names):
        if checks_by_query is not None:
            check_names = checks_by_query[index]
        else:
            check_names = checks or [c["check_name"] for c in template["quality_checks"]]
        query = copy.deepcopy(template)
        query["name"] = name
        query["sql"] = f"SELECT {index} AS query_marker\n"
        query["purpose"] = f"purpose {index}"
        query["datasheet"]["motivation"] = f"motivation {index}"
        query["quality_checks"] = [
            {
                **copy.deepcopy(template["quality_checks"][0]),
                "check_name": check,
                "check_sql": f"SELECT {index}, {number} AS check_marker\n",
            }
            for number, check in enumerate(check_names)
        ]
        queries.append(query)
    data["primary_queries"] = queries
    return data


def _generate(data: dict[str, Any]) -> tuple[RepoProjectResult, dict[str, str]]:
    client = PathCheckingRepoClient()
    agent = WebsiteAgent(client, ci_platform="gitlab")
    # A refused commit is retried after a real 1 s and 2 s sleep; without this a regression makes
    # every failing case cost three seconds, as the host tests avoid in the same way.
    agent.graph = build_website_graph(client, sleep=lambda _seconds: None)
    result = agent.run(
        IntakeReport.model_validate(_load("subrogation_intake.json")),
        DataReport.model_validate(data),
        TARGET,
    )
    assert result.status == "COMPLETE", result.failure_reason
    return result, client.get_files(result.project_id)


def _checkout(files: dict[str, str], root: Path, order: str) -> list[Path]:
    """Write the files the way a checkout does, in the order a client or a host may hold them."""

    paths = list(files)
    if order == "sorted":
        paths.sort()
    elif order == "reversed":
        paths.sort(reverse=True)
    written = []
    for relative in paths:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(files[relative], encoding="utf-8")
        written.append(target)
    return written


def _on_disk(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


class TestThePathModelCanFail:
    """The model is only worth something if a bad path fails it."""

    @pytest.mark.parametrize(
        "path",
        [
            "",
            "/etc/passwd",
            "a//b",
            "a/./b",
            "a/../b",
            "../escape",
            "queries/primary/",
            ".git/config",
            "x/.GIT/config",
            "x/GIT~1/y",
            "a\\b",
            "a:b",
            "a*b",
            "a\nb",
            "a\x00b",
            "a\x7fb",
            "queries/primary/a.",
            "queries/primary/a .sql ",
            "queries/primary/CON.sql",
            "queries/quality/nul/x.sql",
            "queries/primary/Com1.sql",
            "queries/primary/" + "a" * 256 + ".sql",
            "queries/primary/" + "a" * 252 + ".sql",  # a 256-byte component, one too many
            "x/" + E_ACUTE * 128,  # 256 bytes in 128 characters
            "a" + LONE_SURROGATE + "b",
            "a?b",
            "a<b",
            "a>b",
            "a|b",
            'a"b',
            "a\x1fb",  # the last control character
            "queries/primary/a ",
            "queries/primary/conin$.sql",
            "queries/primary/COM" + SUPERSCRIPT_ONE + ".sql",
            "queries/quality/LPT" + SUPERSCRIPT_ONE + "/x.sql",
            "queries/primary/aux",
            "queries/primary/PRN.txt.sql",
        ],
    )
    def test_a_path_that_something_refuses_is_refused(self, path: str) -> None:
        assert unsafe_reason(path) is not None

    @pytest.mark.parametrize(
        "path",
        [
            "README.md",
            ".gitignore",
            ".gitlab-ci.yml",
            ".github/workflows/ci.yml",
            ".pre-commit-config.yaml",
            "queries/primary/subrogation_training_set.sql",
            "data/datasheet_a_b.md",
            "src/hostile_names/data_loading.py",
            "queries/primary/" + "a" * 251 + ".sql",
            "queries/primary/con_file.sql",
            "queries/primary/conx.sql",
            "queries/primary/a b.sql",  # a space inside a name is allowed
            "x/" + E_ACUTE * 127,  # 254 bytes
            "queries/primary/xcon.sql",
            "queries/primary/a.b.sql",
        ],
    )
    def test_a_path_the_scaffold_writes_is_accepted(self, path: str) -> None:
        assert unsafe_reason(path) is None

    @pytest.mark.parametrize(
        "paths",
        [
            ["queries/primary/a.sql", "queries/primary/A.sql"],
            [
                "queries/primary/caf" + E_ACUTE + ".sql",
                "queries/primary/cafe" + COMBINING_ACUTE + ".sql",
            ],
            ["queries/primary", "queries/primary/a.sql"],
            ["a/b/c", "a/b"],
            ["a", "a/b/c"],
        ],
    )
    def test_two_paths_that_are_one_file_somewhere_are_refused(self, paths: list[str]) -> None:
        assert collision(paths) is not None

    def test_paths_that_are_different_everywhere_are_not_a_collision(self) -> None:
        assert collision(["queries/primary/a.sql", "queries/quality/a/b.sql", "a.md"]) is None

    def test_the_client_refuses_a_commit_with_such_a_path(self) -> None:
        client = PathCheckingRepoClient()
        project = client.create_project(namespace="ns", name="p", visibility="private")
        with pytest.raises(RepoClientError, match="path refused"):
            client.commit_files(
                project_id=project.id,
                branch="main",
                files={"queries/primary/../../x.md": "x"},
                message="m",
            )
        with pytest.raises(RepoClientError, match="one file"):
            client.commit_files(
                project_id=project.id,
                branch="main",
                files={"a.sql": "1", "A.sql": "2"},
                message="m",
            )
        assert client.get_files(project.id) == {}

    @pytest.mark.parametrize("bad", ["queries/primary/../../x.md", "queries/primary/CON.sql"])
    def test_a_bad_path_anywhere_in_a_commit_refuses_all_of_it(self, bad: str) -> None:
        """The agent sends the whole scaffold in one commit, so the guard must read every path,
        not the first, and a refused commit must leave nothing behind."""

        client = PathCheckingRepoClient()
        project = client.create_project(namespace="ns", name="p", visibility="private")
        files = {f"queries/primary/q{n:03}.sql": "x" for n in range(60)}
        files[bad] = "x"  # after every safe path, in insertion order and in sorted order alike
        files["zzz/last.md"] = "x"
        with pytest.raises(RepoClientError, match="path refused"):
            client.commit_files(project_id=project.id, branch="main", files=files, message="m")
        assert client.get_files(project.id) == {}

    def test_a_collision_with_a_file_committed_earlier_is_refused(self) -> None:
        client = PathCheckingRepoClient()
        project = client.create_project(namespace="ns", name="p", visibility="private")
        client.commit_files(
            project_id=project.id, branch="main", files={"a/b.sql": "1"}, message="one"
        )
        with pytest.raises(RepoClientError, match="one file"):
            client.commit_files(
                project_id=project.id, branch="main", files={"A/B.sql": "2"}, message="two"
            )
        assert client.get_files(project.id) == {"a/b.sql": "1"}


class TestTheRenderersTakeTheStemTheyAreGiven:
    """``render_datasheet(stem=None)`` and the ``None`` of a report with no checks or queries
    are paths the agent never takes (it always passes a stem and a full report)."""

    def test_a_datasheet_without_a_stem_uses_the_stem_the_query_has_alone(self) -> None:
        text = render_datasheet(query={"name": "Claims 2024", "datasheet": {}})
        assert "> Source SQL: `queries/primary/claims_2024.sql`" in text
        assert text.startswith("# Datasheet " + EM_DASH + " `Claims 2024`")

    def test_a_datasheet_with_a_stem_uses_that_stem_and_keeps_the_name_as_its_title(self) -> None:
        text = render_datasheet(query={"name": "Dup", "datasheet": {}}, stem="dup_2")
        assert "> Source SQL: `queries/primary/dup_2.sql`" in text
        assert "`Dup`" in text.splitlines()[0]

    def test_a_datasheet_for_a_query_with_no_name_is_the_unnamed_one(self) -> None:
        assert "`queries/primary/unnamed.sql`" in render_datasheet(query={})

    @pytest.mark.parametrize("data", [{}, {"primary_queries": None}, {"primary_queries": []}])
    def test_a_report_with_no_queries_writes_no_query_files(self, data: dict[str, Any]) -> None:
        assert render_primary_query_files(data=data) == {}
        assert render_quality_check_files(data=data) == {}

    @pytest.mark.parametrize("query", [{"name": "a"}, {"name": "a", "quality_checks": None}])
    def test_a_query_with_no_checks_writes_its_sql_and_no_check_files(
        self, query: dict[str, Any]
    ) -> None:
        data = {"primary_queries": [{**query, "sql": "SELECT 1"}]}
        assert render_primary_query_files(data=data) == {"queries/primary/a.sql": "SELECT 1\n"}
        assert render_quality_check_files(data=data) == {}


class TestAReportThatWasFineIsUnchanged:
    def test_the_fixture_report_writes_the_paths_it_always_wrote(self) -> None:
        result, files = _generate(_load("sample_datareport.json"))
        assert {
            "queries/primary/subrogation_training_set.sql",
            "queries/quality/subrogation_training_set/row_count_sanity.sql",
            "queries/quality/subrogation_training_set/target_nullability.sql",
            "data/datasheet_subrogation_training_set.md",
        } <= set(files)
        assert sorted(result.files_created) == sorted(files)
        assert all(unsafe_reason(path) is None for path in files)


class TestAHostileNameStillMakesASafeProject:
    @pytest.mark.parametrize("name", NAMES, ids=IDS)
    def test_a_primary_query_name(self, name: str) -> None:
        result, files = _generate(_report([name]))
        assert sorted(result.files_created) == sorted(files)
        assert all(unsafe_reason(path) is None for path in result.files_created)
        assert all(
            unsafe_reason(path) is None for path in result.governance_manifest.artifacts_created
        )
        assert len([p for p in files if p.startswith("queries/primary/")]) == 1
        assert len([p for p in files if p.startswith("data/datasheet_")]) == 1
        assert len([p for p in files if p.startswith("queries/quality/")]) == 2

    @pytest.mark.parametrize("name", NAMES, ids=IDS)
    def test_a_check_name(self, name: str) -> None:
        result, files = _generate(_report(["alpha"], checks=[name, "row_count_sanity"]))
        assert all(unsafe_reason(path) is None for path in result.files_created)
        quality = sorted(p for p in files if p.startswith("queries/quality/"))
        assert len(quality) == 2
        assert all(p.startswith("queries/quality/alpha/") for p in quality)
        assert files["queries/primary/alpha.sql"] == "SELECT 0 AS query_marker\n"

    @pytest.mark.parametrize("name", NAMES, ids=IDS)
    def test_no_file_that_shows_no_name_is_touched(self, name: str) -> None:
        """Every file of the fixture project that does not mention one of its names is
        byte-for-byte the same, so a name cannot have replaced one of them."""

        _, baseline = _generate(_load("sample_datareport.json"))
        _, files = _generate(_report([name]))
        compared = 0
        for path, text in baseline.items():
            if path.startswith(("queries/", "data/datasheet_")):
                continue
            assert path in files, path
            if any(known in text for known in BASELINE_NAMES):
                continue
            compared += 1
            assert files[path] == text, path
        assert compared >= 20  # an emptied comparison would pass every case and prove nothing
        assert files["governance/model_card.md"] == baseline["governance/model_card.md"]

    @pytest.mark.parametrize("name", NAMES, ids=IDS)
    def test_every_path_the_project_prints_is_a_file_it_has(self, name: str) -> None:
        _, files = _generate(_report([name]))
        shown = 0
        for path, text in files.items():
            if path.startswith("reports/") or path.startswith("queries/"):
                continue  # the raw reports keep the readable name; the SQL is SQL
            # Anything up to a space, a backtick, an angle bracket, a brace or a star is a printed
            # path, so a raw name printed in a new place is caught here. The generic text
            # ``datasheet_<query>.md``, the glob ``datasheet_*.md`` and the f-string source of
            # the generated check are not paths and are left alone.
            for stem in re.findall(r"queries/primary/([^`\s<>*{}]+?)\.sql", text):
                shown += 1
                assert f"queries/primary/{stem}.sql" in files, (path, stem)
            for stem in re.findall(r"datasheet_([^`\s<>*{}]+?)\.md", text):
                shown += 1
                if not path.startswith("data/datasheet_"):
                    assert f"data/datasheet_{stem}.md" in files, (path, stem)
        assert shown >= 3


class TestNoFileIsReplacedOrLost:
    def test_a_name_aimed_at_the_model_card_leaves_the_model_card(self, tmp_path: Path) -> None:
        _, baseline = _generate(_load("sample_datareport.json"))
        _, files = _generate(_report(["x/../../governance/model_card"]))
        assert files["governance/model_card.md"] == baseline["governance/model_card.md"]
        assert "data/datasheet_x_governance_model_card.md" in files
        assert "queries/primary/x_governance_model_card.sql" in files
        assert "queries/governance/model_card.sql" not in files
        # ... and the readable name is still what a reader sees.
        assert "x/../../governance/model_card" in files["data/datasheet_x_governance_model_card.md"]
        for order in ("generated", "sorted", "reversed"):
            root = tmp_path / order
            _checkout(files, root, order)
            card = (root / "governance" / "model_card.md").read_text(encoding="utf-8")
            assert card == baseline["governance/model_card.md"], order

    def test_a_check_name_aimed_at_a_primary_query_leaves_it(self) -> None:
        _, files = _generate(_report(["beta"], checks=["../../primary/beta", "row_count_sanity"]))
        assert files["queries/primary/beta.sql"] == "SELECT 0 AS query_marker\n"
        assert files["queries/quality/beta/_primary_beta.sql"] == "SELECT 0, 0 AS check_marker\n"

    @pytest.mark.parametrize("order", ["generated", "sorted", "reversed"])
    def test_names_that_collide_are_all_written_and_none_replaced(
        self, tmp_path: Path, order: str
    ) -> None:
        names = ["dup", "dup", "Foo", "foo", "", " ", "a/b", "a_b"]
        _, files = _generate(_report(names, checks=["c", "c", "C"]))
        written = _checkout(files, tmp_path, order)
        assert len(_on_disk(tmp_path)) == len(files) == len(written)
        primary = {p: t for p, t in files.items() if p.startswith("queries/primary/")}
        assert sorted(primary.values()) == sorted(
            f"SELECT {index} AS query_marker\n" for index in range(len(names))
        )
        datasheets = [p for p in files if p.startswith("data/datasheet_")]
        assert len(datasheets) == len(names)
        checks = {p: t for p, t in files.items() if p.startswith("queries/quality/")}
        assert len(checks) == 3 * len(names)
        assert len(set(checks.values())) == 3 * len(names)
        # Each datasheet names the SQL file of its own query, and each check file sits under
        # the stem of the query it belongs to, even when two queries had one name.
        stem_of_query = {
            text: path.removeprefix("queries/primary/").removesuffix(".sql")
            for path, text in primary.items()
        }
        assert len(stem_of_query) == len(names)
        stem_by_number = {int(text.split()[1]): stem for text, stem in stem_of_query.items()}
        for path in datasheets:
            stem = path.removeprefix("data/datasheet_").removesuffix(".md")
            assert f"queries/primary/{stem}.sql" in files[path], path
            assert f"queries/primary/{stem}.sql" in files, path
            # ... and the datasheet of query N is the one filed under query N's stem.
            motivation = re.search(r"motivation (\d+)", files[path])
            assert motivation is not None, path
            assert stem_by_number[int(motivation.group(1))] == stem, path
        for path, text in checks.items():
            found = re.match(r"SELECT (\d+), ", text)
            assert found is not None, path
            expected = stem_of_query[f"SELECT {found.group(1)} AS query_marker\n"]
            assert path.split("/")[2] == expected, path
        # The data README and notebook 02 print, for each query, the files of that query.
        readme = re.findall(
            r"- \*\*Purpose:\*\* purpose (\d+)\n- \*\*Datasheet:\*\* `datasheet_([a-z0-9_]+)\.md`",
            files["data/README.md"],
        )
        notebook = re.findall(
            r"purpose (\d+)\n\nSQL: `queries/primary/([a-z0-9_]+)\.sql`",
            files["analysis/02_data.qmd"],
        )
        for shown in (readme, notebook):
            assert len(shown) == len(names)
            assert {int(number): stem for number, stem in shown} == stem_by_number

    def test_each_query_gets_the_check_files_of_its_own_checks(self) -> None:
        """Two queries with different checks, one of them repeating a name: every check file is
        named by that check, under that query."""

        data = _report(
            ["first", "second"],
            checks_by_query=[["row_count", "row_count"], ["a/b", "Null Check", "c"]],
        )
        _, files = _generate(data)
        quality = {p: t for p, t in files.items() if p.startswith("queries/quality/")}
        assert quality == {
            "queries/quality/first/row_count.sql": "SELECT 0, 0 AS check_marker\n",
            "queries/quality/first/row_count_2.sql": "SELECT 0, 1 AS check_marker\n",
            "queries/quality/second/a_b.sql": "SELECT 1, 0 AS check_marker\n",
            "queries/quality/second/null_check.sql": "SELECT 1, 1 AS check_marker\n",
            "queries/quality/second/c.sql": "SELECT 1, 2 AS check_marker\n",
        }

    def test_a_primary_name_and_a_check_name_cannot_make_one_path_together(self) -> None:
        """Primary ``a`` with check ``b/c`` and primary ``a/b`` with check ``c`` both made
        ``queries/quality/a/b/c.sql``."""

        data = _report(["a", "a/b"])
        data["primary_queries"][0]["quality_checks"][0]["check_name"] = "b/c"
        data["primary_queries"][1]["quality_checks"][0]["check_name"] = "c"
        _, files = _generate(data)
        markers = [
            text
            for path, text in files.items()
            if path.startswith("queries/quality/") and "check_marker" in text
        ]
        assert "SELECT 0, 0 AS check_marker\n" in markers
        assert "SELECT 1, 0 AS check_marker\n" in markers


class TestTheGeneratedProjectStaysHonest:
    def _project(self, tmp_path: Path, names: list[str]) -> tuple[Path, dict[str, str]]:
        _, files = _generate(_report(names))
        _checkout(files, tmp_path, "generated")
        return tmp_path, files

    def test_its_own_governance_check_passes_for_names_that_used_to_crash_it(
        self, tmp_path: Path
    ) -> None:
        names = [
            "a" * 243,
            "b" * 251,
            "c" * 252,
            "d" * 300,
            "x/../../governance/model_card",
            "CON",
            "",
        ]
        root, _ = self._project(tmp_path, names)
        assert gc.check(root) == []

    def test_the_check_still_asks_for_a_datasheet_for_every_query(self, tmp_path: Path) -> None:
        root, _ = self._project(tmp_path, ["a/b", "Foo", "foo"])
        (root / "data" / "datasheet_a_b.md").unlink()
        problems = gc.check(root)
        assert any("datasheet_a_b.md" in problem for problem in problems)

    def test_data_loading_reads_every_query_it_lists(self, tmp_path: Path) -> None:
        names = ["x/../../governance/model_card", "dup", "dup", "CON", "../../../etc/passwd"]
        root, _ = self._project(tmp_path, names)
        module = self._data_loading(root)
        listed = module.PRIMARY_QUERY_NAMES
        assert len(listed) == len(names)
        assert len(set(listed)) == len(names)
        for index, stem in enumerate(listed):
            assert re.fullmatch(r"[a-z0-9_]+", stem), stem
            assert module.read_sql(stem) == f"SELECT {index} AS query_marker\n"

    @staticmethod
    def _data_loading(root: Path) -> ModuleType:
        spec = importlib.util.spec_from_file_location(
            "generated_data_loading", root / "src" / SLUG / "data_loading.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
