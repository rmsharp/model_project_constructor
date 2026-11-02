"""A project name must not become a package that shadows a Python module.

``derive_project_slug`` names the package the scaffold writes. Named ``tests``, ``logging`` or
``class``, that package fails every generated test (Session 286's run found it, Session 290's
review measured it): pytest or the standard library finds another module first, or the file is a
``SyntaxError``. These tests pin the rename and hold the frozen list against the interpreter that
runs them.
"""

from __future__ import annotations

import keyword
import re
import sys

import pytest

from model_project_constructor.agents.website._reserved_names import RESERVED_SLUGS, SUFFIX
from model_project_constructor.agents.website.templates import (
    derive_project_name,
    derive_project_slug,
)

# What ``derive_project_slug`` can produce: lower case, a letter first, no repeated or trailing
# underscore.
PRODUCIBLE = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")

_DIFFERS_BY_VERSION = """
    aifc annotationlib asynchat asyncore audioop cgi cgitb chunk compression crypt distutils
    imghdr imp lib2to3 mailcap msilib nis nntplib ossaudiodev pipes profiling smtpd sndhdr
    spwd sre_compile sre_constants sre_parse sunau telnetlib uu xdrlib
"""
DIFFERS_BY_VERSION = frozenset(_DIFFERS_BY_VERSION.split())


class TestAReservedNameIsRenamed:
    @pytest.mark.parametrize(
        ("hint", "slug"),
        [
            ("Tests", "tests_model"),
            ("test", "test_model"),
            ("Logging", "logging_model"),
            ("types", "types_model"),
            ("Email", "email_model"),
            ("JSON", "json_model"),
            ("os", "os_model"),
            ("random", "random_model"),
            ("Class", "class_model"),
            ("import", "import_model"),
            ("pass", "pass_model"),
            # Five reserved names contain an underscore, and ``derive_project_name`` turns every
            # underscore into a hyphen, so the pipeline reaches them only in these forms.
            ("Py Compile", "py_compile_model"),
            ("sre-parse", "sre_parse_model"),
            ("Pydoc Data", "pydoc_data_model"),
        ],
    )
    def test_the_slug_gets_the_suffix(self, hint: str, slug: str) -> None:
        assert derive_project_slug(derive_project_name(hint)) == slug

    def test_the_repository_name_is_not_renamed(self) -> None:
        # Only the Python package is. The repository keeps the name the stakeholder chose.
        assert derive_project_name("Types") == "types"
        assert derive_project_slug("types") == "types_model"

    @pytest.mark.parametrize("name", ["json-schema", "Logging Tools", "email_2", "tests-2"])
    def test_a_name_that_merely_contains_one_is_unchanged(self, name: str) -> None:
        slug = derive_project_slug(name)
        assert not slug.endswith(SUFFIX)
        assert slug not in RESERVED_SLUGS

    def test_the_renamed_slug_is_stable(self) -> None:
        once = derive_project_slug("types")
        assert derive_project_slug(once) == once

    def test_the_suffix_never_lands_on_another_reserved_name(self) -> None:
        assert [name for name in RESERVED_SLUGS if f"{name}{SUFFIX}" in RESERVED_SLUGS] == []


class TestEverySlugThatWasFineStaysTheSame:
    """A repository created last month must get the same package name next month."""

    @pytest.mark.parametrize(
        ("name", "slug"),
        [
            ("subrogation-model", "subrogation_model"),
            ("renewal-pricing-model", "renewal_pricing_model"),
            ("123-model", "m_123_model"),
            ("foo-bar!@baz", "foo_bar_baz"),
            ("", "model_project"),
            ("claims", "claims"),
            ("model", "model"),
            ("data", "data"),
            ("src", "src"),
        ],
    )
    def test_the_slug_is_unchanged(self, name: str, slug: str) -> None:
        assert derive_project_slug(name) == slug


class TestTheFrozenListAgreesWithThePython:
    def test_every_standard_library_module_a_slug_can_name_is_listed(self) -> None:
        reachable = {n for n in sys.stdlib_module_names if PRODUCIBLE.fullmatch(n)}
        assert sorted(reachable - RESERVED_SLUGS) == [], (
            "a standard-library module this Python added: add it to RESERVED_SLUGS"
        )

    def test_every_lower_case_keyword_is_listed(self) -> None:
        keywords = {k for k in keyword.kwlist if PRODUCIBLE.fullmatch(k)}
        assert keywords and sorted(keywords - RESERVED_SLUGS) == []

    def test_nothing_else_is_listed(self) -> None:
        # The other direction: an entry that is not a standard-library name, a keyword, one of
        # the names only some Pythons have, or test/tests would rename every repository that
        # a stakeholder happened to name that. Holds on 3.11 to 3.15.
        running = {n for n in sys.stdlib_module_names if PRODUCIBLE.fullmatch(n)}
        keywords = {k for k in keyword.kwlist if PRODUCIBLE.fullmatch(k)}
        allowed = running | keywords | DIFFERS_BY_VERSION | {"test", "tests"}
        assert sorted(RESERVED_SLUGS - allowed) == []

    def test_test_and_tests_are_listed(self) -> None:
        # ``test`` is a standard-library package on python.org and Homebrew builds and is not in
        # ``sys.stdlib_module_names``, so no set read from the interpreter finds it.
        assert {"test", "tests"} <= RESERVED_SLUGS

    def test_every_entry_is_a_slug_the_rule_can_produce(self) -> None:
        # An entry no name can reach (an upper-case letter, a hyphen, a leading underscore) is
        # dead weight. A misspelt but reachable entry would only rename a slug nobody uses.
        assert sorted(n for n in RESERVED_SLUGS if not PRODUCIBLE.fullmatch(n)) == []
        assert all(derive_project_slug(n) == f"{n}{SUFFIX}" for n in RESERVED_SLUGS)

    def test_the_list_keeps_the_modules_that_only_some_pythons_have(self) -> None:
        # The running interpreter shows only its own standard library, but a project may run on
        # any Python from 3.11, and the same project name must give the same package name on all
        # of them. These are the names that are not a standard-library module on every Python
        # from 3.11 to 3.15 (measured from each build's ``sys.stdlib_module_names``): removed in
        # 3.12 (PEP 594's first group and ``distutils``), in 3.13 (the rest of PEP 594 and
        # ``lib2to3``), in 3.15 (``sre_*``), or added in 3.14 and 3.15.
        assert len(DIFFERS_BY_VERSION) == 31
        assert sorted(DIFFERS_BY_VERSION - RESERVED_SLUGS) == []
