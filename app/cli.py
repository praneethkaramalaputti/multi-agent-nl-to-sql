import json

from app.graph.workflow import run_workflow


def print_result(output: dict) -> None:
    print("\n" + "=" * 70)
    print("NL-TO-SQL RESULT")
    print("=" * 70)

    print("\nQuestion:")
    print(output.get("question"))

    print("\nQuery plan:")
    print(
        json.dumps(
            output.get("query_plan", {}),
            indent=2,
        )
    )

    print("\nGenerated SQL:")
    print(output.get("generated_sql"))

    print("\nStatus:")
    print(output.get("status"))

    print("\nAttempts:")
    print(output.get("attempt_count", 0))

    validation = output.get("validation", {})

    if validation.get("warnings"):
        print("\nValidation warnings:")
        for warning in validation["warnings"]:
            print("-", warning)

    result = output.get("result")

    if result:
        print("\nResult:")

        rows = result.get("rows", [])

        if not rows:
            print("No rows returned.")
        else:
            for row in rows:
                print(row)

        if result.get("truncated"):
            print("\nResult truncated to the configured row limit.")

    if output.get("execution_error"):
        print("\nError:")
        print(output["execution_error"])

    history = output.get("attempt_history", [])

    if len(history) > 1:
        print("\nRepair history:")

        for attempt in history:
            if attempt.get("type") != "repair":
                continue

            print(
                f"- Attempt {attempt.get('attempt')}: "
                f"{attempt.get('failure_category')}"
            )


def main() -> None:
    print("=" * 70)
    print("MULTI-AGENT HEALTHCARE NL-TO-SQL")
    print("=" * 70)
    print("Enter a healthcare database question.")
    print("Type 'exit' or 'quit' to stop.")

    while True:
        question = input("\nQuestion: ").strip()

        if question.lower() in {"exit", "quit"}:
            print("Application stopped.")
            break

        if not question:
            print("Please enter a question.")
            continue

        try:
            output = run_workflow(question)
            print_result(output)

        except KeyboardInterrupt:
            print("\nApplication stopped.")
            break

        except Exception as error:
            print("\nApplication error:")
            print(error)


if __name__ == "__main__":
    main()
