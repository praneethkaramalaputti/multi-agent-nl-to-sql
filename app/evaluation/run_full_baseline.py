import json
from pathlib import Path
from statistics import mean

from app.evaluation.baseline_runner import evaluate_baseline
from app.evaluation.benchmark_runner import load_benchmark


OUTPUT_PATH = Path("benchmarks/baseline_all_50.json")


def main() -> None:
    examples = load_benchmark()
    results = []

    for index, example in enumerate(examples, start=1):
        print("=" * 70)
        print(f"Baseline evaluation {index}/{len(examples)}")
        print("Question ID:", example.get("question_id"))
        print(example["question"])

        result = evaluate_baseline(example)
        results.append(result)

        print("Status:", result.get("status"))
        print(
            "Execution match:",
            result.get("execution_match", False),
        )
        print(
            "Latency:",
            result.get("latency_seconds", 0),
            "seconds",
        )

        if result.get("error"):
            print("Error:", result["error"])

        # Save progress after every question.
        OUTPUT_PATH.write_text(
            json.dumps(
                results,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    total = len(results)

    successful = sum(
        result.get("status") == "success"
        for result in results
    )

    matches = sum(
        bool(result.get("execution_match"))
        for result in results
    )

    latencies = [
        result.get("latency_seconds", 0)
        for result in results
    ]

    accuracy = (
        matches / total * 100
        if total
        else 0
    )

    print("\n" + "=" * 70)
    print("FULL SINGLE-AGENT BASELINE SUMMARY")
    print("=" * 70)
    print("Total questions:", total)
    print("Successful executions:", successful)
    print("Execution matches:", matches)
    print("Execution accuracy:", f"{accuracy:.2f}%")
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
