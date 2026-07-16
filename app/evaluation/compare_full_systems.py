import json
from pathlib import Path
from statistics import mean
from typing import Any


BASELINE_PATH = Path("benchmarks/baseline_all_50.json")
MULTI_AGENT_PATH = Path("benchmarks/results_all_50.json")
OUTPUT_PATH = Path("benchmarks/full_system_comparison.json")


def load_results(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Results file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def calculate_metrics(
    results: list[dict[str, Any]],
    *,
    is_multi_agent: bool,
) -> dict[str, Any]:
    total = len(results)

    matches = sum(
        bool(result.get("execution_match"))
        for result in results
    )

    successful = sum(
        result.get("status") == "success"
        for result in results
    )

    latencies = [
        float(result.get("latency_seconds", 0) or 0)
        for result in results
    ]

    metrics: dict[str, Any] = {
        "total_questions": total,
        "successful_executions": successful,
        "failed_executions": total - successful,
        "execution_matches": matches,
        "incorrect_queries": total - matches,
        "execution_accuracy_percent": (
            matches / total * 100 if total else 0
        ),
        "average_latency_seconds": (
            mean(latencies) if latencies else 0
        ),
    }

    if is_multi_agent:
        attempts = [
            int(result.get("attempt_count", 0) or 0)
            for result in results
        ]

        repaired_queries = sum(
            attempt > 1
            for attempt in attempts
        )

        first_pass_matches = sum(
            bool(result.get("execution_match"))
            and int(result.get("attempt_count", 0) or 0) == 1
            for result in results
        )

        metrics.update(
            {
                "queries_requiring_repair": repaired_queries,
                "first_pass_matches": first_pass_matches,
                "first_pass_accuracy_percent": (
                    first_pass_matches / total * 100
                    if total
                    else 0
                ),
                "average_attempts": (
                    mean(attempts) if attempts else 0
                ),
            }
        )

    return metrics


def main() -> None:
    baseline_results = load_results(BASELINE_PATH)
    multi_agent_results = load_results(MULTI_AGENT_PATH)

    baseline = calculate_metrics(
        baseline_results,
        is_multi_agent=False,
    )

    multi_agent = calculate_metrics(
        multi_agent_results,
        is_multi_agent=True,
    )

    accuracy_improvement = (
        multi_agent["execution_accuracy_percent"]
        - baseline["execution_accuracy_percent"]
    )

    baseline_errors = baseline["incorrect_queries"]
    multi_agent_errors = multi_agent["incorrect_queries"]

    error_reduction = (
        (baseline_errors - multi_agent_errors)
        / baseline_errors
        * 100
        if baseline_errors
        else 0
    )

    execution_success_improvement = (
        multi_agent["successful_executions"]
        - baseline["successful_executions"]
    )

    latency_multiplier = (
        multi_agent["average_latency_seconds"]
        / baseline["average_latency_seconds"]
        if baseline["average_latency_seconds"]
        else 0
    )

    comparison = {
        "evaluation_scope": {
            "dataset": "BIRD Mini-Dev",
            "database": "thrombosis_prediction",
            "questions": len(multi_agent_results),
        },
        "single_agent_baseline": baseline,
        "multi_agent_system": multi_agent,
        "improvements": {
            "accuracy_percentage_points": accuracy_improvement,
            "query_error_reduction_percent": error_reduction,
            "additional_correct_queries": (
                multi_agent["execution_matches"]
                - baseline["execution_matches"]
            ),
            "additional_successful_executions": (
                execution_success_improvement
            ),
            "latency_multiplier": latency_multiplier,
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            comparison,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("=" * 70)
    print("FULL SYSTEM COMPARISON")
    print("=" * 70)

    print("\nSingle-agent baseline")
    print(
        "Correct queries:",
        f"{baseline['execution_matches']}/{baseline['total_questions']}",
    )
    print(
        "Execution accuracy:",
        f"{baseline['execution_accuracy_percent']:.2f}%",
    )
    print(
        "Successful executions:",
        baseline["successful_executions"],
    )
    print(
        "Average latency:",
        f"{baseline['average_latency_seconds']:.3f} seconds",
    )

    print("\nMulti-agent system")
    print(
        "Correct queries:",
        f"{multi_agent['execution_matches']}/{multi_agent['total_questions']}",
    )
    print(
        "Execution accuracy:",
        f"{multi_agent['execution_accuracy_percent']:.2f}%",
    )
    print(
        "Successful executions:",
        multi_agent["successful_executions"],
    )
    print(
        "Queries requiring repair:",
        multi_agent["queries_requiring_repair"],
    )
    print(
        "Average latency:",
        f"{multi_agent['average_latency_seconds']:.3f} seconds",
    )

    print("\nMeasured improvement")
    print(
        "Accuracy improvement:",
        f"{accuracy_improvement:.2f} percentage points",
    )
    print(
        "Additional correct queries:",
        comparison["improvements"]["additional_correct_queries"],
    )
    print(
        "Query-error reduction:",
        f"{error_reduction:.2f}%",
    )
    print(
        "Additional successful executions:",
        execution_success_improvement,
    )
    print(
        "Latency multiplier:",
        f"{latency_multiplier:.2f}x",
    )

    print("\nResults saved to:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
