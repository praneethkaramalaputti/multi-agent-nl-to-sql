import json
import time
from pathlib import Path
from typing import Any

from app.database.safe_executor import execute_safe_query
from app.graph.workflow import run_workflow


BENCHMARK_PATH = Path("benchmarks/thrombosis_prediction.json")


def normalize_value(value: Any) -> str:
    if value is None:
        return "NULL"

    if isinstance(value, float):
        return f"{value:.10f}".rstrip("0").rstrip(".")

    return str(value)


def normalize_rows(
    rows: list[dict[str, Any]],
) -> list[tuple[str, ...]]:
    """
    Compare query results independently of aliases and row ordering.
    """
    normalized: list[tuple[str, ...]] = []

    for row in rows:
        normalized_row = tuple(
            normalize_value(value)
            for value in row.values()
        )
        normalized.append(normalized_row)

    return sorted(normalized)


def compare_results(
    generated_result: dict[str, Any],
    gold_result: dict[str, Any],
) -> bool:
    generated_rows = normalize_rows(
        generated_result.get("rows", [])
    )
    gold_rows = normalize_rows(
        gold_result.get("rows", [])
    )

    return generated_rows == gold_rows


def evaluate_example(
    example: dict[str, Any],
) -> dict[str, Any]:
    question = example["question"]
    gold_sql = example["SQL"]

    start_time = time.perf_counter()

    workflow_output = run_workflow(
        question,
        evidence=example.get("evidence", ""),
    )

    latency_seconds = time.perf_counter() - start_time

    generated_sql = workflow_output.get("generated_sql")

    evaluation: dict[str, Any] = {
        "question_id": example.get("question_id"),
        "question": question,
        "difficulty": example.get("difficulty"),
        "evidence": example.get("evidence"),
        "gold_sql": gold_sql,
        "generated_sql": generated_sql,
        "status": workflow_output.get("status"),
        "attempt_count": workflow_output.get(
            "attempt_count",
            0,
        ),
        "attempt_history": workflow_output.get(
            "attempt_history",
            [],
        ),
        "failure_category": workflow_output.get(
            "failure_category"
        ),
        "execution_match": False,
        "latency_seconds": round(latency_seconds, 3),
        "error": workflow_output.get("execution_error"),
    }

    try:
        gold_result = execute_safe_query(
            gold_sql,
            max_rows=10000,
        )
    except Exception as error:
        evaluation["error"] = (
            f"Gold SQL execution failed: {error}"
        )
        return evaluation

    if not generated_sql:
        return evaluation

    try:
        generated_result = execute_safe_query(
            generated_sql,
            max_rows=10000,
        )
    except Exception as error:
        evaluation["error"] = (
            f"Generated SQL execution failed: {error}"
        )
        return evaluation

    evaluation["execution_match"] = compare_results(
        generated_result,
        gold_result,
    )

    evaluation["generated_rows"] = generated_result["rows"]
    evaluation["gold_rows"] = gold_result["rows"]
    evaluation["generated_row_count"] = len(
        generated_result["rows"]
    )
    evaluation["gold_row_count"] = len(
        gold_result["rows"]
    )
    evaluation["generated_truncated"] = generated_result[
        "truncated"
    ]
    evaluation["gold_truncated"] = gold_result["truncated"]

    return evaluation


def load_benchmark() -> list[dict[str, Any]]:
    if not BENCHMARK_PATH.exists():
        raise FileNotFoundError(
            f"Benchmark file not found: {BENCHMARK_PATH}"
        )

    with BENCHMARK_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


if __name__ == "__main__":
    benchmark = load_benchmark()
    first_example = benchmark[0]

    print("Evaluating question:")
    print(first_example["question"])

    print("\nEvidence:")
    print(first_example["evidence"])

    evaluation = evaluate_example(first_example)

    print("\nGenerated SQL:")
    print(evaluation["generated_sql"])

    print("\nGold SQL:")
    print(evaluation["gold_sql"])

    print("\nStatus:")
    print(evaluation["status"])

    print("\nAttempt count:")
    print(evaluation["attempt_count"])

    print("\nExecution match:")
    print(evaluation["execution_match"])

    print("\nLatency:")
    print(evaluation["latency_seconds"], "seconds")

    print("\nGenerated row count:")
    print(evaluation.get("generated_row_count"))

    print("\nGold row count:")
    print(evaluation.get("gold_row_count"))

    if evaluation.get("error"):
        print("\nError:")
        print(evaluation["error"])
