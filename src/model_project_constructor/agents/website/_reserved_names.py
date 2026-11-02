"""Names a generated project's package may not take.

``derive_project_slug`` turns a project name into the name of the Python package the scaffold
writes (``src/<slug>/``), and the scaffold's tests, notebooks and registry import that package
by name. A package named like a module that Python finds first is not the one the import
reaches, and the failure is not the same everywhere:

- ``tests`` and the names of many standard-library modules (``logging``, ``email``, ``types``
  ...) stop the generated tests from collecting at all, because pytest puts the project's own
  ``tests`` package and the standard library ahead of ``src``;
- the others pass pytest and fail once the package is installed, because an editable install
  puts ``src`` after the standard library on ``sys.path``;
- a Python keyword (``class``, ``import`` ...) is a ``SyntaxError`` in every generated test file.

``derive_project_slug`` appends ``_model`` to a slug found here, so ``Types`` becomes
``types_model`` and every other slug is unchanged.

The list is frozen, not read from the running interpreter, so the same project name gives the
same package name on any machine and on any Python that the project allows (3.11 and later).
It holds the names the slug rule can produce (lower case, a letter first, then letters, digits
and underscores) from the union of ``sys.stdlib_module_names`` for Python 3.11 to 3.15, plus
``test`` (a standard-library package on some builds, absent from ``sys.stdlib_module_names``),
``tests`` and the lower-case keywords. ``test_reserved_names.py`` holds it against the
interpreter that runs the suite, so a standard-library module added by a later Python fails the
suite until it is listed here.

Not covered, on purpose: names of third-party packages the scaffold or its test runner imports
(``pytest``, ``sklearn``, ``sqlalchemy`` ...) and names that collide with the project's own
dependencies as a *distribution* (``pandas``). Both are separate defects with separate fixes.
"""

from __future__ import annotations

from typing import Final

_NAMES: Final[str] = """
    abc aifc and annotationlib antigravity argparse array as assert ast async asynchat
    asyncio asyncore atexit audioop await base64 bdb binascii bisect break builtins bz2
    calendar cgi cgitb chunk class cmath cmd code codecs codeop collections colorsys
    compileall compression concurrent configparser contextlib contextvars continue copy
    copyreg crypt csv ctypes curses dataclasses datetime dbm decimal def del difflib dis
    distutils doctest elif else email encodings ensurepip enum errno except faulthandler
    fcntl filecmp fileinput finally fnmatch for fractions from ftplib functools gc
    genericpath getopt getpass gettext glob global graphlib grp gzip hashlib heapq hmac
    html http idlelib if imaplib imghdr imp import importlib in inspect io ipaddress is
    itertools json keyword lambda lib2to3 linecache locale logging lzma mailbox mailcap
    marshal math mimetypes mmap modulefinder msilib msvcrt multiprocessing netrc nis
    nntplib nonlocal not nt ntpath nturl2path numbers opcode operator optparse or os
    ossaudiodev pass pathlib pdb pickle pickletools pipes pkgutil platform plistlib
    poplib posix posixpath pprint profile profiling pstats pty pwd py_compile pyclbr
    pydoc pydoc_data pyexpat queue quopri raise random re readline reprlib resource
    return rlcompleter runpy sched secrets select selectors shelve shlex shutil signal
    site smtpd smtplib sndhdr socket socketserver spwd sqlite3 sre_compile sre_constants
    sre_parse ssl stat statistics string stringprep struct subprocess sunau symtable sys
    sysconfig syslog tabnanny tarfile telnetlib tempfile termios test tests textwrap
    this threading time timeit tkinter token tokenize tomllib trace traceback
    tracemalloc try tty turtle turtledemo types typing unicodedata unittest urllib uu
    uuid venv warnings wave weakref webbrowser while winreg winsound with wsgiref xdrlib
    xml xmlrpc yield zipapp zipfile zipimport zlib zoneinfo
"""

RESERVED_SLUGS: Final[frozenset[str]] = frozenset(_NAMES.split())

SUFFIX: Final[str] = "_model"
