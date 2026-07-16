import json
from typing import Any

import ollama

from app.agents.sql_generator import MODEL_NAME


def generate_natural_language_answer(
    question: str,
    generated_sql: str,
    result: dict[str, Any] | None,
) -> str:
    if not result:
        return "The query did not return a result."

    rows = result.get("rows", [])

    if not rows:
        return "No matching records were found."

    prompt = f"""
You are a healthcare database result-explanation agent.

Explain the SQL query result in clear, concise natural language.

Rules:
1. Answer the user's question directly.
2. Use only the provided result rows.
3. Do not invent medical interpretations.
4. Do not provide medical advice.
5. Mention missing or blank values as "unspecified".
6. Keep the answer under 120 words.
7. Do not include SQL unless necessary.
8. Preserve numerical precision when the result is a percentage or ratio.

USER QUESTION:
{question}

GENERATED SQL:
{generated_sql}

RESULT ROWS:
{json.dumps(rows, ensure_ascii=False, default=str)}

ANSWER:
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

    answer = response["message"]["content"].strip()

    if not answer:
        return "The query executed successfully, but no explanation was generated."

    return answer


if __name__ == "__main__":
    test_result = {
        "rows": [
            {"SEX": "", "patient_count": 13},
            {"SEX": "F", "patient_count": 1023},
            {"SEX": "M", "patient_count": 202},
        ]
    }

    answer = generate_natural_language_answer(
        question="How many patients are there for each sex?",
        generated_sql=(
            'SELECT "SEX", COUNT(*) AS "patient_count" '
            'FROM "Patient" GROUP BY "SEX";'
        ),
        result=test_result,
    )

    print(answer)
