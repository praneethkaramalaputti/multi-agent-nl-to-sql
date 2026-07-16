import json
from pathlib import Path
from statistics import mean


BASELINE_PATH = Path("benchmarks/baseline_first_10.json")
MULTI_AGENT_PATH = Path("benchmarks/results_first_10.json")
OUTPUT_PATH = Path("benchmarks/system_comparison.json")


def load_results(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Results file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def calculate_metrics(results: list[dict]) -> dict:
    total = len(results)

    matches = sum(
        1
        for result in results
        if result.get("execution_match")
    )

    successful = sum(
        1
        for result in results
        if result.get("status") == "success"
    )

    latencies = [
        result.get("latency_seconds", 0)
        for result in results
    ]

    attempts = [
        result.get("attempt_count", 1)
        for result in results
    ]

    errors = total - matches

    return {
        "total_questions": total,
        "successful_executions": successful,
        "execution_matches": matches,
        "execution_errors": errors,
        "execution_accuracy": (
            matches / total * 100
            if total
            else 0
        ),
        "average_latency_seconds": (
            mean(latencies)
            if latencies
            else 0
        ),
        "average_attempts": (
            mean(attempts)
            if attempts
            else 0
        ),
    }


def main() -> None:
    baseline_results = load_results(BASELINE_PATH)
    multi_agent_results = load_results(MULTI_AGENT_PATH)

    baseline = calculate_metrics(baseline_results)
    multi_agent = calculate_metrics(multi_agent_results)

    baseline_errors = baseline["execution_errors"]
    multi_agent_errors = multi_agent["execution_errors"]

    error_reduction = (
        (
            baseline_errors - multi_agent_errors
        )
        / baseline_errors
        * 100
        if baseline_errors
        else 0
    )

    accuracy_improvement = (
        multi_agent["execution_accuracy"]
        - baseline["execution_accuracy"]
    )

    comparison = {
        "baseline": baseline,
        "multi_agent": multi_agent,
        "accuracy_improvement_percentage_points": (
            accuracy_improvement
        ),
        "error_reduction_percentage": error_reduction,
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
    print("SINGLE-AGENT VS MULTI-AGENT COMPARISON")
    print("=" * 70)

    print("\nSingle-agent baseline")
    print(
        "Execution accuracy:",
        f"{baseline['execution_accuracy']:.2f}%",
    )
    print(
        "Execution errors:",
        baseline["execution_errors"],
    )
    print(
        "Average latency:",
        f"{baseline['average_latency_seconds']:.3f} seconds",
    )

    print("\nMulti-agent system")
    print(
        "Execution accuracy:",
        f"{multi_agent['execution_accuracy']:.2f}%",
    )
    print(
        "Execution errors:",
        multi_agent["execution_errors"],
    )
    print(
        "Average latency:",
        f"{multi_agent['average_latency_seconds']:.3f} seconds",
    )
    print(
        "Average attempts:",
        f"{multi_agent['average_attempts']:.2f}",
    )

    print("\nImprovement")
    print(
        "Accuracy improvement:",
        f"{accuracy_improvement:.2f} percentage points",
    )
    print(
        "Query error reduction:",
        f"{error_reduction:.2f}%",
    )

    print("\nResults saved to:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
