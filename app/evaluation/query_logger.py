import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_DATABASE_PATH = Path("data/nl2sql_logs.db")


def initialize_log_database() -> None:
    LOG_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(LOG_DATABASE_PATH)

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS query_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                source TEXT NOT NULL,
                user_id TEXT,
                channel_id TEXT,
                question TEXT NOT NULL,
                generated_sql TEXT,
                status TEXT,
                attempt_count INTEGER,
                failure_category TEXT,
                natural_language_answer TEXT,
                execution_error TEXT,
                result_json TEXT,
                attempt_history_json TEXT
            )
            """
        )

        connection.commit()

    finally:
        connection.close()


def log_query(
    *,
    source: str,
    question: str,
    output: dict[str, Any],
    user_id: str | None = None,
    channel_id: str | None = None,
) -> int:
    initialize_log_database()

    created_at = datetime.now(timezone.utc).isoformat()

    connection = sqlite3.connect(LOG_DATABASE_PATH)

    try:
        cursor = connection.execute(
            """
            INSERT INTO query_logs (
                created_at,
                source,
                user_id,
                channel_id,
                question,
                generated_sql,
                status,
                attempt_count,
                failure_category,
                natural_language_answer,
                execution_error,
                result_json,
                attempt_history_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                source,
                user_id,
                channel_id,
                question,
                output.get("generated_sql"),
                output.get("status"),
                output.get("attempt_count", 0),
                output.get("failure_category"),
                output.get("natural_language_answer"),
                output.get("execution_error"),
                json.dumps(
                    output.get("result"),
                    ensure_ascii=False,
                    default=str,
                ),
                json.dumps(
                    output.get("attempt_history", []),
                    ensure_ascii=False,
                    default=str,
                ),
            ),
        )

        connection.commit()
        return int(cursor.lastrowid)

    finally:
        connection.close()


def get_recent_logs(limit: int = 10) -> list[dict[str, Any]]:
    initialize_log_database()

    connection = sqlite3.connect(LOG_DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute(
            """
            SELECT
                log_id,
                created_at,
                source,
                user_id,
                channel_id,
                question,
                status,
                attempt_count,
                failure_category
            FROM query_logs
            ORDER BY log_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


if __name__ == "__main__":
    test_output = {
        "generated_sql": (
            'SELECT "SEX", COUNT(*) '
            'FROM "Patient" GROUP BY "SEX";'
        ),
        "status": "success",
        "attempt_count": 1,
        "failure_category": None,
        "natural_language_answer": (
            "There are 1,023 female patients, "
            "202 male patients, and 13 unspecified patients."
        ),
        "execution_error": None,
        "result": {
            "rows": [
                {"SEX": "F", "COUNT(*)": 1023},
                {"SEX": "M", "COUNT(*)": 202},
            ]
        },
        "attempt_history": [],
    }

    log_id = log_query(
        source="test",
        question="How many patients are there for each sex?",
        output=test_output,
        user_id="test-user",
        channel_id="test-channel",
    )

    print("Created log ID:", log_id)
    print("Recent logs:")

    for log in get_recent_logs():
        print(log)
