import json
from typing import Any

import ollama

from app.agents.sql_generator import MODEL_NAME
from app.database.schema_loader import load_database_schema


def create_query_plan(
    question: str,
    evidence: str = "",
) -> dict[str, Any]:
    if not question.strip():
        raise ValueError("Question cannot be empty.")

    schema = load_database_schema()
    evidence_text = evidence.strip() or "No external evidence provided."

    prompt = f"""
You are a healthcare database query-planning agent.

Create a structured plan for answering the user's question using SQLite.

Return only valid JSON with this exact structure:
{{
  "intent": "short description",
  "tables": ["table names"],
  "columns": ["column names"],
  "joins": ["join conditions"],
  "filters": ["filter conditions"],
  "aggregation": "aggregation or null",
  "group_by": ["grouping columns"],
  "order_by": ["ordering requirements"],
  "limit": null,
  "calculation": "required formula or null",
  "notes": ["important assumptions"]
}}

Rules:
1. Use only tables and columns in the database schema.
2. Use the provided evidence to resolve business and medical terminology.
3. Do not ignore formulas or value mappings in the evidence.
4. Do not write SQL.
5. Use "ID" to connect tables when appropriate.
6. Do not invent medical definitions.
7. Return valid JSON only.

DATABASE SCHEMA:
{schema}

EXTERNAL EVIDENCE:
{evidence_text}

USER QUESTION:
{question}
""".strip()

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        format="json",
        options={"temperature": 0},
    )

    content = response["message"]["content"]

    try:
        return json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Planner returned invalid JSON: {content}"
        ) from error


if __name__ == "__main__":
    question = (
        "Are there more in-patient or outpatient who were male? "
        "What is the deviation in percentage?"
    )

    evidence = (
        "male refers to SEX = 'M'; "
        "in-patient refers to Admission = '+'; "
        "outpatient refers to Admission = '-'; "
        "percentage means inpatient count divided by outpatient count "
        "multiplied by 100"
    )

    print(
        json.dumps(
            create_query_plan(question, evidence),
            indent=2,
        )
    )
