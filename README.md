# Expert Panel

A multi-agent deliberation system that runs a structured, adversarial debate over a real decision (a job offer, a pricing call, a build-vs-buy choice) across four analytical personas, tracks every argument in a claims ledger, and stops the debate when it stops producing new information rather than after a fixed number of turns. The output is a tradeoff report with a full audit trail.

## Stack

- **Orchestration:** LangGraph, LangChain
- **Tools:** custom MCP servers (evidence search, document generation)
- **Backend:** FastAPI, WebSockets
- **Frontend:** React

## Structure

```
backend/    FastAPI app, LangGraph state graph, MCP servers, tests
frontend/   React live debate UI
reports/    generated report exports (not committed)
```

## Status

Early scaffolding, in active development.
