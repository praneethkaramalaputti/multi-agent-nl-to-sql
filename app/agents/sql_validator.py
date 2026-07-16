from typing import Any
import sqlite3

import sqlglot
from sqlglot import expressions as exp

from app.database.safe_executor import (
    UnsafeQueryError,
    validate_read_only_sql,
)
from app.database.schema_loader import DATABASE_PATH


def get_database_schema_map() -> dict[str, set[str]]:
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    try:
        tables = cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            """
        ).fetchall()

        schema_map: dict[str, set[str]] = {}

        for (table_name,) in tables:
            columns = cursor.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()

            schema_map[table_name] = {
                column[1] for column in columns
            }

        return schema_map

    finally:
        connection.close()


def has_safe_real_division(parsed: exp.Expression) -> bool:
    """
    Return True when division includes an explicit REAL/FLOAT/DOUBLE cast
    or multiplication by a decimal literal such as 1.0 or 100.0.
    """
    for division in parsed.find_all(exp.Div):
        division_sql = division.sql(dialect="sqlite").upper()

        if any(
            token in division_sql
            for token in (
                "CAST(",
                " AS REAL",
                " AS FLOAT",
                " AS DOUBLE",
                "1.0",
                "100.0",
            )
        ):
            continue

        return False

    return True


def validate_sql(sql: str) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        validate_read_only_sql(sql)
    except (ValueError, UnsafeQueryError) as error:
        errors.append(str(error))

        return {
            "is_valid": False,
            "errors": errors,
            "warnings": warnings,
            "tables": [],
            "columns": [],
        }

    try:
        parsed = sqlglot.parse_one(sql, read="sqlite")
    except sqlglot.errors.ParseError as error:
        errors.append(f"SQL parsing failed: {error}")

        return {
            "is_valid": False,
            "errors": errors,
            "warnings": warnings,
            "tables": [],
            "columns": [],
        }

    schema_map = get_database_schema_map()

    referenced_tables = {
        table.name
        for table in parsed.find_all(exp.Table)
    }

    referenced_columns = {
        column.name
        for column in parsed.find_all(exp.Column)
    }

    for table_name in referenced_tables:
        if table_name not in schema_map:
            errors.append(
                f'Table "{table_name}" does not exist.'
            )

    known_columns = {
        column_name
        for columns in schema_map.values()
        for column_name in columns
    }

    for column_name in referenced_columns:
        if column_name not in known_columns:
            errors.append(
                f'Column "{column_name}" does not exist.'
            )

    if list(parsed.find_all(exp.Div)) and not has_safe_real_division(parsed):
        errors.append(
            "Division may use SQLite integer arithmetic. "
            "Cast the numerator or denominator to REAL, or multiply "
            "by a decimal value such as 100.0 before division."
        )

    if not referenced_tables:
        warnings.append(
            "The query does not reference a database table."
        )

    if not list(parsed.find_all(exp.Limit)):
        warnings.append(
            "The query has no LIMIT clause. "
            "The executor will still restrict returned rows."
        )

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "tables": sorted(referenced_tables),
        "columns": sorted(referenced_columns),
    }


if __name__ == "__main__":
    safe_division_sql = """
    SELECT CAST(COUNT(*) AS REAL) / 10
    FROM "Patient"
    """

    unsafe_division_sql = """
    SELECT COUNT(*) / 10
    FROM "Patient"
    """

    print("SAFE DIVISION TEST")
    print(validate_sql(safe_division_sql))

    print("\nUNSAFE DIVISION TEST")
    print(validate_sql(unsafe_division_sql))
