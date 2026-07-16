import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama


MODEL_NAME = "qwen2.5-coder:7b"


def verify_result(
    *,
    question: str,
    query_plan: dict[str, Any],
    generated_sql: str,
    result: dict[str, Any],
    evidence: str = "",
) -> dict[str, Any]:
    rows = result.get("rows", [])
    columns = result.get("columns", [])
    row_count = result.get("row_count", len(rows))

    model = ChatOllama(
        model=MODEL_NAME,
        temperature=0,
        format="json",
    )

    system_prompt = """
You are a semantic verifier for a natural-language-to-SQL system.

Your task is to determine whether the executed SQL result plausibly answers
the user's question.

Check all of the following:

1. The SQL selects the information requested by the user.
2. Required filters appear to be present.
3. The output granularity is correct:
   - one scalar when a scalar is requested
   - grouped rows when categories are requested
   - patient-level rows when patient records are requested
4. Requested columns are present.
5. The result does not appear to contain accidental duplicate entities.
6. Aggregations, ratios, percentages, minimums, maximums, and date filters
   appear semantically appropriate.
7. Empty results are only accepted when they are plausible.
8. The result is consistent with the query plan and supplied evidence.
9. SQL execution success alone does not mean semantic correctness.

Return valid JSON only with this structure:

{
  "is_valid": true,
  "confidence": 0.0,
  "failure_category": null,
  "reason": "Brief explanation",
  "repair_instructions": []
}

Allowed failure_category values:

- missing_filter
- wrong_aggregation
- wrong_granularity
- missing_requested_column
- duplicate_entities
- implausible_empty_result
- incorrect_join
- incorrect_date_logic
- incorrect_percentage_or_ratio
- query_plan_mismatch
- semantic_mismatch
- null_result
- unknown

When is_valid is false, provide specific repair instructions.
Do not invent database values.
"""

    user_payload = {
        "question": question,
        "evidence": evidence,
        "query_plan": query_plan,
        "generated_sql": generated_sql,
        "result": {
            "columns": columns,
            "row_count": row_count,
            "rows": rows[:20],
            "truncated": result.get("truncated", False),
        },
    }

    response = model.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=json.dumps(
                    user_payload,
                    ensure_ascii=False,
                    default=str,
                )
            ),
        ]
    )

    try:
        verification = json.loads(response.content)
    except json.JSONDecodeError as error:
        return {
            "is_valid": False,
            "confidence": 0.0,
            "failure_category": "unknown",
            "reason": (
                "The verifier did not return valid JSON: "
                f"{error}"
            ),
            "repair_instructions": [
                "Review the SQL and result manually.",
                "Regenerate the query using the original question and plan.",
            ],
        }

    return {
        "is_valid": bool(
            verification.get("is_valid", False)
        ),
        "confidence": float(
            verification.get("confidence", 0.0)
        ),
        "failure_category": verification.get(
            "failure_category"
        ),
        "reason": verification.get(
            "reason",
            "No verifier explanation was provided.",
        ),
        "repair_instructions": verification.get(
            "repair_instructions",
            [],
        ),
    }


if __name__ == "__main__":
    sample_verification = verify_result(
        question="How many patients are there for each sex?",
        query_plan={
            "intent": "Count patients grouped by sex",
            "tables": ["Patient"],
        },
        generated_sql=(
            'SELECT "SEX", COUNT("ID") AS patient_count '
            'FROM "Patient" GROUP BY "SEX";'
        ),
        result={
            "columns": ["SEX", "patient_count"],
            "rows": [
                {"SEX": "F", "patient_count": 1023},
                {"SEX": "M", "patient_count": 202},
                {"SEX": None, "patient_count": 13},
            ],
            "row_count": 3,
            "truncated": False,
        },
    )

    print(
        json.dumps(
            sample_verification,
            indent=2,
        )
    )
