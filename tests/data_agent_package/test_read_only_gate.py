"""The statement gate in front of ``ReadOnlyDB.execute`` (``read_only_gate``).

The tables are the regression set Session 288 built from a scout's catalogue, in three parts:
the SQL this repository itself sends through ``execute`` (every one must pass); benign queries
that are false-positive traps for a naive gate (a keyword inside an identifier, a literal or a
comment); and hostile statements, each pinned to the RULE that refuses it, not merely to a
refusal, so removing one rule fails a test that only that rule explains. Many hostile entries
are the same text that two dialects read differently, which is why every entry carries the list
of dialects it applies to. Entries marked "accepted over-refusal" are refused on purpose; they
are here so the cost of the gate is a recorded choice and not a surprise.

The existing suite cannot tell a correct gate from a naive one: every statement it sends through
``execute`` is a plain ``SELECT`` (measured, Session 288: 83 calls, 16 distinct strings, with a
substring gate and a word-boundary regex gate both leaving it green).
"""

from __future__ import annotations

import copy
import pickle
from typing import Any

import pytest
from model_project_constructor_data_agent import read_only_gate
from model_project_constructor_data_agent.read_only_gate import (
    ReadOnlyViolation,
    check_read_only_sql,
)

# SQLAlchemy backend names; ``None`` is a dialect the gate has no facts for.
ALL: tuple[str | None, ...] = ("sqlite", "postgresql", "mysql", "mssql", "oracle", None)

# The 16 distinct strings that reach ``execute`` in this repository's suite (a spy on the method,
# full run), then four of the Larkspur example's model-shaped quality-check and baseline queries.
_REPO_SQL: list[str] = [
    "SELECT * FROM ghost_table",
    "SELECT * FROM no_such_table_at_all",
    "SELECT 1",
    "SELECT 2",
    "SELECT AVG(paid_amount) AS subro_recovery_rate FROM claims",
    "SELECT AVG(x) FROM table_that_does_not_exist",
    (
        "SELECT CASE WHEN SUM(paid_amount) = 0 THEN 0 ELSE "
        "SUM(subro_recovered) * 1.0 / SUM(paid_amount) END AS "
        "recovery_rate FROM claims WHERE subro_eligible = 1"
    ),
    "SELECT COUNT(*) AS n FROM claims WHERE state = 'TX'",
    "SELECT COUNT(*) FROM claims",
    "SELECT DATEDIFF(day, a, b) FROM claims",
    (
        "SELECT c.claim_id, c.paid_amount, c.subro_recovered, "
        "p.annual_premium FROM claims c JOIN policies p ON c.policy_id = "
        "p.policy_id WHERE c.line_of_business = 'auto' AND c.state = 'TX'"
    ),
    "SELECT claim_id FROM claims",
    "SELECT claim_id FROM claims WHERE state = 'TX' AND paid_amount < 0",
    (
        "SELECT claim_id, (julianday(fnol_date) - julianday(loss_date)) "
        "AS fnol_latency_days FROM claims"
    ),
    (
        "SELECT claim_id, paid_amount, state, loss_date FROM claims "
        "WHERE line_of_business = 'property'"
    ),
    "SELECT no_such_col FROM claims",
    (
        "SELECT 1 AS ok\nWHERE (SELECT COUNT(*) FROM claim) = (SELECT "
        "COUNT(DISTINCT claim_id) FROM claim)"
    ),
    (
        "SELECT ROUND(rate, 4) AS total_loss_rate FROM (\n    SELECT "
        "AVG(CASE WHEN settlement_type = 'TOTAL_LOSS' THEN 1.0 ELSE 0.0 "
        "END)\n           AS rate\n    FROM claim_outcome WHERE "
        "settlement_type IS NOT NULL\n) WHERE rate BETWEEN 0.06 AND 0.12"
    ),
    (
        "SELECT ROUND(m, 2) AS median_days FROM (SELECT AVG(days) AS m "
        "FROM (\n    SELECT julianday(o.tl_decision_ts) - "
        "julianday(c.fnol_ts) AS days\n    FROM claim c JOIN "
        "claim_outcome o ON o.claim_id = c.claim_id\n    WHERE "
        "o.settlement_type = 'TOTAL_LOSS'\n    ORDER BY days\n    LIMIT "
        "2 - (SELECT COUNT(*) FROM claim_outcome\n               WHERE "
        "settlement_type = 'TOTAL_LOSS') % 2\n    OFFSET (SELECT "
        "(COUNT(*) - 1) / 2 FROM claim_outcome\n            WHERE "
        "settlement_type = 'TOTAL_LOSS')\n)) WHERE m BETWEEN 4.0 AND 6.0"
    ),
    (
        "SELECT AVG(days) AS m FROM (\n    SELECT "
        "julianday(o.tl_decision_ts) - julianday(c.fnol_ts) AS days\n    "
        "FROM claim c JOIN claim_outcome o ON o.claim_id = c.claim_id\n  "
        "  WHERE o.settlement_type = 'TOTAL_LOSS'\n      AND o.closed_ts "
        "> date((SELECT as_of_date FROM data_snapshot), '-12 months')\n  "
        "  ORDER BY days\n    LIMIT 2 - (SELECT COUNT(*) FROM "
        "claim_outcome\n               WHERE settlement_type = "
        "'TOTAL_LOSS' AND closed_ts > date((SELECT as_of_date FROM "
        "data_snapshot), '-12 months')) % 2\n    OFFSET (SELECT "
        "(COUNT(*) - 1) / 2 FROM claim_outcome\n            WHERE "
        "settlement_type = 'TOTAL_LOSS' AND closed_ts > date((SELECT "
        "as_of_date FROM data_snapshot), '-12 months'))\n)"
    ),
]

# (id, sql, dialects it applies to, why). Every entry must pass.
BENIGN: list[tuple[str, str, tuple[str | None, ...], str]] = [
    ("B01", "SELECT 1", ALL, "minimal"),
    ("B02", "select claim_id from claims where state = 'TX'", ALL, "lower case"),
    (
        "B03",
        "SELECT COUNT(*) AS n FROM claims WHERE state = 'TX';",
        ALL,
        "single trailing semicolon",
    ),
    ("B04", "SELECT 1;   \n -- trailing comment\n", ALL, "trailing ; then whitespace and comment"),
    ("B05", "SELECT 1 ; /* c */", ALL, "trailing ; then block comment"),
    (
        "B06",
        "WITH s AS (SELECT state, COUNT(*) c FROM claims GROUP BY state) "
        "SELECT * FROM s ORDER BY c DESC",
        ALL,
        "plain CTE",
    ),
    (
        "B07",
        "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM r WHERE n<5) SELECT n FROM r",
        ALL,
        "recursive CTE",
    ),
    ("B08", "VALUES (1),(2)", ALL, "VALUES statement"),
    ("B09", "(SELECT 1) UNION ALL (SELECT 2)", ALL, "parenthesised select start"),
    ("B10", "((SELECT 1))", ALL, "double parentheses"),
    (
        "B11",
        "SELECT update_ts, deleted_flag, created_at, insert_date, "
        "drop_off, replace_cnt, set_id, into_x FROM t",
        ALL,
        "identifiers that merely CONTAIN keywords (token-level match)",
    ),
    (
        "B12",
        "SELECT * FROM claims WHERE note = 'please DELETE FROM claims; DROP TABLE claims'",
        ALL,
        "keywords and ; inside a string literal",
    ),
    (
        "B13",
        "SELECT 'it''s; DROP TABLE t; --' AS s",
        ALL,
        "doubled-quote escape keeps ; DROP inside the literal",
    ),
    (
        "B14",
        'SELECT "update", "delete", "into" FROM t',
        ALL,
        "double-quoted identifiers named after keywords",
    ),
    ("B15", "SELECT `update`, `delete` FROM t", ALL, "backtick identifiers named after keywords"),
    (
        "B16",
        "SELECT [update], [delete] FROM t",
        ("sqlite", "mssql"),
        "bracket identifiers named after keywords (bracket-quoting dialects)",
    ),
    ("B17", "SELECT 1 -- DROP TABLE t; DELETE FROM t", ALL, "keywords in a line comment"),
    ("B18", "SELECT 1 /* INSERT INTO t VALUES (1); */", ALL, "keywords in a block comment"),
    ("B19", "SELECT /*+ INDEX(t idx) */ * FROM t", ALL, "optimizer hint is an ordinary comment"),
    (
        "B20",
        "SELECT REPLACE(note, 'a', 'b') FROM claims",
        ALL,
        "REPLACE() is a scalar function in every dialect",
    ),
    (
        "B21",
        "SELECT TRUNCATE(paid_amount, 2) FROM claims",
        ALL,
        "TRUNCATE() is a MySQL numeric function",
    ),
    (
        "B22",
        "SELECT SUBSTRING(note FROM 2 FOR 3) FROM claims",
        ALL,
        "FOR not followed by UPDATE/SHARE/NO/KEY",
    ),
    (
        "B23",
        "SELECT share, key_val, no_val FROM mkt",
        ALL,
        "columns named share/key_val/no_val (SHARE must not be banned bare)",
    ),
    ("B24", "SELECT x FROM t FOR XML PATH('')", ("mssql", None), "T-SQL FOR XML"),
    ("B25", "SELECT LEFT(a,2), RIGHT(a,2) FROM t", ALL, "LEFT/RIGHT functions"),
    (
        "B26",
        "SELECT * FROM t WHERE created >= '2024-01-01' AND amt <> 0 OR x != 1",
        ALL,
        "comparison operators",
    ),
    ("B27", "SELECT CAST(x AS INTEGER), x::int FROM t", ALL, "cast forms"),
    ("B28", "SELECT a #> '{b}' FROM t", ("postgresql",), "PostgreSQL # operator"),
    (
        "B29",
        "SELECT $$it's; DROP TABLE t;$$ AS s",
        ("postgresql",),
        "dollar-quoted literal hides ; DROP",
    ),
    ("B30", "SELECT $tag$ ; DELETE FROM t $tag$", ("postgresql",), "tagged dollar quote"),
    ("B31", "SELECT E'a\\nb'", ALL, "backslash escape not before a quote"),
    ("B32", "SELECT 'C:\\temp\\file'", ALL, "backslashes in the middle of a literal"),
    (
        "B33",
        "SELECT 1 /* a * b / c */",
        ALL,
        "star and slash inside a block comment but no */ or /*",
    ),
    ("B34", "SELECT /*/ x */ 1", ALL, "/*/ does not self-close"),
    (
        "B35",
        'SELECT * FROM "Claims" c JOIN "pc"."policies" p ON c.pid = p.pid',
        ALL,
        "quoted qualified names",
    ),
    ("B36", "SELECT 1\n\t\r\n", ALL, "trailing whitespace variants"),
    ("B37", "  \n SELECT 1", ALL, "leading whitespace"),
    (
        "B38",
        "-- note: this does not update anything\nSELECT 1",
        ALL,
        "leading line comment containing a keyword",
    ),
    ("B39", "/* c */ SELECT 1", ALL, "leading block comment"),
    ("B40", "SELECT 'multi\nline literal'", ALL, "literal with real newline"),
    ("B41", "SELECT 'café'", ALL, "non-ASCII inside a literal"),
    (
        "B42",
        "SELECT 1 -- café \u200b zero-width in a comment",
        ALL,
        "non-ASCII/ZWSP inside a comment",
    ),
    ("B43", 'SELECT "café" FROM t', ALL, "non-ASCII inside a quoted identifier"),
    (
        "B44",
        "SELECT x FROM t WHERE x LIKE '%!_%' ESCAPE '!'",
        ALL,
        "LIKE ... ESCAPE with a non-backslash escape char",
    ),
    ("B45", "SELECT current_timestamp, random()", ALL, "zero-arg functions"),
    ("B46", "SELECT * FROM t ORDER BY 1 LIMIT 10 OFFSET 5", ALL, "OFFSET (token is not SET)"),
    ("B47", "SELECT t.updated, t.deleted FROM t", ALL, "past-tense words are not keywords"),
    (
        "B48",
        "SELECT * FROM t WHERE x = 'a' -- it's fine",
        ALL,
        "apostrophe inside a line comment must not open a literal",
    ),
    ("B49", 'select 1 as "select"', ALL, "keyword as quoted alias"),
    (
        "B50",
        "SELECT * FROM insert_log l JOIN update_log u ON l.id = u.id",
        ALL,
        "table names with keyword prefixes",
    ),
    (
        "B51",
        "SELECT * FROM t WHERE x IN (SELECT y FROM u) AND NOT EXISTS (SELECT 1 FROM v)",
        ALL,
        "subqueries",
    ),
    (
        "B52",
        "SELECT 'a:b', '12:30' AS tm",
        ALL,
        "colons in literals (gate-level pass; see sa.text note)",
    ),
    (
        "B53",
        "SELECT count(*) FROM t WHERE a = 1 -- x\r\n",
        ALL,
        "CRLF line ending after -- comment is unambiguous",
    ),
    ("B54", "SELECT 1 /* x */ /* y */", ALL, "adjacent comments, not nested"),
    ("B55", "SELECT a FROM t WHERE b='\\\\'", ALL, "escaped backslash pair then closing quote"),
    (
        "B56",
        "SELECT ARRAY[1,2,3], a[1] FROM t",
        ("sqlite", "postgresql", "mysql", "mssql", "oracle"),
        "array brackets",
    ),
    ("B57", "SELECT $1", ALL, "positional parameter marker"),
    (
        "B58",
        "SELECT * FROM t WHERE a = 'x' AND b = 'it''s' /* c ' d */ AND c = 1",
        ALL,
        "quote inside a block comment",
    ),
    ("B59", "WITH a AS (SELECT 1), b AS (SELECT 2) SELECT * FROM a, b", ALL, "two CTEs"),
    ("B60", "SELECT CASE WHEN x > 0 THEN 'pos' ELSE 'neg' END FROM t", ALL, "CASE"),
    (
        "B61",
        "SELECT SUM(paid_amount) OVER (PARTITION BY state ORDER BY "
        "loss_date ROWS BETWEEN 1 PRECEDING AND CURRENT ROW) FROM claims",
        ALL,
        "window frame",
    ),
    (
        "B62",
        "SELECT * FROM claims WHERE loss_date >= DATE '2024-01-01' AND state IN ('TX','NY')",
        ALL,
        "typed date literal",
    ),
    ("B63", "SELECT EXTRACT(YEAR FROM loss_date) AS y FROM claims", ALL, "EXTRACT ... FROM"),
    (
        "B64",
        "SELECT COUNT(DISTINCT policy_id) FROM claims GROUP BY state HAVING COUNT(*) > 1",
        ALL,
        "aggregate with HAVING",
    ),
    (
        "B65",
        "SELECT [a]]; DROP TABLE t; --] FROM t",
        ("mssql",),
        "SQL Server doubles ]] inside a bracketed identifier: this is ONE identifier (see H116)",
    ),
    (
        "B66",
        "SELECT \"pragmatic\", 'pragma', [x_pragma_y] FROM t WHERE n = 'ok'",
        ("sqlite", "mssql"),
        "only a name that BEGINS pragma_ is refused (H117 to H123), not one that contains pragma",
    ),
]

# (id, sql, rule code or {dialect: code}, dialects it applies to, why). Every entry must be
# refused, and by that rule.
HOSTILE: list[tuple[str, str, str | dict[str | None, str], tuple[str | None, ...], str]] = [
    ("H01", "SELECT 1; DROP TABLE t", "MULTIPLE_STATEMENTS", ALL, "second statement"),
    ("H02", "SELECT 1;DROP TABLE t", "MULTIPLE_STATEMENTS", ALL, "no space"),
    (
        "H03",
        "select 1; select 2",
        "MULTIPLE_STATEMENTS",
        ALL,
        "even a benign second statement is refused",
    ),
    ("H04", "SELECT 1;;", "MULTIPLE_STATEMENTS", ALL, "stray second ;"),
    (
        "H05",
        "SELECT 1; -- ok\nDELETE FROM t",
        "MULTIPLE_STATEMENTS",
        ALL,
        "comment then DML after ;",
    ),
    ("H06", "SELECT 1 /* x */ ; DELETE FROM t", "MULTIPLE_STATEMENTS", ALL, "comment before ;"),
    ("H07", "DROP TABLE t", "NOT_A_QUERY", ALL, "DDL first token"),
    ("H08", "DELETE FROM t", "NOT_A_QUERY", ALL, "DML first token"),
    ("H09", "INSERT INTO t VALUES (99,'x')", "NOT_A_QUERY", ALL, "DML"),
    ("H10", "UPDATE t SET x=1", "NOT_A_QUERY", ALL, "DML"),
    ("H11", "CREATE TABLE z(a)", "NOT_A_QUERY", ALL, "DDL"),
    ("H12", "PRAGMA user_version=7", "NOT_A_QUERY", ALL, "SQLite pragma"),
    ("H13", "ATTACH DATABASE 'x.db' AS x", "NOT_A_QUERY", ALL, "SQLite attach"),
    ("H14", "VACUUM INTO 'copy.db'", "NOT_A_QUERY", ALL, "SQLite copy-out"),
    (
        "H15",
        "EXPLAIN ANALYZE DELETE FROM t",
        "NOT_A_QUERY",
        ALL,
        "PG EXPLAIN ANALYZE executes the DML",
    ),
    ("H16", "WITH x AS (SELECT 1) DELETE FROM t", "WRITE_KEYWORD", ALL, "WITH-prefixed DML"),
    (
        "H17",
        "WITH x AS (SELECT 98 AS a, 'w' AS b) INSERT INTO t SELECT a, b FROM x",
        "WRITE_KEYWORD",
        ALL,
        "WITH-prefixed DML",
    ),
    ("H18", "WITH x AS (SELECT 1) UPDATE t SET x='w'", "WRITE_KEYWORD", ALL, "WITH-prefixed DML"),
    (
        "H19",
        "WITH x AS (DELETE FROM t RETURNING *) SELECT * FROM x",
        "WRITE_KEYWORD",
        ALL,
        "PG data-modifying CTE",
    ),
    (
        "H20",
        "WITH x AS (UPDATE t SET a=1 RETURNING *) SELECT * FROM x",
        "WRITE_KEYWORD",
        ALL,
        "PG data-modifying CTE",
    ),
    (
        "H21",
        "WITH x AS (INSERT INTO t VALUES (1) RETURNING *) SELECT * FROM x",
        "WRITE_KEYWORD",
        ALL,
        "PG data-modifying CTE",
    ),
    (
        "H22",
        "WITH x AS (SELECT 1) REPLACE INTO t VALUES (1,'w')",
        "WRITE_KEYWORD",
        ALL,
        "SQLite REPLACE after WITH",
    ),
    (
        "H23",
        "WITH x AS (SELECT 1) MERGE INTO t USING x ON t.a = x.a WHEN MATCHED THEN DELETE",
        "WRITE_KEYWORD",
        ALL,
        "PG15+ MERGE after WITH",
    ),
    (
        "H24",
        "SELECT * INTO newt FROM t",
        "WRITE_KEYWORD",
        ALL,
        "SELECT INTO creates a table (PG, T-SQL)",
    ),
    ("H25", "SELECT * INTO TEMP newt FROM t", "WRITE_KEYWORD", ALL, "SELECT INTO TEMP"),
    ("H26", "SELECT * FROM t INTO OUTFILE '/tmp/x'", "WRITE_KEYWORD", ALL, "MySQL file write"),
    ("H27", "SELECT * FROM t INTO DUMPFILE '/tmp/x'", "WRITE_KEYWORD", ALL, "MySQL file write"),
    ("H28", "SELECT a INTO @v FROM t", "WRITE_KEYWORD", ALL, "MySQL session variable"),
    ("H29", "SELECT * FROM t FOR UPDATE", "ROW_LOCK", ALL, "row locks"),
    ("H30", "SELECT * FROM t FOR NO KEY UPDATE", "ROW_LOCK", ALL, "row locks"),
    ("H31", "SELECT * FROM t FOR SHARE", "ROW_LOCK", ALL, "row locks"),
    ("H32", "SELECT * FROM t FOR KEY SHARE", "ROW_LOCK", ALL, "row locks"),
    ("H33", "SELECT * FROM t LOCK IN SHARE MODE", "ROW_LOCK", ALL, "MySQL row locks"),
    ("H34", "SELECT * FROM t FOR UPDATE SKIP LOCKED", "ROW_LOCK", ALL, "row locks"),
    ("H35", "SELECT * FROM t FOR\nUPDATE", "ROW_LOCK", ALL, "FOR and UPDATE split by newline"),
    (
        "H36",
        "SELECT * FROM t FOR /* c */ UPDATE",
        "ROW_LOCK",
        ALL,
        "FOR and UPDATE split by a comment",
    ),
    ("H37", "SELECT 'unterminated", "UNTERMINATED", ALL, "unterminated string"),
    ("H38", 'SELECT "unterminated', "UNTERMINATED", ALL, "unterminated quoted identifier"),
    ("H39", "SELECT 1 /* unterminated", "UNTERMINATED", ALL, "unterminated block comment"),
    ("H40", "SELECT 1 -- ok\n; DROP TABLE t", "MULTIPLE_STATEMENTS", ALL, "; after a line comment"),
    (
        "H41",
        "SELECT '\\'; DROP TABLE t; --'",
        "BACKSLASH_QUOTE",
        ALL,
        "backslash-quote: MySQL keeps the literal open, PG/SQLite/ANSI close it",
    ),
    ("H42", "SELECT E'\\'; DROP TABLE t; --'", "BACKSLASH_QUOTE", ALL, "same with E'' prefix"),
    (
        "H43",
        "SELECT 1 /*! ; DROP TABLE t */",
        "EXECUTABLE_COMMENT",
        ALL,
        "MySQL executable comment",
    ),
    (
        "H44",
        "SELECT 1 /*!50000 ; DROP TABLE t */",
        "EXECUTABLE_COMMENT",
        ALL,
        "MySQL versioned executable comment",
    ),
    (
        "H45",
        "SELECT 1 /*M! ; DROP TABLE t */",
        "EXECUTABLE_COMMENT",
        ALL,
        "MariaDB executable comment",
    ),
    (
        "H46",
        "SELECT 1 /* a /* b */ ; DROP TABLE t; /* c */ */",
        "NESTED_COMMENT",
        ALL,
        "nested comment: PG/T-SQL nest, MySQL/SQLite end at the first */",
    ),
    (
        "H46b",
        "SELECT 1 /* a /* b */ ' */ ; DROP TABLE t; --'",
        "NESTED_COMMENT",
        ALL,
        "nested comment desync: a non-nesting scanner opens a literal that hides the PG-visible ;",
    ),
    (
        "H47",
        "SELECT 1 # x\n; DROP TABLE t",
        {
            "sqlite": "HASH_COMMENT",
            "postgresql": "MULTIPLE_STATEMENTS",
            "mysql": "HASH_COMMENT",
            "mssql": "HASH_COMMENT",
            "oracle": "HASH_COMMENT",
            None: "HASH_COMMENT",
        },
        ALL,
        "# is a MySQL comment but a PG operator",
    ),
    (
        "H48",
        "SELECT 1--1\n;DROP TABLE t",
        "LINE_COMMENT_FORM",
        ALL,
        "-- not followed by space: MySQL code, PG comment",
    ),
    (
        "H49",
        "SELECT 1 -- x\r; DROP TABLE t",
        "LINE_COMMENT_FORM",
        ALL,
        "lone CR ends a PG comment but not a MySQL one: the ; is code in PG",
    ),
    (
        "H49b",
        "SELECT 1 -- x\r' \n; DROP TABLE t; -- '",
        "LINE_COMMENT_FORM",
        ALL,
        "same, quote-desync variant",
    ),
    (
        "H50",
        "SELECT $$ ; DROP TABLE t; $$",
        {
            "sqlite": "MULTIPLE_STATEMENTS",
            "mysql": "MULTIPLE_STATEMENTS",
            "mssql": "MULTIPLE_STATEMENTS",
            "oracle": "MULTIPLE_STATEMENTS",
            None: "DOLLAR",
        },
        ("sqlite", "mysql", "mssql", "oracle", None),
        "non-PG: $$ is identifier text so the ; is real",
    ),
    (
        "H51",
        "SELECT $a$ x $a$ ; DROP TABLE t",
        "MULTIPLE_STATEMENTS",
        ("postgresql",),
        "tagged dollar quote closes then ; DROP",
    ),
    ("H52", "SELECT $$ unterminated", "UNTERMINATED", ("postgresql",), "unterminated dollar quote"),
    ("H53", "SELECT\xa0* FROM t", "CODE_CHARACTER", ALL, "NBSP outside literal"),
    ("H54", "SELECT 1;\u200bDROP TABLE t", "CODE_CHARACTER", ALL, "ZWSP between ; and DROP"),
    ("H55", "\u200bSELECT 1", "CODE_CHARACTER", ALL, "leading ZWSP"),
    ("H56", "SELECT 1\x00; DROP TABLE t", "NUL", ALL, "NUL byte"),
    ("H57", "SELECT 'a\x00b'", "NUL", ALL, "NUL inside literal"),
    ("H58", "SELECT\x0b1", "CODE_CHARACTER", ALL, "vertical tab"),
    ("H59", "SELECT\x01 1", "CODE_CHARACTER", ALL, "control character"),
    ("H60", "SELECT nextval('s')", "SIDE_EFFECT_FUNCTION", ALL, "PG sequence advance"),
    ("H61", "SELECT setval('s', 1)", "SIDE_EFFECT_FUNCTION", ALL, "PG sequence set"),
    (
        "H62",
        "SELECT set_config('default_transaction_read_only','off',false)",
        "SIDE_EFFECT_FUNCTION",
        ALL,
        "PG session setting",
    ),
    ("H63", "SELECT pg_sleep(10)", "SIDE_EFFECT_FUNCTION", ALL, "PG delay"),
    ("H64", "SELECT pg_catalog.pg_sleep(10)", "SIDE_EFFECT_FUNCTION", ALL, "schema-qualified"),
    ("H65", 'SELECT "pg_sleep"(10)', "SIDE_EFFECT_FUNCTION", ALL, "quoted function name"),
    (
        "H66",
        "SELECT PG_SLEEP /* c */ (10)",
        "SIDE_EFFECT_FUNCTION",
        ALL,
        "comment between name and (",
    ),
    ("H67", "SELECT pg_read_file('/etc/passwd')", "SIDE_EFFECT_FUNCTION", ALL, "PG file read"),
    (
        "H68",
        "SELECT lo_import('/etc/passwd')",
        "SIDE_EFFECT_FUNCTION",
        ALL,
        "PG large object import",
    ),
    (
        "H69",
        "SELECT dblink_exec('dbname=x','DELETE FROM t')",
        "SIDE_EFFECT_FUNCTION",
        ALL,
        "PG dblink",
    ),
    ("H70", "SELECT pg_terminate_backend(123)", "SIDE_EFFECT_FUNCTION", ALL, "PG backend kill"),
    ("H71", "SELECT pg_advisory_lock(1)", "SIDE_EFFECT_FUNCTION", ALL, "PG advisory lock"),
    ("H72", "SELECT SLEEP(10)", "SIDE_EFFECT_FUNCTION", ALL, "MySQL delay"),
    ("H73", "SELECT GET_LOCK('a', 10)", "SIDE_EFFECT_FUNCTION", ALL, "MySQL named lock"),
    ("H74", "SELECT LOAD_FILE('/etc/passwd')", "SIDE_EFFECT_FUNCTION", ALL, "MySQL file read"),
    ("H75", "SELECT BENCHMARK(100000000, MD5('a'))", "SIDE_EFFECT_FUNCTION", ALL, "MySQL CPU burn"),
    ("H76", "SELECT @a := 1", "ASSIGNMENT", ALL, "MySQL session variable assignment"),
    ("H77", "SELECT load_extension('x')", "SIDE_EFFECT_FUNCTION", ALL, "SQLite extension load"),
    ("H78", "SELECT writefile('f','x')", "SIDE_EFFECT_FUNCTION", ALL, "SQLite CLI fileio function"),
    (
        "H79",
        "SELECT optimize(ft) FROM ft",
        "SIDE_EFFECT_FUNCTION",
        ALL,
        "SQLite FTS3/4 optimize() writes",
    ),
    (
        "H80",
        "SELECT * FROM pragma_optimize",
        "PRAGMA_FUNCTION",
        ALL,
        "SQLite table-valued pragma that writes sqlite_stat1",
    ),
    ("H81", "SELECT * FROM PRAGMA_Optimize", "PRAGMA_FUNCTION", ALL, "case-insensitive"),
    ("H82", "SELECT 1 DELETE FROM t", "WRITE_KEYWORD", ALL, "T-SQL needs no ; between statements"),
    ("H83", "SELECT 1 EXEC xp_cmdshell 'dir'", "WRITE_KEYWORD", ALL, "T-SQL EXEC without ;"),
    (
        "H84",
        "SELECT * FROM OPENROWSET('SQLNCLI','x','DELETE FROM t')",
        "WRITE_KEYWORD",
        ALL,
        "T-SQL OPENROWSET",
    ),
    (
        "H85",
        "SELECT * FROM OPENQUERY(lnk, 'DELETE FROM t')",
        "WRITE_KEYWORD",
        ALL,
        "T-SQL OPENQUERY",
    ),
    (
        "H86",
        'SELECT U&"\\0070g_sleep"(1)',
        "PREFIXED_STRING",
        ALL,
        "PG unicode-escape identifier spells pg_sleep",
    ),
    ("H87", "SELECT q'[x'; DROP TABLE t; --]'", "PREFIXED_STRING", ALL, "Oracle q-quoted literal"),
    (
        "H87b",
        "SELECT q'[ ' ]'; DROP TABLE t; --'",
        "PREFIXED_STRING",
        ALL,
        "Oracle q-quote: literal ends at ]' so ; is code; a plain scanner hides it",
    ),
    ("H88", "COPY (SELECT 1) TO PROGRAM 'id'", "NOT_A_QUERY", ALL, "first token COPY"),
    (
        "H89",
        "( DELETE FROM t )",
        "NOT_A_QUERY",
        ALL,
        "parenthesis not followed by SELECT/WITH/VALUES",
    ),
    (
        "H90",
        "SELECT ARRAY[']'] ; DROP TABLE t; SELECT ARRAY[']']",
        {
            "sqlite": "UNTERMINATED",
            "postgresql": "MULTIPLE_STATEMENTS",
            "mysql": "MULTIPLE_STATEMENTS",
            "mssql": "UNTERMINATED",
            "oracle": "MULTIPLE_STATEMENTS",
            None: "BRACKET",
        },
        ALL,
        "bracket/quote desync attempt",
    ),
    (
        "H91",
        "SELECT 1 /*+ x */ ; INSERT INTO t VALUES (1)",
        "MULTIPLE_STATEMENTS",
        ALL,
        "hint comment then ;",
    ),
    (
        "H92",
        "SELECT `a``b` ; DROP TABLE t",
        "MULTIPLE_STATEMENTS",
        ALL,
        "backtick identifier with doubled backtick then ;",
    ),
    ("H93", "SELECT 1\r\n;\r\nDELETE FROM t", "MULTIPLE_STATEMENTS", ALL, "CRLF separated"),
    ("H94", "SELECT 1 1DELETE FROM t", "WRITE_KEYWORD", ALL, "digit-led token hiding a keyword"),
    ("H95", "SELECT /*!50000 1; */ 2", "EXECUTABLE_COMMENT", ALL, "executable comment before code"),
    (
        "H96",
        "/*! SELECT 1 */ DROP TABLE t",
        "EXECUTABLE_COMMENT",
        ALL,
        "executable comment at start",
    ),
    ("H97", "", "EMPTY", ALL, "empty string"),
    ("H98", "   -- only a comment", "EMPTY", ALL, "comment only"),
    (
        "H99",
        "SELECT 1 UNION ALL SELECT 2; EXPLAIN DELETE FROM t",
        "MULTIPLE_STATEMENTS",
        ALL,
        "stray statement after ;",
    ),
    (
        "H100",
        "TABLE t",
        "NOT_A_QUERY",
        ALL,
        "PG shorthand not in the allowlist (over-refusal by design)",
    ),
    ("H101", "SHOW TABLES", "NOT_A_QUERY", ALL, "not in allowlist"),
    (
        "H102",
        "SELECT INSERT('abc',1,1,'x')",
        "WRITE_KEYWORD",
        ALL,
        "MySQL INSERT() function (accepted over-refusal)",
    ),
    (
        "H103",
        "SELECT * FROM t WHERE x LIKE '%\\_%' ESCAPE '\\'",
        "BACKSLASH_QUOTE",
        ALL,
        "ESCAPE '\\' (accepted over-refusal: ambiguous)",
    ),
    (
        "H104",
        "SELECT a #> '{b}' FROM t",
        "HASH_COMMENT",
        ("sqlite", "mysql", "mssql", "oracle", None),
        "# operator refused outside PostgreSQL (accepted over-refusal)",
    ),
    (
        "H105",
        "SELECT pg_size_pretty(pg_total_relation_size('t'))",
        "SIDE_EFFECT_FUNCTION",
        ALL,
        "pg_ prefix (accepted over-refusal)",
    ),
    (
        "H106",
        "SELECT 1--comment",
        "LINE_COMMENT_FORM",
        ALL,
        "-- without space (accepted over-refusal)",
    ),
    (
        "H107",
        "SELECT t.delete FROM t",
        "WRITE_KEYWORD",
        ALL,
        "keyword after a dot (accepted over-refusal)",
    ),
    ("H108", "SELECT [a] FROM t", "BRACKET", (None,), "bracket in an unknown dialect"),
    ("H109", "SELECT '\ud800'", "NOT_UTF8", ALL, "lone surrogate cannot be UTF-8 encoded"),
    (
        "H110",
        "SELECT $x FROM t",
        "DOLLAR",
        (None,),
        "$name in an unknown dialect may open a dollar quote",
    ),
    # Added after a mutation check (each of these rules was reachable by no case that it alone
    # explains: another rule refused the same text first, or no case reached it at all).
    ("H111", "SELECT 'abc\\", "UNTERMINATED", ALL, "a backslash as the last character"),
    ("H112", "SELECT `abc", "UNTERMINATED", ALL, "unterminated backtick identifier"),
    (
        "H113",
        "SELECT [abc",
        "UNTERMINATED",
        ("sqlite", "mssql"),
        "unterminated bracket identifier",
    ),
    (
        "H114",
        "SELECT 1 FROM t REPLACE x",
        "WRITE_KEYWORD",
        ALL,
        "REPLACE as a statement word, with no INTO behind it to refuse it first",
    ),
    (
        "H115",
        "SELECT 1 FROM t TRUNCATE x",
        "WRITE_KEYWORD",
        ALL,
        "TRUNCATE as a statement word",
    ),
    (
        "H116",
        "SELECT [a]]; DROP TABLE t; --] FROM t",
        "LINE_COMMENT_FORM",
        ("sqlite",),
        "SQLite does not double ]], so B65's text ends the identifier early and the rest is code",
    ),
    (
        "H117",
        'SELECT * FROM "pragma_optimize"',
        "PRAGMA_FUNCTION",
        ALL,
        "SQLite resolves a double-quoted table function like the bare one (found in review)",
    ),
    (
        "H118",
        "SELECT * FROM `pragma_optimize`",
        "PRAGMA_FUNCTION",
        ALL,
        "backtick-quoted",
    ),
    (
        "H119",
        "SELECT * FROM 'pragma_optimize'",
        "PRAGMA_FUNCTION",
        ALL,
        "a single-quoted name, which SQLite also accepts as an identifier",
    ),
    (
        "H120",
        'SELECT * FROM "PRAGMA_OPTIMIZE"',
        "PRAGMA_FUNCTION",
        ALL,
        "case-insensitive when quoted",
    ),
    (
        "H121",
        'SELECT * FROM main."pragma_optimize"(0x10002)',
        "PRAGMA_FUNCTION",
        ALL,
        "schema-qualified and called with its argument",
    ),
    (
        "H122",
        "SELECT * FROM [pragma_optimize]",
        {
            "sqlite": "PRAGMA_FUNCTION",
            "postgresql": "PRAGMA_FUNCTION",
            "mysql": "PRAGMA_FUNCTION",
            "mssql": "PRAGMA_FUNCTION",
            "oracle": "PRAGMA_FUNCTION",
            None: "BRACKET",
        },
        ALL,
        "bracket-quoted on SQLite; elsewhere the word is bare after a subscript; unknown: BRACKET",
    ),
    (
        "H123",
        'SELECT 1 AS "Pragma_x"',
        "PRAGMA_FUNCTION",
        ALL,
        "accepted over-refusal: any quoted name beginning pragma_, even an alias",
    ),
]


def _benign_params() -> list[Any]:
    return [
        pytest.param(sql, dialect, id=f"{case_id}-{dialect}")
        for case_id, sql, dialects, _why in BENIGN
        for dialect in dialects
    ]


def _hostile_params() -> list[Any]:
    params = []
    for case_id, sql, code, dialects, _why in HOSTILE:
        for dialect in dialects:
            expected = code[dialect] if isinstance(code, dict) else code
            params.append(pytest.param(sql, dialect, expected, id=f"{case_id}-{dialect}"))
    return params


@pytest.mark.parametrize("dialect", ALL, ids=str)
@pytest.mark.parametrize("sql", _REPO_SQL)
def test_the_sql_this_repository_runs_passes(sql: str, dialect: str | None) -> None:
    check_read_only_sql(sql, dialect)


@pytest.mark.parametrize(("sql", "dialect"), _benign_params())
def test_a_read_only_query_passes(sql: str, dialect: str | None) -> None:
    check_read_only_sql(sql, dialect)


@pytest.mark.parametrize(("sql", "dialect", "code"), _hostile_params())
def test_a_statement_that_could_write_is_refused_by_the_rule_that_names_it(
    sql: str, dialect: str | None, code: str
) -> None:
    with pytest.raises(ReadOnlyViolation) as caught:
        check_read_only_sql(sql, dialect)
    assert caught.value.code == code


@pytest.mark.parametrize("value", [None, 5, b"SELECT 1", ["SELECT 1"], object()])
def test_something_that_is_not_text_is_refused(value: Any) -> None:
    with pytest.raises(ReadOnlyViolation) as caught:
        check_read_only_sql(value, "sqlite")
    assert caught.value.code == "NOT_TEXT"


# The three lists below are typed out here, not read from the module, on purpose: a word taken off
# the module's list must fail a test, so loosening the gate takes two edits and a reviewer's eye.
WRITE_WORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "UPSERT",
    "DROP",
    "CREATE",
    "ALTER",
    "RENAME",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "VACUUM",
    "REINDEX",
    "COPY",
    "CALL",
    "DO",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "REVOKE",
    "DENY",
    "SET",
    "DECLARE",
    "USE",
    "LOAD",
    "HANDLER",
    "PREPARE",
    "DEALLOCATE",
    "LISTEN",
    "NOTIFY",
    "UNLISTEN",
    "DISCARD",
    "CLUSTER",
    "REFRESH",
    "BACKUP",
    "RESTORE",
    "SHUTDOWN",
    "KILL",
    "DBCC",
    "BULK",
    "OPENROWSET",
    "OPENQUERY",
    "OPENDATASOURCE",
    "OPENXML",
    "WAITFOR",
    "INTO",
]
SIDE_EFFECT_FUNCTIONS = [
    "nextval",
    "setval",
    "set_config",
    "sleep",
    "benchmark",
    "get_lock",
    "release_lock",
    "release_all_locks",
    "load_file",
    "load_extension",
    "writefile",
    "readfile",
    "optimize",
    "fts3_tokenizer",
    "edit",
]
SIDE_EFFECT_PREFIXES = ["pg_", "lo_", "dblink", "xp_", "sp_", "utl_", "dbms_"]


@pytest.mark.parametrize("word", WRITE_WORDS)
def test_each_write_word_is_refused_wherever_it_stands_in_code(word: str) -> None:
    for sql in (f"SELECT 1 FROM t {word} x", f"WITH c AS (SELECT 1) {word.lower()} x"):
        with pytest.raises(ReadOnlyViolation) as caught:
            check_read_only_sql(sql, "sqlite")
        assert caught.value.code == "WRITE_KEYWORD"


@pytest.mark.parametrize("word", ["REPLACE", "TRUNCATE"])
def test_replace_and_truncate_are_refused_as_statements_and_allowed_as_functions(
    word: str,
) -> None:
    check_read_only_sql(f"SELECT {word}(a, 2) FROM t", "mysql")
    check_read_only_sql(f"SELECT {word} (a, 2) FROM t", "mysql")
    with pytest.raises(ReadOnlyViolation) as caught:
        check_read_only_sql(f"SELECT 1 FROM t {word} t", "mysql")
    assert caught.value.code == "WRITE_KEYWORD"


@pytest.mark.parametrize("name", SIDE_EFFECT_FUNCTIONS)
def test_each_side_effect_function_is_refused_when_it_is_called(name: str) -> None:
    for sql in (f"SELECT {name}(1)", f"SELECT {name.upper()} (1)", f'SELECT "{name}"(1)'):
        with pytest.raises(ReadOnlyViolation) as caught:
            check_read_only_sql(sql, "sqlite")
        assert caught.value.code == "SIDE_EFFECT_FUNCTION"
    check_read_only_sql(f"SELECT {name} FROM t", "sqlite")  # a column of that name is not a call


@pytest.mark.parametrize("prefix", SIDE_EFFECT_PREFIXES)
def test_each_side_effect_prefix_is_refused_when_it_is_called(prefix: str) -> None:
    with pytest.raises(ReadOnlyViolation) as caught:
        check_read_only_sql(f"SELECT {prefix}anything(1)", "sqlite")
    assert caught.value.code == "SIDE_EFFECT_FUNCTION"
    check_read_only_sql(f"SELECT {prefix}anything FROM t", "sqlite")


def test_every_rule_has_a_hostile_case_that_names_it() -> None:
    named = {"NOT_TEXT"}
    for _case_id, _sql, code, _dialects, _why in HOSTILE:
        named |= {code} if isinstance(code, str) else set(code.values())
    assert named == set(read_only_gate._REASONS)


def test_the_cases_cover_every_dialect_the_gate_has_facts_for() -> None:
    assert {d for _id, _sql, dialects, _why in BENIGN for d in dialects} == set(ALL)
    assert {d for _id, _sql, _code, dialects, _why in HOSTILE for d in dialects} == set(ALL)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1 AS {m}; DROP TABLE t",
        "DROP TABLE {m}",
        "SELECT pg_sleep_{m}(1)",
        "SELECT {m} INTO t FROM u",
        "SELECT '{m}",
        "SELECT 1 FROM {m} FOR UPDATE",
    ],
)
def test_a_refusal_never_quotes_the_sql(sql: str) -> None:
    marker = "marker_8c1f3a"
    with pytest.raises(ReadOnlyViolation) as caught:
        check_read_only_sql(sql.format(m=marker), "postgresql")
    assert marker not in str(caught.value)
    assert f"({caught.value.code})" in str(caught.value)


@pytest.mark.parametrize(
    "copier", [copy.copy, copy.deepcopy, lambda e: pickle.loads(pickle.dumps(e))]
)
def test_a_violation_survives_copy_and_pickle(copier: Any) -> None:
    original = ReadOnlyViolation("NUL")
    rebuilt = copier(original)
    assert isinstance(rebuilt, ReadOnlyViolation)
    assert rebuilt.code == "NUL"
    assert str(rebuilt) == str(original)


def test_a_violation_is_a_value_error_that_carries_its_code() -> None:
    with pytest.raises(ValueError, match=r"read-only gate \(NOT_A_QUERY\)") as caught:
        check_read_only_sql("DELETE FROM t", "sqlite")
    assert isinstance(caught.value, ReadOnlyViolation)
    assert caught.value.code == "NOT_A_QUERY"


def test_the_dialect_name_is_read_without_regard_to_case() -> None:
    check_read_only_sql("SELECT [a] FROM t", "SQLITE")
    check_read_only_sql("SELECT $$x$$", "PostgreSQL")


@pytest.mark.parametrize("dialect", [None, "", "snowflake", "duckdb", "cockroachdb"])
def test_a_dialect_with_no_lexer_facts_gets_the_strictest_reading(dialect: str | None) -> None:
    for sql, code in (("SELECT [a] FROM t", "BRACKET"), ("SELECT $$x$$", "DOLLAR")):
        with pytest.raises(ReadOnlyViolation) as caught:
            check_read_only_sql(sql, dialect)
        assert caught.value.code == code
    check_read_only_sql("SELECT 1", dialect)
