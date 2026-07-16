from typing import Any

from app.agents.answer_generator import generate_natural_language_answer
from app.agents.query_planner import create_query_plan
from app.agents.result_verifier import verify_result
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




def verify_query_result_node(
    state: NLToSQLState,
) -> dict[str, Any]:
    result = state.get("result")

    if not result:
        verification = {
            "is_valid": False,
            "confidence": 0.0,
            "failure_category": "null_result",
            "reason": (
                "No executed result was available "
                "for semantic verification."
            ),
            "repair_instructions": [
                "Execute the generated SQL before verification."
            ],
        }
    else:
        verification = verify_result(
            question=state.get("question", ""),
            evidence=state.get("evidence", ""),
            query_plan=state.get("query_plan", {}),
            generated_sql=state.get("generated_sql", ""),
            result=result,
        )

    history = list(state.get("attempt_history", []))

    history.append(
        {
            "attempt": state.get("attempt_count", 0),
            "type": "result_verification",
            "is_valid": verification.get(
                "is_valid",
                False,
            ),
            "confidence": verification.get(
                "confidence",
                0.0,
            ),
            "failure_category": verification.get(
                "failure_category"
            ),
            "reason": verification.get("reason"),
            "repair_instructions": verification.get(
                "repair_instructions",
                [],
            ),
        }
    )

    is_valid = verification.get("is_valid", False)

    return {
        "result_verification": verification,
        "semantic_repair_instructions": verification.get(
            "repair_instructions",
            [],
        ),
        "attempt_history": history,
        "status": (
            "result_verified"
            if is_valid
            else "semantic_verification_failed"
        ),
        "failure_category": (
            None
            if is_valid
            else verification.get(
                "failure_category",
                "semantic_mismatch",
            )
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

    result_verification = state.get("result_verification", {})
    semantic_reason = result_verification.get("reason")
    semantic_instructions = state.get(
        "semantic_repair_instructions",
        [],
    )

    if semantic_reason:
        error_parts.append(
            f"Semantic verification failure: {semantic_reason}"
        )

    if semantic_instructions:
        error_parts.append(
            "Semantic repair instructions:\n- "
            + "\n- ".join(semantic_instructions)
        )

    error_message = "\n".join(error_parts) or "Unknown SQL failure."

    failure_category = (
        result_verification.get("failure_category")
        or classify_failure(
            validation=validation,
            execution_error=execution_error,
        )
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
            "result_verification": {},
            "semantic_repair_instructions": [],
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



def route_after_result_verification(
    state: NLToSQLState,
) -> str:
    verification = state.get("result_verification", {})

    if verification.get("is_valid", False):
        return "answer"

    if state.get("attempt_count", 0) < MAX_ATTEMPTS:
        return "repair"

    return "answer"
