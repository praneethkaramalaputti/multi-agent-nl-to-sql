from typing import Any


def classify_failure(
    validation: dict[str, Any] | None = None,
    execution_error: str | None = None,
) -> str | None:
    validation = validation or {}
    errors = validation.get("errors", [])

    combined_error = " ".join(errors)

    if execution_error:
        combined_error = f"{combined_error} {execution_error}".strip()

    normalized = combined_error.lower()

    if not normalized:
        return None

    if (
        "integer arithmetic" in normalized
        or "cast the numerator" in normalized
        or "decimal value" in normalized
    ):
        return "integer_division_error"

    if "table" in normalized and "does not exist" in normalized:
        return "invalid_table"

    if "column" in normalized and "does not exist" in normalized:
        return "invalid_column"

    if "syntax" in normalized or "parse" in normalized:
        return "sql_syntax_error"

    if "ambiguous column" in normalized:
        return "ambiguous_column"

    if "no such table" in normalized:
        return "invalid_table"

    if "no such column" in normalized:
        return "invalid_column"

    if "join" in normalized:
        return "join_error"

    if "blocked sql operation" in normalized:
        return "unsafe_query"

    if "only select" in normalized:
        return "unsafe_query"

    if "database execution failed" in normalized:
        return "execution_error"

    return "unknown_failure"


if __name__ == "__main__":
    test_cases = [
        {
            "validation": {
                "errors": ['Column "PatientID" does not exist.']
            },
            "execution_error": None,
        },
        {
            "validation": {
                "errors": ['Table "Patients" does not exist.']
            },
            "execution_error": None,
        },
        {
            "validation": {
                "errors": ["Invalid SQL syntax"]
            },
            "execution_error": None,
        },
        {
            "validation": {},
            "execution_error": (
                "Database execution failed: ambiguous column name: ID"
            ),
        },
        {
            "validation": {
                "errors": [
                    "Division may use SQLite integer arithmetic. "
                    "Cast the numerator or denominator to REAL."
                ]
            },
            "execution_error": None,
        },
    ]

    for index, test_case in enumerate(test_cases, start=1):
        category = classify_failure(
            validation=test_case["validation"],
            execution_error=test_case["execution_error"],
        )

        print(f"Test {index}: {category}")
