from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.graph.workflow import run_workflow


app = FastAPI(
    title="Multi-Agent Healthcare NL-to-SQL API",
    description=(
        "Converts natural-language healthcare questions into validated, "
        "read-only SQLite queries."
    ),
    version="1.0.0",
)


class QueryRequest(BaseModel):
    question: str = Field(
        min_length=1,
        description="Natural-language database question.",
    )
    evidence: str = Field(
        default="",
        description="Optional terminology or business-rule evidence.",
    )


class QueryResponse(BaseModel):
    question: str
    generated_sql: str | None
    status: str
    attempt_count: int
    result: dict[str, Any] | None
    validation: dict[str, Any]
    attempt_history: list[dict[str, Any]]
    error: str | None


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Multi-Agent Healthcare NL-to-SQL API is running."
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
    }


@app.post("/query", response_model=QueryResponse)
def query_database(request: QueryRequest) -> QueryResponse:
    try:
        output = run_workflow(
            question=request.question,
            evidence=request.evidence,
        )

        return QueryResponse(
            question=request.question,
            generated_sql=output.get("generated_sql"),
            status=output.get("status", "unknown"),
            attempt_count=output.get("attempt_count", 0),
            result=output.get("result"),
            validation=output.get("validation", {}),
            attempt_history=output.get("attempt_history", []),
            error=output.get("execution_error"),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error
