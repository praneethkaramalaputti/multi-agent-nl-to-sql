import json
from pathlib import Path
from statistics import mean

from app.evaluation.benchmark_runner import (
    evaluate_example,
    load_benchmark,
)


OUTPUT_PATH = Path("benchmarks/results_all_50.json")


def main() -> None:
    examples = load_benchmark()
    results = []

    for index, example in enumerate(examples, start=1):
        print("=" * 70)
        print(f"Evaluating {index}/{len(examples)}")
        print("Question ID:", example.get("question_id"))
        print(example["question"])

        result = evaluate_example(example)
        results.append(result)

        print("Status:", result.get("status"))
        print(
            "Execution match:",
            result.get("execution_match"),
        )
        print(
            "Attempts:",
            result.get("attempt_count", 0),
        )
        print(
            "Latency:",
            result.get("latency_seconds", 0),
            "seconds",
        )

        if result.get("failure_category"):
            print(
                "Failure category:",
                result["failure_category"],
            )

        if result.get("error"):
            print("Error:", result["error"])

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

    successful = sum(
        1
        for result in results
        if result.get("status") == "success"
    )

    repaired = sum(
        1
        for result in results
        if result.get("attempt_count", 0) > 1
    )

    first_pass_matches = sum(
        1
        for result in results
        if result.get("execution_match")
        and result.get("attempt_count", 0) == 1
    )

    latencies = [
        result.get("latency_seconds", 0)
        for result in results
    ]

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

    print("\n" + "=" * 70)
    print("FULL BIRD HEALTHCARE BENCHMARK SUMMARY")
    print("=" * 70)
    print("Total questions:", total)
    print("Successful executions:", successful)
    print("Execution matches:", matches)
    print("Queries requiring repair:", repaired)
    print(
        "Execution accuracy:",
        f"{execution_accuracy:.2f}%",
    )
    print(
        "First-pass accuracy:",
        f"{first_pass_accuracy:.2f}%",
    )
    print(
        "Average latency:",
        (
            f"{mean(latencies):.3f} seconds"
            if latencies
            else "0.000 seconds"
        ),
    )
    print("Results saved to:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
