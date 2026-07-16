import sqlite3
from typing import Any

import sqlglot
from sqlglot import expressions as exp

from app.database.schema_loader import DATABASE_PATH


class UnsafeQueryError(ValueError):
    """Raised when a query contains an unsafe SQL operation."""


def validate_read_only_sql(sql: str) -> None:
    if not sql or not sql.strip():
        raise ValueError("SQL query cannot be empty.")

    try:
        statements = sqlglot.parse(sql, read="sqlite")
    except sqlglot.errors.ParseError as error:
        raise ValueError(f"Invalid SQL syntax: {error}") from error

    if len(statements) != 1:
        raise UnsafeQueryError(
            "Only one SQL statement may be executed at a time."
        )

    statement = statements[0]

    blocked_expression_types = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Create,
        exp.Alter,
        exp.Command,
        exp.Merge,
    )

    for blocked_type in blocked_expression_types:
        if statement.find(blocked_type):
            raise UnsafeQueryError(
                f"Blocked SQL operation: {blocked_type.__name__}"
            )

    if not isinstance(statement, (exp.Select, exp.Union)):
        raise UnsafeQueryError(
            "Only SELECT queries and read-only set operations are allowed."
        )


def execute_safe_query(
    sql: str,
    max_rows: int = 100,
) -> dict[str, Any]:
    validate_read_only_sql(sql)

    connection = sqlite3.connect(
        f"file:{DATABASE_PATH}?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()
        cursor.execute(sql)

        columns = [
            description[0]
            for description in cursor.description or []
        ]

        rows = cursor.fetchmany(max_rows + 1)
        truncated = len(rows) > max_rows
        rows = rows[:max_rows]

        return {
            "columns": columns,
            "rows": [dict(row) for row in rows],
            "row_count": len(rows),
            "truncated": truncated,
        }

    except sqlite3.Error as error:
        raise RuntimeError(
            f"Database execution failed: {error}"
        ) from error

    finally:
        connection.close()


if __name__ == "__main__":
    test_sql = """
    SELECT
        "SEX",
        COUNT(*) AS patient_count
    FROM "Patient"
    GROUP BY "SEX"
    ORDER BY patient_count DESC
    """

    result = execute_safe_query(test_sql)

    print("Columns:", result["columns"])
    print("Rows:", result["rows"])
    print("Row count:", result["row_count"])
    print("Truncated:", result["truncated"])
