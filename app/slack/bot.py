import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from app.graph.workflow import run_workflow
from app.evaluation.query_logger import get_recent_logs, log_query


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

ENV_PATH = Path.cwd() / ".env"
load_dotenv(dotenv_path=ENV_PATH)

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

if not SLACK_BOT_TOKEN:
    raise RuntimeError("SLACK_BOT_TOKEN is missing from .env")

if not SLACK_APP_TOKEN:
    raise RuntimeError("SLACK_APP_TOKEN is missing from .env")


app = App(token=SLACK_BOT_TOKEN)

# Temporary in-memory storage for interaction details.
# This is sufficient for local development.
DETAIL_STORE: dict[str, dict[str, Any]] = {}


def format_rows(
    rows: list[dict[str, Any]],
    max_rows: int = 10,
) -> str:
    if not rows:
        return "No rows returned."

    displayed_rows = rows[:max_rows]
    columns = list(displayed_rows[0].keys())

    headers = [str(column) for column in columns]
    formatted_rows: list[list[str]] = []

    for row in displayed_rows:
        formatted_rows.append(
            [
                (
                    "Unknown"
                    if row.get(column) in ("", None)
                    else str(row.get(column))
                )
                for column in columns
            ]
        )

    widths = [
        max(
            len(headers[index]),
            max(
                len(row[index])
                for row in formatted_rows
            ),
        )
        for index in range(len(columns))
    ]

    header_line = " | ".join(
        headers[index].ljust(widths[index])
        for index in range(len(columns))
    )

    separator_line = "-+-".join(
        "-" * width
        for width in widths
    )

    data_lines = [
        " | ".join(
            row[index].ljust(widths[index])
            for index in range(len(columns))
        )
        for row in formatted_rows
    ]

    table = "\n".join(
        [header_line, separator_line, *data_lines]
    )

    output = f"```{table}```"

    if len(rows) > max_rows:
        output += (
            f"\n_Showing {max_rows} of {len(rows)} returned rows._"
        )

    return output


def build_summary_blocks(
    output: dict[str, Any],
    details_key: str,
) -> list[dict[str, Any]]:
    status = output.get("status", "unknown")
    attempts = output.get("attempt_count", 0)
    answer = (
        output.get("natural_language_answer")
        or "The query completed, but no explanation was generated."
    )

    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Answer*\n{answer}\n\n"
                    f"*Status:* `{status}`\n"
                    f"*Attempts:* `{attempts}`"
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Show details",
                    },
                    "action_id": "show_nl2sql_details",
                    "value": details_key,
                }
            ],
        },
    ]


def build_details_text(output: dict[str, Any]) -> str:
    generated_sql = (
        output.get("generated_sql")
        or "No SQL generated."
    )

    result = output.get("result") or {}
    rows = result.get("rows", [])

    sections = [
        "*Generated SQL:*",
        f"```{generated_sql}```",
        "*Result rows:*",
        format_rows(rows),
    ]

    repairs = [
        attempt
        for attempt in output.get("attempt_history", [])
        if attempt.get("type") == "repair"
    ]

    if repairs:
        sections.append("*Repair history:*")

        for attempt in repairs:
            sections.append(
                (
                    f"- Attempt {attempt.get('attempt')}: "
                    f"`{attempt.get('failure_category', 'unknown_failure')}`"
                )
            )

    validation = output.get("validation", {})
    warnings = validation.get("warnings", [])

    if warnings:
        sections.append("*Validation warnings:*")

        for warning in warnings:
            sections.append(f"- {warning}")

    error = output.get("execution_error")

    if error:
        sections.extend(
            [
                "*Error:*",
                f"`{error}`",
            ]
        )

    return "\n".join(sections)


def process_question(
    question: str,
    *,
    source: str,
    user_id: str,
    channel_id: str,
) -> dict[str, Any]:
    question = question.strip()

    if not question:
        raise ValueError("Question cannot be empty.")

    output = run_workflow(question)

    log_id = log_query(
        source=source,
        question=question,
        output=output,
        user_id=user_id,
        channel_id=channel_id,
    )

    output["log_id"] = log_id

    return output


def store_output(
    output: dict[str, Any],
    user_id: str,
    channel_id: str,
) -> str:
    key = f"{user_id}:{channel_id}:{len(DETAIL_STORE) + 1}"

    DETAIL_STORE[key] = output

    return key


@app.command("/nl2sql-history")
def handle_nl2sql_history(ack, command, respond, logger):
    ack()

    requested_limit = command.get("text", "").strip()

    try:
        limit = int(requested_limit) if requested_limit else 5
    except ValueError:
        respond(
            response_type="ephemeral",
            text="Please provide a whole number, for example: `/nl2sql-history 5`",
        )
        return

    limit = max(1, min(limit, 20))

    try:
        logs = get_recent_logs(limit=limit)

        if not logs:
            respond(
                response_type="ephemeral",
                text="No query history is available yet.",
            )
            return

        lines = ["*Recent NL-to-SQL queries:*"]

        for log in logs:
            question = log.get("question", "")
            status = log.get("status", "unknown")
            attempts = log.get("attempt_count", 0)
            source = log.get("source", "unknown")

            lines.append(
                f"• `{log.get('log_id')}` "
                f"*{question}*\n"
                f"  Status: `{status}` | "
                f"Attempts: `{attempts}` | "
                f"Source: `{source}`"
            )

        respond(
            response_type="ephemeral",
            text="\n".join(lines),
        )

    except Exception as error:
        logger.exception("Could not load query history")

        respond(
            response_type="ephemeral",
            text=f"Unable to load history: `{error}`",
        )


@app.command("/nl2sql")
def handle_nl2sql(ack, command, respond, logger):
    ack()

    question = command.get("text", "").strip()
    user_id = command.get("user_id", "unknown-user")
    channel_id = command.get("channel_id", "unknown-channel")

    if not question:
        respond(
            response_type="ephemeral",
            text=(
                "Please include a question.\n"
                "Example: `/nl2sql How many patients are there "
                "for each sex?`"
            ),
        )
        return

    respond(
        response_type="ephemeral",
        text=f"Processing: _{question}_",
    )

    try:
        output = process_question(
            question,
            source="slash_command",
            user_id=user_id,
            channel_id=channel_id,
        )

        details_key = store_output(
            output,
            user_id=user_id,
            channel_id=channel_id,
        )

        respond(
            response_type="in_channel",
            text=output.get(
                "natural_language_answer",
                "NL-to-SQL query completed.",
            ),
            blocks=build_summary_blocks(
                output,
                details_key,
            ),
        )

    except Exception as error:
        logger.exception("Slash-command workflow failed")

        respond(
            response_type="ephemeral",
            text=f"Application error: `{error}`",
        )


@app.event("app_mention")
def handle_app_mention(event, say, logger):
    raw_text = event.get("text", "")
    question = raw_text.split(">", maxsplit=1)[-1].strip()

    user_id = event.get("user", "unknown-user")
    channel_id = event.get("channel", "unknown-channel")

    try:
        say(
            text=f"Processing: _{question}_",
            thread_ts=event.get("ts"),
        )

        output = process_question(
            question,
            source="app_mention",
            user_id=user_id,
            channel_id=channel_id,
        )

        details_key = store_output(
            output,
            user_id=user_id,
            channel_id=channel_id,
        )

        say(
            text=output.get(
                "natural_language_answer",
                "NL-to-SQL query completed.",
            ),
            blocks=build_summary_blocks(
                output,
                details_key,
            ),
            thread_ts=event.get("ts"),
        )

    except Exception as error:
        logger.exception("App-mention workflow failed")

        say(
            text=f"Application error: `{error}`",
            thread_ts=event.get("ts"),
        )


@app.event("message")
def handle_direct_message(event, say, logger):
    logger.info(
        "Message event received: %s",
        json.dumps(event, default=str),
    )

    if event.get("bot_id") or event.get("subtype"):
        return

    if event.get("channel_type") != "im":
        return

    question = event.get("text", "").strip()
    user_id = event.get("user", "unknown-user")
    channel_id = event.get("channel", "unknown-channel")

    if not question:
        say("Please enter a healthcare database question.")
        return

    try:
        say(f"Processing: _{question}_")

        output = process_question(
            question,
            source="direct_message",
            user_id=user_id,
            channel_id=channel_id,
        )

        details_key = store_output(
            output,
            user_id=user_id,
            channel_id=channel_id,
        )

        say(
            text=output.get(
                "natural_language_answer",
                "NL-to-SQL query completed.",
            ),
            blocks=build_summary_blocks(
                output,
                details_key,
            ),
        )

    except Exception as error:
        logger.exception("Direct-message workflow failed")
        say(f"Application error: `{error}`")


@app.action("show_nl2sql_details")
def handle_show_details(ack, body, respond, logger):
    ack()

    try:
        action = body["actions"][0]
        details_key = action["value"]

        output = DETAIL_STORE.get(details_key)

        if not output:
            respond(
                response_type="ephemeral",
                text=(
                    "The stored details are no longer available. "
                    "Please run the query again."
                ),
            )
            return

        respond(
            response_type="ephemeral",
            text=build_details_text(output),
        )

    except Exception as error:
        logger.exception("Could not show NL-to-SQL details")

        respond(
            response_type="ephemeral",
            text=f"Unable to show details: `{error}`",
        )


if __name__ == "__main__":
    print("Starting Healthcare NL-to-SQL Slack bot...")
    print("Waiting for commands, mentions, messages, and button actions...")

    SocketModeHandler(
        app,
        SLACK_APP_TOKEN,
    ).start()
