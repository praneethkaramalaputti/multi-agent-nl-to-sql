from typing import Any

from app.agents.sql_generator import generate_sql
from app.agents.sql_validator import validate_sql
from app.database.safe_executor import execute_safe_query


def run_nl_to_sql(question: str) -> dict[str, Any]:
    if not question.strip():
        raise ValueError("Question cannot be empty.")

    generated_sql = generate_sql(question)
    validation = validate_sql(generated_sql)

    output: dict[str, Any] = {
        "question": question,
        "sql": generated_sql,
        "validation": validation,
        "result": None,
        "status": "validation_failed",
    }

    if not validation["is_valid"]:
        return output

    try:
        result = execute_safe_query(generated_sql)
        output["result"] = result
        output["status"] = "success"
    except Exception as error:
        output["status"] = "execution_failed"
        output["execution_error"] = str(error)

    return output


if __name__ == "__main__":
    test_question = "How many patients are there for each sex?"

    output = run_nl_to_sql(test_question)

    print("Question:")
    print(output["question"])

    print("\nGenerated SQL:")
    print(output["sql"])

    print("\nValidation:")
    print(output["validation"])

    print("\nStatus:")
    print(output["status"])

    if output["result"]:
        print("\nRows:")
        for row in output["result"]["rows"]:
            print(row)

    if output.get("execution_error"):
        print("\nExecution error:")
        print(output["execution_error"])
