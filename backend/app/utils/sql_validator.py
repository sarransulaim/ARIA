import re
from typing import Optional, Tuple

import sqlglot
from sqlglot import exp

# AST node types that represent write / DDL operations
_BLOCKED_NODE_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.TruncateTable,
    exp.Command,   # catches dialect-specific raw commands
)

# Regex guard: matches when the first real token of a statement is a write keyword.
# Used as a second layer in case sqlglot silently skips an unknown dialect construct.
_WRITE_KEYWORD_RE = re.compile(
    r"^\s*(?:INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|REPLACE)\b",
    re.IGNORECASE,
)


def validate_sql(
    sql: str,
    read_only: bool = True,
    dialect: str = "postgres",
) -> Tuple[bool, Optional[str]]:
    """
    Parse and validate SQL.

    Returns (is_valid, error_message).  error_message is None when valid.
    In read_only mode, any DDL or DML write statement is rejected.
    """
    if not sql or not sql.strip():
        return False, "SQL cannot be empty"

    # Regex fast-path before paying sqlglot parse cost
    if read_only and _WRITE_KEYWORD_RE.match(sql):
        match = _WRITE_KEYWORD_RE.match(sql)
        keyword = match.group(0).strip().split()[0].upper()
        return False, f"Statement not permitted on a read-only connection: {keyword}"

    try:
        statements = sqlglot.parse(sql, dialect=dialect, error_level=sqlglot.ErrorLevel.RAISE)
    except sqlglot.errors.ParseError as exc:
        return False, f"SQL parse error: {exc}"

    if not statements:
        return False, "No valid SQL statements found"

    if read_only:
        for stmt in statements:
            if stmt is None:
                continue
            for node in stmt.walk():
                if isinstance(node, _BLOCKED_NODE_TYPES):
                    return (
                        False,
                        f"Statement not permitted on a read-only connection: {type(node).__name__}",
                    )

    return True, None
