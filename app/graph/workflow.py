from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    create_query_plan_node,
    execute_sql_node,
    generate_answer_node,
    generate_sql_node,
    load_schema_node,
    repair_sql_node,
    route_after_execution,
    route_after_validation,
    validate_sql_node,
)
from app.graph.state import NLToSQLState


def build_workflow():
    graph = StateGraph(NLToSQLState)

    graph.add_node("load_schema", load_schema_node)
    graph.add_node("create_query_plan", create_query_plan_node)
    graph.add_node("generate_sql", generate_sql_node)
    graph.add_node("validate_sql", validate_sql_node)
    graph.add_node("execute_sql", execute_sql_node)
    graph.add_node("repair_sql", repair_sql_node)
    graph.add_node("generate_answer", generate_answer_node)

    graph.add_edge(START, "load_schema")
    graph.add_edge("load_schema", "create_query_plan")
    graph.add_edge("create_query_plan", "generate_sql")
    graph.add_edge("generate_sql", "validate_sql")

    graph.add_conditional_edges(
        "validate_sql",
        route_after_validation,
        {
            "execute": "execute_sql",
            "repair": "repair_sql",
            "stop": END,
        },
    )

    graph.add_conditional_edges(
        "execute_sql",
        route_after_execution,
        {
            "repair": "repair_sql",
            "stop": "generate_answer",
        },
    )

    graph.add_edge("repair_sql", "validate_sql")
    graph.add_edge("generate_answer", END)

    return graph.compile()


workflow = build_workflow()


def run_workflow(
    question: str,
    evidence: str = "",
) -> NLToSQLState:
    initial_state: NLToSQLState = {
        "question": question,
        "evidence": evidence,
        "attempt_count": 0,
        "attempt_history": [],
        "status": "started",
    }

    return workflow.invoke(initial_state)


if __name__ == "__main__":
    output = run_workflow(
        "How many patients are there for each sex?"
    )

    print("Generated SQL:")
    print(output.get("generated_sql"))

    print("\nNatural-language answer:")
    print(output.get("natural_language_answer"))

    print("\nStatus:")
    print(output.get("status"))
