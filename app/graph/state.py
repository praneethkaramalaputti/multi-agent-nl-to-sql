from typing import Any, TypedDict


class NLToSQLState(TypedDict, total=False):
    question: str
    evidence: str
    schema: str
    query_plan: dict[str, Any]
    generated_sql: str
    validation: dict[str, Any]
    result: dict[str, Any] | None
    natural_language_answer: str
    execution_error: str | None
    failure_category: str | None
    status: str
    attempt_count: int
    attempt_history: list[dict[str, Any]]
