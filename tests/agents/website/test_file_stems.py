"""File stems: a report name that becomes a file name (BACKLOG (7)(a), Session 296).

``PrimaryQuery.name`` and ``QualityCheck.check_name`` are bare strings, and the website agent used
to put them into ``queries/primary/<name>.sql``, ``data/datasheet_<name>.md`` and
``queries/quality/<name>/<check>.sql`` unchanged. A name of ``x/../../governance/model_card``
chose another file of the project, two queries named alike replaced one another, and a name of
243 characters made the generated governance check crash. ``_file_stems`` turns every name into a
stem that is safe as a file name and unique in its list, and a name that is already safe is its
own stem.

No non-ASCII character is written raw in this file (the Write tool and the shell layer turn an
escape into the raw character, learning #397): every one is built with ``chr`` and says which.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any

import pytest

from model_project_constructor.agents.website._file_stems import (
    DEVICE_SUFFIX,
    MAX_STEM_LENGTH,
    UNNAMED,
    UNNAMED_CHECK,
    WINDOWS_DEVICE_NAMES,
    derive_file_stems,
    file_stem,
    primary_query_stems,
    quality_check_stems,
)
from tests.agents.website.hostile_names import (
    HOSTILE_IDS,
    HOSTILE_VALUES,
    PATH_IDS,
    PATH_VALUES,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
SAFE = re.compile(r"[a-z0-9_]+")

E_ACUTE = chr(0xE9)  # the precomposed letter e with an acute accent
COMBINING_ACUTE = chr(0x301)
SHARP_S = chr(0xDF)
FULLWIDTH_SOLIDUS = chr(0xFF0F)  # looks like a slash, and is one after compatibility folding
FULLWIDTH_A = chr(0xFF21)
FULLWIDTH_B = chr(0xFF22)
CAPITAL_I_WITH_DOT = chr(0x130)  # decomposes into a letter and a combining dot
CJK_FIRST = chr(0x65E5)
CJK_SECOND = chr(0x672C)
LONE_SURROGATE = chr(0xD800)

ALL_HOSTILE = HOSTILE_VALUES + PATH_VALUES
ALL_HOSTILE_IDS = HOSTILE_IDS + PATH_IDS


class TestAConformingNameIsItsOwnStem:
    """Changing a name that was fine would change every report that was fine."""

    @pytest.mark.parametrize(
        "name",
        [
            "subrogation_training_set",
            "a",
            "q1",
            "row_count_sanity",
            "x_y_z",
            "_leading",
            "trailing_",
            "2024_claims",
            "0",
            "a" * MAX_STEM_LENGTH,
            "con_file",
            "conx",
            "nul2",
            "com10",
            "com0",
            "lpt",
            "z",
            "9",
            "_con",
            "con_",
            "lpt_1",
        ],
    )
    def test_the_stem_is_the_name(self, name: str) -> None:
        assert file_stem(name) == name
        assert derive_file_stems([name]) == [name]

    def test_every_name_in_the_fixture_report_keeps_its_name(self) -> None:
        report = json.loads((FIXTURES / "sample_datareport.json").read_text(encoding="utf-8"))
        names = [q["name"] for q in report["primary_queries"]]
        checks = [c["check_name"] for q in report["primary_queries"] for c in q["quality_checks"]]
        assert names and checks
        assert primary_query_stems(report) == names
        for query in report["primary_queries"]:
            expected = [c["check_name"] for c in query["quality_checks"]]
            assert quality_check_stems(query) == expected

    def test_a_list_of_distinct_conforming_names_comes_back_unchanged(self) -> None:
        names = ["b", "a", "c_2", "c", "z9"]
        assert derive_file_stems(names) == names

    def test_the_longest_name_that_fits_is_the_longest_stem(self) -> None:
        assert MAX_STEM_LENGTH == 64
        assert file_stem("a" * 64) == "a" * 64
        assert file_stem("a" * 65) == "a" * 64


class TestAnyNameBecomesAFileNameThatIsSafeEverywhere:
    """Lower-case letters, digits and underscores only: no separator, no dot, no device name."""

    @pytest.mark.parametrize(
        ("name", "stem"),
        [
            ("x/../../governance/model_card", "x_governance_model_card"),
            ("../escape", "_escape"),
            ("a/b", "a_b"),
            ("a//b", "a_b"),
            ("a\\b", "a_b"),
            ("/etc/passwd", "_etc_passwd"),
            ("Claims 2024", "claims_2024"),
            ("Row count > 0", "row_count_0"),
            ("a\nb", "a_b"),
            ("a" + chr(0) + "b", "a_b"),
            ("a%2fb", "a_2fb"),
            (".git", "_git"),
            ("GIT~1", "git_1"),
            ("a.sql", "a_sql"),
            ("Foo", "foo"),
            ("FOO_BAR", "foo_bar"),
            # Letters with accents lose the accent, whichever way the accent is written.
            ("caf" + E_ACUTE, "cafe"),
            ("cafe" + COMBINING_ACUTE, "cafe"),
            # Case folding, not lower-casing: the sharp s is two letters.
            ("Stra" + SHARP_S + "e", "strasse"),
            # Compatibility folding: the look-alike of a slash is a separator, and the look-alike
            # of a letter is that letter.
            ("a" + FULLWIDTH_SOLIDUS + "b", "a_b"),
            (FULLWIDTH_A + FULLWIDTH_B, "ab"),
            ("a" + LONE_SURROGATE + "b", "a_b"),
            # A capital I with a dot above decomposes into two characters; only the letter stays.
            (CAPITAL_I_WITH_DOT, "i"),
        ],
    )
    def test_the_stem_of(self, name: str, stem: str) -> None:
        assert file_stem(name) == stem

    @pytest.mark.parametrize("name", ["", ".", "..", "...", "/", "//", "_", "__", "-", " ", "\n"])
    def test_a_name_with_nothing_to_keep_is_unnamed(self, name: str) -> None:
        assert file_stem(name) == UNNAMED
        assert file_stem(name, fallback=UNNAMED_CHECK) == UNNAMED_CHECK

    def test_no_letters_of_another_script_means_unnamed(self) -> None:
        assert file_stem(CJK_FIRST + CJK_SECOND) == UNNAMED

    def test_a_missing_name_is_unnamed(self) -> None:
        assert file_stem(None) == UNNAMED
        assert file_stem(None, fallback=UNNAMED_CHECK) == UNNAMED_CHECK
        assert UNNAMED == "unnamed"
        assert UNNAMED_CHECK == "unnamed_check"

    @pytest.mark.parametrize(
        "device",
        ["con", "prn", "aux", "nul"]
        + [f"com{n}" for n in range(1, 10)]
        + [f"lpt{n}" for n in range(1, 10)],
    )
    def test_each_of_the_twenty_two_device_names_is_renamed(self, device: str) -> None:
        assert file_stem(device) == device + DEVICE_SUFFIX
        assert file_stem(device.upper()) == device + DEVICE_SUFFIX

    def test_a_letter_that_only_normalising_turns_into_a_capital_is_a_letter(self) -> None:
        """Case folding comes after the compatibility fold: the mathematical bold capital A
        and the modifier capital A become ``A`` only once decomposed, and ``a`` once folded."""

        assert file_stem(chr(0x1D400)) == "a"
        assert file_stem(chr(0x1D2C)) == "a"

    def test_the_cut_comes_after_the_runs_are_collapsed(self) -> None:
        assert file_stem("/" * 50 + "a" * 100) == "_" + "a" * 63

    def test_a_falsy_name_that_is_not_none_is_written_as_text(self) -> None:
        assert file_stem(0) == "0"
        assert file_stem(False) == "false"

    def test_a_name_that_is_not_text_is_written_as_text(self) -> None:
        assert file_stem(5) == "5"

    def test_the_underscores_a_run_of_separators_leaves_are_one(self) -> None:
        assert file_stem("a" + "/." * 20 + "b") == "a_b"

    def test_a_cut_that_leaves_only_underscores_is_unnamed(self) -> None:
        """The check for something to keep is made after the cut, not before it."""

        assert file_stem("_" * MAX_STEM_LENGTH + "a") == UNNAMED
        assert file_stem("_" * (MAX_STEM_LENGTH - 1) + "a") == "_" * (MAX_STEM_LENGTH - 1) + "a"

    @pytest.mark.parametrize(
        "name",
        ["con", "CON", "Con", "prn", "aux", "nul", "NUL", "com1", "COM9", "lpt1", "Lpt9"],
    )
    def test_a_windows_device_name_is_not_a_stem(self, name: str) -> None:
        """``CON.sql`` cannot be checked out on Windows, so ``con`` is not a file stem."""

        stem = file_stem(name)
        assert stem == name.lower() + DEVICE_SUFFIX
        assert stem not in WINDOWS_DEVICE_NAMES

    @pytest.mark.parametrize("name", ["con.sql", "conx", "xcon", "con_1", "com", "lpt0", "nul_"])
    def test_a_name_that_only_starts_or_ends_like_a_device_name_is_not_one(self, name: str) -> None:
        assert file_stem(name) == re.sub(r"[^a-z0-9_]+", "_", name)

    def test_the_device_names_are_the_twenty_two_ascii_names_windows_reserves(self) -> None:
        expected = {"con", "prn", "aux", "nul"}
        expected |= {f"com{n}" for n in range(1, 10)} | {f"lpt{n}" for n in range(1, 10)}
        assert expected == set(WINDOWS_DEVICE_NAMES)
        assert len(expected) == 22
        assert DEVICE_SUFFIX == "_file"
        assert file_stem("con") == "con_file"
        assert file_stem("COM1") == "com1_file"

    @pytest.mark.parametrize("value", ALL_HOSTILE, ids=ALL_HOSTILE_IDS)
    def test_every_hostile_name_gets_a_safe_stem(self, value: str) -> None:
        stem = file_stem(value)
        assert SAFE.fullmatch(stem)
        assert re.search(r"[a-z0-9]", stem)
        assert len(stem) <= MAX_STEM_LENGTH
        assert stem not in WINDOWS_DEVICE_NAMES
        assert file_stem(stem) == stem  # a stem is its own stem

    @pytest.mark.parametrize("plane", range(17), ids=lambda plane: f"plane_{plane}")
    def test_every_code_point_alone_gets_a_safe_stem(self, plane: int) -> None:
        """No class of character is left out: all 1,114,112 code points, a plane at a time."""

        for code in range(plane * 0x10000, (plane + 1) * 0x10000):
            stem = file_stem(chr(code))
            assert SAFE.fullmatch(stem), hex(code)
            assert len(stem) <= MAX_STEM_LENGTH, hex(code)
            assert stem not in WINDOWS_DEVICE_NAMES, hex(code)

    def test_the_longest_file_name_a_stem_can_make_fits_every_filesystem(self) -> None:
        stem = "a" * MAX_STEM_LENGTH
        for name in (f"datasheet_{stem}.md", f"{stem}.sql"):
            assert len(name.encode("utf-8")) <= 255


class TestAListOfStemsIsUniqueAndKeepsTheNamesThatAreFine:
    @pytest.mark.parametrize(
        ("names", "stems"),
        [
            ([], []),
            (["dup", "dup"], ["dup", "dup_2"]),
            (["dup", "dup", "dup"], ["dup", "dup_2", "dup_3"]),
            # Two names that fold to one stem: the one that was already a stem keeps it,
            # wherever it stands in the list.
            (["Foo", "foo"], ["foo_2", "foo"]),
            (["foo", "Foo"], ["foo", "foo_2"]),
            # A number never takes the stem another name has as its own.
            (["a", "a", "a_2"], ["a", "a_3", "a_2"]),
            (["A", "A", "a_2"], ["a", "a_3", "a_2"]),
            # ... nor the stem a later name that is not itself a stem folds to.
            (["A", "A", "A_2"], ["a", "a_3", "a_2"]),
            (["", "unnamed"], ["unnamed_2", "unnamed"]),
            (["", ""], ["unnamed", "unnamed_2"]),
            (["con", "con_file"], ["con_file_2", "con_file"]),
            (["x/y", "x_y", "X Y"], ["x_y_2", "x_y", "x_y_3"]),
            (["x/y", "x/y"], ["x_y", "x_y_2"]),
        ],
    )
    def test_the_stems_of(self, names: list[str], stems: list[str]) -> None:
        assert derive_file_stems(names) == stems

    def test_a_number_fits_inside_the_length_cap(self) -> None:
        long = "a" * 70
        assert derive_file_stems([long, long, long]) == [
            "a" * 64,
            "a" * 62 + "_2",
            "a" * 62 + "_3",
        ]
        full = "a" * 64
        assert derive_file_stems([full, full]) == [full, "a" * 62 + "_2"]

    def test_a_number_of_two_or_three_digits_still_fits_inside_the_cap(self) -> None:
        full = "a" * 64
        stems = derive_file_stems([full] * 120)
        assert stems[0] == full
        assert stems[1] == "a" * 62 + "_2"
        assert stems[8] == "a" * 62 + "_9"
        assert stems[9] == "a" * 61 + "_10"
        assert stems[98] == "a" * 61 + "_99"
        assert stems[99] == "a" * 60 + "_100"
        assert stems[119] == "a" * 60 + "_120"
        assert len(set(stems)) == 120
        assert all(len(stem) <= MAX_STEM_LENGTH for stem in stems)

    def test_a_missing_name_and_a_name_that_says_unnamed_are_two_names(self) -> None:
        assert derive_file_stems([None, "unnamed"]) == ["unnamed_2", "unnamed"]
        assert derive_file_stems(["unnamed", None]) == ["unnamed", "unnamed_2"]

    def test_ten_or_more_of_one_name_are_numbered_up_to_the_cap(self) -> None:
        stems = derive_file_stems(["q"] * 12)
        assert stems[0] == "q" and stems[1] == "q_2" and stems[11] == "q_12"
        assert len(set(stems)) == 12

    def test_when_no_name_was_a_stem_the_first_of_them_keeps_it(self) -> None:
        assert derive_file_stems(["Foo", "FOO"]) == ["foo", "foo_2"]
        assert derive_file_stems(["FOO", "Foo"]) == ["foo", "foo_2"]
        assert derive_file_stems(["a b", "A-B", "a.b"]) == ["a_b", "a_b_2", "a_b_3"]

    def test_the_fallback_applies_to_every_name_with_nothing_to_keep(self) -> None:
        assert derive_file_stems([None, "..", ""], fallback="unnamed_check") == [
            "unnamed_check",
            "unnamed_check_2",
            "unnamed_check_3",
        ]

    def test_the_same_list_always_gives_the_same_stems(self) -> None:
        names = ["B", "b", "b_2", "x/y", "x_y", "", "CON", "con_file"]
        assert derive_file_stems(names) == derive_file_stems(list(names))

    @pytest.mark.parametrize("seed", range(20))
    def test_random_lists_over_awkward_tokens(self, seed: int) -> None:
        rng = random.Random(296_000 + seed)
        tokens = [
            "a",
            "A",
            "a_2",
            "a_3",
            "x/y",
            "x_y",
            "X Y",
            "",
            ".",
            "..",
            "con",
            "CON",
            "con_file",
            "unnamed",
            "Unnamed",
            E_ACUTE,
            "e",
            COMBINING_ACUTE,
            CJK_FIRST,
            "a" * 70,
            "b" * 64,
            "b" * 63 + "c",
            "_",
            "__",
            "9",
            "-",
            " ",
            "/",
            LONE_SURROGATE,
        ]
        for _ in range(60):
            names = [
                "".join(rng.choice(tokens) for _ in range(rng.randint(1, 3)))
                for _ in range(rng.randint(1, 8))
            ]
            stems = derive_file_stems(names)
            assert len(stems) == len(names), names
            assert len(set(stems)) == len(stems), (names, stems)
            assert len({s.casefold() for s in stems}) == len(stems), (names, stems)
            for stem in stems:
                assert SAFE.fullmatch(stem), (names, stems)
                assert len(stem) <= MAX_STEM_LENGTH, (names, stems)
                assert stem not in WINDOWS_DEVICE_NAMES, (names, stems)
            assert stems == derive_file_stems(names), names
            seen: set[str] = set()
            for name, stem in zip(names, stems, strict=True):
                if file_stem(name) == name and name not in seen:
                    assert stem == name, (names, stems)  # the first of a name that is fine
                seen.add(name)
            if len(set(names)) == len(names) and all(file_stem(n) == n for n in names):
                assert stems == names


class TestTheHelpersReadTheReport:
    def test_primary_query_stems(self) -> None:
        data = {"primary_queries": [{"name": "a"}, {"name": "a"}, {}, {"name": "../x"}]}
        assert primary_query_stems(data) == ["a", "a_2", "unnamed", "_x"]

    @pytest.mark.parametrize("data", [{}, {"primary_queries": None}, {"primary_queries": []}])
    def test_a_report_without_queries_has_no_stems(self, data: dict[str, Any]) -> None:
        assert primary_query_stems(data) == []

    def test_quality_check_stems_are_those_of_one_query(self) -> None:
        query = {
            "quality_checks": [{"check_name": "c"}, {"check_name": "c"}, {}, {"check_name": ".."}]
        }
        assert quality_check_stems(query) == ["c", "c_2", "unnamed_check", "unnamed_check_2"]

    @pytest.mark.parametrize("query", [{}, {"quality_checks": None}, {"quality_checks": []}])
    def test_a_query_without_checks_has_no_stems(self, query: dict[str, Any]) -> None:
        assert quality_check_stems(query) == []

    def test_two_queries_may_use_the_same_check_name(self) -> None:
        one = {"name": "p", "quality_checks": [{"check_name": "row_count"}]}
        two = {"name": "q", "quality_checks": [{"check_name": "row_count"}]}
        assert quality_check_stems(one) == quality_check_stems(two) == ["row_count"]


class TestTheCorporaAreNotEmptied:
    """An emptied corpus would skip every parametrised case that reads it and still pass."""

    def test_the_path_corpus_is_not_empty_and_has_no_repeats(self) -> None:
        assert len(PATH_VALUES) >= 25
        assert len(set(PATH_IDS)) == len(PATH_IDS)
        assert len(set(PATH_VALUES)) == len(PATH_VALUES)
        assert len(ALL_HOSTILE) == len(ALL_HOSTILE_IDS) == len(HOSTILE_VALUES) + len(PATH_VALUES)
