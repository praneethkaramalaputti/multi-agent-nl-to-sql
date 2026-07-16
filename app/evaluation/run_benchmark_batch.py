import json
from pathlib import Path

from app.evaluation.benchmark_runner import (
    evaluate_example,
    load_benchmark,
)


OUTPUT_PATH = Path("benchmarks/results_first_5.json")


def main() -> None:
    benchmark = load_benchmark()
    examples = benchmark[:5]

    results = []

    for index, example in enumerate(examples, start=1):
        print(f"\n{'=' * 70}")
        print(f"Evaluating {index}/{len(examples)}")
        print(f"Question ID: {example.get('question_id')}")
        print(example["question"])
        print(f"{'=' * 70}")

        evaluation = evaluate_example(example)
        results.append(evaluation)

        print("Status:", evaluation["status"])
        print("Execution match:", evaluation["execution_match"])
        print("Attempts:", evaluation["attempt_count"])
        print("Latency:", evaluation["latency_seconds"], "seconds")

        if evaluation.get("failure_category"):
            print(
                "Failure category:",
                evaluation["failure_category"],
            )

        if evaluation.get("error"):
            print("Error:", evaluation["error"])

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            results,
            file,
            indent=2,
            ensure_ascii=False,
        )

    total = len(results)
    matched = sum(
        1
        for result in results
        if result["execution_match"]
    )
    successful = sum(
        1
        for result in results
        if result["status"] == "success"
    )
    repaired = sum(
        1
        for result in results
        if result["attempt_count"] > 1
    )

    execution_accuracy = (
        matched / total * 100
        if total
        else 0
    )

    print(f"\n{'=' * 70}")
    print("BATCH SUMMARY")
    print(f"{'=' * 70}")
    print("Total questions:", total)
    print("Successful executions:", successful)
    print("Execution matches:", matched)
    print("Queries requiring repair:", repaired)
    print(
        "Execution accuracy:",
        f"{execution_accuracy:.2f}%",
    )
    print("Results saved to:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
