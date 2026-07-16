import re

import ollama

from app.agents.sql_generator import MODEL_NAME
from app.database.schema_loader import load_database_schema


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
            "Repair response did not contain a SELECT query."
        )

    return select_match.group(0).strip().rstrip(";") + ";"


def repair_sql(
    question: str,
    failed_sql: str,
    error_message: str,
    evidence: str = "",
) -> str:
    schema = load_database_schema()
    evidence_text = evidence.strip() or "No external evidence provided."

    prompt = f"""
You are an expert SQLite query-repair agent.

Repair the failed SQL query using the schema, evidence, user question,
and error message.

Rules:
1. Return exactly one read-only SQLite SELECT query.
2. Use only tables and columns that exist in the schema.
3. Quote every table and column name using double quotes.
4. Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or PRAGMA.
5. Preserve the user's original intent and evidence mappings.
6. Return only SQL with no explanation or Markdown.
7. Verify which table owns every referenced column.
8. "RVVT", "KCT", "LAC", "Symptoms", and "Thrombosis" belong to
   the "Examination" table, not "Laboratory".
9. "Birthday", "SEX", "Admission", and the patient diagnosis belong to
   the "Patient" table.
10. When multiple joined tables contain the same column name, always
    qualify the column with its table name.
11. Both "Patient" and "Examination" contain a "Diagnosis" column.
12. When the question asks what disease the patient is diagnosed with,
    use "Patient"."Diagnosis" unless the evidence explicitly requests
    examination diagnosis.
13. Use "Examination"."Symptoms" for observed symptoms.
14. Join "Patient", "Examination", and "Laboratory" using their "ID"
    columns.
15. Never invent columns such as "PatientID".
16. Fix the actual table or column causing the error. Do not merely
    change equality to LIKE.
17. Use DISTINCT when a one-to-many join could duplicate patient rows.
18. Use CAST(... AS REAL) when SQLite division must return a decimal.

DATABASE SCHEMA:
{schema}

EXTERNAL EVIDENCE:
{evidence_text}

USER QUESTION:
{question}

FAILED SQL:
{failed_sql}

ERROR:
{error_message}

REPAIRED SQL:
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
