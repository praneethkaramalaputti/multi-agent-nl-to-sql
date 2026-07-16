from typing import Any

from app.agents.answer_generator import generate_natural_language_answer
from app.agents.query_planner import create_query_plan
from app.agents.sql_generator import generate_sql
from app.agents.sql_repair import repair_sql
from app.agents.sql_validator import validate_sql
from app.database.safe_executor import execute_safe_query
from app.database.schema_loader import load_database_schema
from app.evaluation.failure_classifier import classify_failure
from app.graph.state import NLToSQLState


MAX_ATTEMPTS = 3


def load_schema_node(state: NLToSQLState) -> dict[str, Any]:
    return {
        "schema": load_database_schema(),
        "status": "schema_loaded",
    }


def create_query_plan_node(state: NLToSQLState) -> dict[str, Any]:
    question = state.get("question", "").strip()

    if not question:
        return {
            "query_plan": {},
            "status": "planning_failed",
            "execution_error": "Question cannot be empty.",
            "failure_category": "empty_question",
        }

    try:
        query_plan = create_query_plan(
            question,
            state.get("evidence", ""),
        )

        return {
            "query_plan": query_plan,
            "status": "query_planned",
            "execution_error": None,
            "failure_category": None,
        }

    except Exception as error:
        return {
            "query_plan": {},
            "status": "planning_failed",
            "execution_error": str(error),
            "failure_category": "planning_error",
        }


def generate_sql_node(state: NLToSQLState) -> dict[str, Any]:
    question = state.get("question", "").strip()

    if not question:
        return {
            "status": "generation_failed",
            "execution_error": "Question cannot be empty.",
            "failure_category": "empty_question",
        }

    try:
        generated_sql = generate_sql(
            question,
            state.get("query_plan", {}),
            state.get("evidence", ""),
        )

        next_attempt = state.get("attempt_count", 0) + 1
        history = list(state.get("attempt_history", []))

        history.append(
            {
                "attempt": next_attempt,
                "type": "generation",
                "sql": generated_sql,
            }
        )

        return {
            "generated_sql": generated_sql,
            "attempt_count": next_attempt,
            "attempt_history": history,
            "status": "sql_generated",
            "execution_error": None,
            "failure_category": None,
        }

    except Exception as error:
        return {
            "status": "generation_failed",
            "execution_error": str(error),
            "failure_category": "generation_error",
        }


def validate_sql_node(state: NLToSQLState) -> dict[str, Any]:
    generated_sql = state.get("generated_sql", "")

    if not generated_sql:
        validation = {
            "is_valid": False,
            "errors": ["No SQL query was generated."],
            "warnings": [],
            "tables": [],
            "columns": [],
        }
    else:
        validation = validate_sql(generated_sql)

    failure_category = classify_failure(
        validation=validation,
        execution_error=None,
    )

    return {
        "validation": validation,
        "failure_category": failure_category,
        "status": (
            "sql_validated"
            if validation["is_valid"]
            else "validation_failed"
        ),
    }


def execute_sql_node(state: NLToSQLState) -> dict[str, Any]:
    try:
        result = execute_safe_query(
            state.get("generated_sql", "")
        )

        return {
            "result": result,
            "status": "success",
            "execution_error": None,
            "failure_category": None,
        }

    except Exception as error:
        error_message = str(error)

        return {
            "result": None,
            "status": "execution_failed",
            "execution_error": error_message,
            "failure_category": classify_failure(
                validation=state.get("validation", {}),
                execution_error=error_message,
            ),
        }



def generate_answer_node(state: NLToSQLState) -> dict[str, Any]:
    try:
        answer = generate_natural_language_answer(
            question=state.get("question", ""),
            generated_sql=state.get("generated_sql", ""),
            result=state.get("result"),
        )

        return {
            "natural_language_answer": answer,
            "status": "success",
        }

    except Exception as error:
        return {
            "natural_language_answer": (
                "The SQL query executed successfully, "
                "but the answer explanation could not be generated."
            ),
            "status": "success",
            "execution_error": str(error),
        }


def repair_sql_node(state: NLToSQLState) -> dict[str, Any]:
    validation = state.get("validation", {})
    validation_errors = validation.get("errors", [])
    execution_error = state.get("execution_error")

    error_parts = list(validation_errors)

    if execution_error:
        error_parts.append(execution_error)

    error_message = "\n".join(error_parts) or "Unknown SQL failure."
    failure_category = classify_failure(
        validation=validation,
        execution_error=execution_error,
    )

    try:
        repaired_sql = repair_sql(
            question=state.get("question", ""),
            failed_sql=state.get("generated_sql", ""),
            error_message=error_message,
            evidence=state.get("evidence", ""),
        )

        next_attempt = state.get("attempt_count", 0) + 1
        history = list(state.get("attempt_history", []))

        history.append(
            {
                "attempt": next_attempt,
                "type": "repair",
                "failure_category": failure_category,
                "failed_sql": state.get("generated_sql", ""),
                "error": error_message,
                "sql": repaired_sql,
            }
        )

        return {
            "generated_sql": repaired_sql,
            "attempt_count": next_attempt,
            "attempt_history": history,
            "validation": {},
            "execution_error": None,
            "failure_category": None,
            "result": None,
            "status": "sql_repaired",
        }

    except Exception as error:
        return {
            "status": "repair_failed",
            "execution_error": str(error),
            "failure_category": failure_category or "repair_error",
        }


def route_after_validation(state: NLToSQLState) -> str:
    validation = state.get("validation", {})

    if validation.get("is_valid", False):
        return "execute"

    if state.get("attempt_count", 0) < MAX_ATTEMPTS:
        return "repair"

    return "stop"


def route_after_execution(state: NLToSQLState) -> str:
    if state.get("status") == "success":
        return "stop"

    if state.get("attempt_count", 0) < MAX_ATTEMPTS:
        return "repair"

    return "stop"
