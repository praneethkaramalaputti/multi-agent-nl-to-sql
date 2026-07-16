import json
import time
from pathlib import Path
from typing import Any

from app.agents.sql_generator import generate_sql
from app.agents.sql_validator import validate_sql
from app.database.safe_executor import execute_safe_query
from app.evaluation.benchmark_runner import (
    compare_results,
    load_benchmark,
)


OUTPUT_PATH = Path("benchmarks/baseline_first_10.json")


def evaluate_baseline(
    example: dict[str, Any],
) -> dict[str, Any]:
    question = example["question"]
    evidence = example.get("evidence", "")
    gold_sql = example["SQL"]

    start_time = time.perf_counter()

    result: dict[str, Any] = {
        "question_id": example.get("question_id"),
        "question": question,
        "difficulty": example.get("difficulty"),
        "evidence": evidence,
        "gold_sql": gold_sql,
        "generated_sql": None,
        "status": "started",
        "execution_match": False,
        "latency_seconds": 0,
        "validation": {},
        "error": None,
    }

    try:
        # Single-agent baseline:
        # no query planner, no LangGraph, and no repair loop.
        generated_sql = generate_sql(
            question=question,
            query_plan={},
            evidence=evidence,
        )

        result["generated_sql"] = generated_sql

        validation = validate_sql(generated_sql)
        result["validation"] = validation

        if not validation["is_valid"]:
            result["status"] = "validation_failed"
            result["error"] = "; ".join(
                validation.get("errors", [])
            )
            return result

        generated_result = execute_safe_query(
            generated_sql,
            max_rows=10000,
        )

        gold_result = execute_safe_query(
            gold_sql,
            max_rows=10000,
        )

        result["execution_match"] = compare_results(
            generated_result,
            gold_result,
        )
        result["status"] = "success"
        result["generated_row_count"] = len(
            generated_result.get("rows", [])
        )
        result["gold_row_count"] = len(
            gold_result.get("rows", [])
        )

        return result

    except Exception as error:
        result["status"] = "execution_failed"
        result["error"] = str(error)
        return result

    finally:
        result["latency_seconds"] = round(
            time.perf_counter() - start_time,
            3,
        )


def main() -> None:
    examples = load_benchmark()[:10]
    results: list[dict[str, Any]] = []

    for index, example in enumerate(examples, start=1):
        print("=" * 70)
        print(f"Baseline evaluation {index}/{len(examples)}")
        print("Question ID:", example.get("question_id"))
        print(example["question"])

        evaluation = evaluate_baseline(example)
        results.append(evaluation)

        print("Status:", evaluation["status"])
        print(
            "Execution match:",
            evaluation["execution_match"],
        )
        print(
            "Latency:",
            evaluation["latency_seconds"],
            "seconds",
        )

        if evaluation.get("error"):
            print("Error:", evaluation["error"])

    OUTPUT_PATH.write_text(
        json.dumps(
            results,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    total = len(results)

    matches = sum(
        1
        for result in results
        if result.get("execution_match")
    )

    successful_executions = sum(
        1
        for result in results
        if result.get("status") == "success"
    )

    accuracy = (
        matches / total * 100
        if total
        else 0
    )

    print("\n" + "=" * 70)
    print("SINGLE-AGENT BASELINE SUMMARY")
    print("=" * 70)
    print("Total questions:", total)
    print(
        "Successful executions:",
        successful_executions,
    )
    print("Execution matches:", matches)
    print("Execution accuracy:", f"{accuracy:.2f}%")
    print("Results saved to:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
