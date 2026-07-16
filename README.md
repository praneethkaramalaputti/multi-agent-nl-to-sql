
# Multi-Agent NL-to-SQL System

A multi-agent natural-language-to-SQL system that converts user questions into safe, executable SQL queries using LangGraph, Ollama, SQLGlot, SQLite, FastAPI, and Slack.

The system uses specialized agents for planning, SQL generation, validation, repair, execution, and natural-language answer generation

## Results

Evaluated on 50 questions from the BIRD Mini-Dev healthcare benchmark using the `thrombosis_prediction` database.

| Metric | Single-Agent | Multi-Agent |
|---|---:|---:|
| Execution accuracy | 26% | 46% |
| Correct queries | 13/50 | 23/50 |
| Successful executions | 34/50 | 49/50 |
| Average latency | 1.867 s | 12.303 s |

The multi-agent system achieved:

- 20 percentage-point accuracy improvement
- 27.03% query-error reduction
- 10 additional correct queries
- 15 additional successful executions
- 18 queries routed through the repair workflow

## Architecture

```text
Natural-language question
        |
        v
Schema Loader
        |
        v
Query Planner Agent
        |
        v
SQL Generator Agent
        |
        v
SQL Validator
    |          |
 invalid      valid
    |          |
    v          v
SQL Repair   Safe Executor
    ^          |
    |          v
    +------ execution failure
               |
               v
Natural-Language Answer Generator
