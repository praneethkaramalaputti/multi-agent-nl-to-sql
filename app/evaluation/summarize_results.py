import json
from collections import Counter
from pathlib import Path
from statistics import mean


RESULTS_PATH = Path("benchmarks/results_first_10.json")


def main() -> None:
    with RESULTS_PATH.open("r", encoding="utf-8") as file:
        results = json.load(file)

    total = len(results)

    successful = sum(
        1
        for result in results
        if result.get("status") == "success"
    )

    matches = sum(
        1
        for result in results
        if result.get("execution_match")
    )

    first_pass_matches = sum(
        1
        for result in results
        if result.get("execution_match")
        and result.get("attempt_count", 0) == 1
    )

    repaired_results = [
        result
        for result in results
        if result.get("attempt_count", 0) > 1
    ]

    repaired = len(repaired_results)

    successful_repairs = sum(
        1
        for result in repaired_results
        if result.get("execution_match")
    )

    latencies = [
        result.get("latency_seconds", 0)
        for result in results
    ]

    attempts = [
        result.get("attempt_count", 0)
        for result in results
    ]

    repair_categories = Counter()

    for result in results:
        for attempt in result.get("attempt_history", []):
            if attempt.get("type") != "repair":
                continue

            category = attempt.get(
                "failure_category"
            ) or "unknown_failure"

            repair_categories[category] += 1

    execution_accuracy = (
        matches / total * 100
        if total
        else 0
    )

    first_pass_accuracy = (
        first_pass_matches / total * 100
        if total
        else 0
    )

    repair_success_rate = (
        successful_repairs / repaired * 100
        if repaired
        else 0
    )

    print("=" * 70)
    print("NL-TO-SQL EVALUATION SUMMARY")
    print("=" * 70)

    print("\nOverall metrics")
    print("Total questions:", total)
    print("Successful executions:", successful)
    print("Execution matches:", matches)
    print(
        "Execution accuracy:",
        f"{execution_accuracy:.2f}%",
    )
    print(
        "First-pass accuracy:",
        f"{first_pass_accuracy:.2f}%",
    )
    print("Queries requiring repair:", repaired)
    print("Successfully repaired queries:", successful_repairs)
    print(
        "Repair success rate:",
        f"{repair_success_rate:.2f}%",
    )
    print(
        "Average attempts:",
        f"{mean(attempts):.2f}" if attempts else "0.00",
    )
    print(
        "Average latency:",
        (
            f"{mean(latencies):.3f} seconds"
            if latencies
            else "0.000 seconds"
        ),
    )

    print("\nFailure categories repaired")

    if not repair_categories:
        print("No repairs were required.")
    else:
        for category, count in repair_categories.most_common():
            print(f"- {category}: {count}")


if __name__ == "__main__":
    main()
