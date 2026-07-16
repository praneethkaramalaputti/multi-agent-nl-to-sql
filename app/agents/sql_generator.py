import json
import re
from typing import Any

import ollama

from app.database.schema_loader import load_database_schema


MODEL_NAME = "qwen2.5-coder:7b"


def extract_sql(response_text: str) -> str:
    fenced_match = re.search(
        r"```(?:sql)?\s*(.*?)```",
        response_text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if fenced_match:
        return fenced_match.group(1).strip().rstrip(";") + ";"

    select_match = re.search(
        r"\bSELECT\b.*",
        response_text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not select_match:
        raise ValueError(
            "The model response did not contain a SELECT query."
        )

    return select_match.group(0).strip().rstrip(";") + ";"


def generate_sql(
    question: str,
    query_plan: dict[str, Any] | None = None,
    evidence: str = "",
) -> str:
    if not question.strip():
        raise ValueError("Question cannot be empty.")

    schema = load_database_schema()
    plan_text = json.dumps(query_plan or {}, indent=2)
    evidence_text = evidence.strip() or "No external evidence provided."

    prompt = f"""
You are an expert SQLite query-generation agent.

Convert the user's question into exactly one valid, read-only SQLite
SELECT query.

Rules:
1. Use only tables and columns listed in the database schema.
2. Follow the query plan unless it conflicts with the schema.
3. Use the external evidence to resolve terminology, values, and formulas.
4. Do not ignore calculations explicitly described in the evidence.
5. Quote every table and column name using double quotes.
6. Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or PRAGMA.
7. Use "ID" to join healthcare tables when required.
8. Do not invent medical definitions or filtering rules.
9. Return only SQL without explanations or Markdown.
10. Use SQLite-compatible syntax.
11. Use CAST(... AS REAL) when division must produce a decimal value.
12. Return one scalar row when the question requests one percentage,
    ratio, average, total, difference, maximum, or minimum.
13. Do not add GROUP BY when calculating one overall scalar value.
14. Do not select category columns unless the user requests separate
    results for each category.
15. Add GROUP BY only when the user explicitly asks for results per
    category, by category, or for each category.
16. Before returning SQL, verify that every selected non-aggregate
    column is required by the user's requested output.
17. When calculating a ratio between two conditional counts, calculate
    both counts over the same ungrouped filtered row set.
18. Use SELECT DISTINCT when returning entities such as patients,
    doctors, or examinations from a one-to-many join and multiple
    matching child records could duplicate the same entity.
19. When the question says "list patients", return each patient only
    once unless repeated records are explicitly requested.
20. Laboratory can contain multiple rows for the same patient ID because
    laboratory measurements are recorded on different dates.
21. Examination may also contain multiple records for an ID. Prevent
    duplicate patient rows when only patient details are requested.

DATABASE SCHEMA:
{schema}

EXTERNAL EVIDENCE:
{evidence_text}

QUERY PLAN:
{plan_text}

USER QUESTION:
{question}

SQL:
""".strip()

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        options={"temperature": 0},
    )

    return extract_sql(response["message"]["content"])
