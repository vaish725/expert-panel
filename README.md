# Expert Panel

A multi-agent deliberation system that runs a structured, adversarial debate over a real decision (a job offer, a pricing call, a build-vs-buy choice) across four analytical personas, tracks every argument in a claims ledger, and stops the debate when it stops producing new information rather than after a fixed number of turns. The output is a tradeoff report the user reviews and approves, with a full audit trail of how the system got there.

Live debate view, ledger, and review panel all stream over a single WebSocket; the LangGraph state machine is the source of truth throughout.

## Stack

- **Orchestration:** LangGraph, LangChain
- **Tools:** custom MCP servers (evidence search, document generation), built with the official MCP Python SDK
- **Backend:** FastAPI, WebSockets, SQLite checkpointer
- **Frontend:** React, TypeScript, Vite

## How it works

1. **Intake** parses the raw decision (question, options, free-text context) into structured state, surfacing any stakes or constraints the user implied but didn't say outright, for confirmation rather than silent assumption.
2. **Evidence gathering** runs 2 to 4 web searches through the evidence-server MCP tool before round 1. Personas work from this snapshot plus the user's own context; evidence isn't re-fetched mid-debate.
3. **Four personas debate in parallel**, one round at a time, each with a distinct job rather than a distinct personality:
   - **Skeptic** names concrete failure scenarios, not just general doubt.
   - **Optimist** quantifies or bounds the upside.
   - **Contrarian** attacks whichever claim currently has the most support in the ledger, by claim ID, and steelmans the underdog option.
   - **Pragmatist** only asserts claims traceable to evidence, and flags ungrounded claims from the others.
4. **Claim extraction** runs after every round: a structured-output LLM call classifies each distinct assertion as new, a restatement of an existing claim, or a resolution of one, so paraphrases get recognized instead of filed as duplicates.
5. **Convergence** is checked by a pure, table-tested function against `min_rounds`/`max_rounds`: the debate stops naturally once a round adds no new claims and resolves none, or is force-stopped at `max_rounds` with every still-contested claim flagged.
6. **Synthesis** turns the full ledger into a recommendation: which option (if any is clearly better), a pro/con tradeoff table, and a confidence note. The tradeoff table and the list of unresolved disagreements are derived directly from the ledger's data, not asked of the model, since a claim's recorded stance already determines which option it supports.
7. **Human review** pauses the graph (a real pause via the checkpointer, not an in-memory block) before anything is exported. The user can approve as-is, edit the recommendation, or reopen the debate for one more round without discarding the ledger.
8. **Export** renders the decision, recommendation, tradeoff table, and full claims ledger as an audit-trail appendix to Markdown, through the document-generator-server MCP tool.

## Convergence in practice

Every real debate run so far, across genuinely different topics, hit `max_rounds` still productive (`forced=True`); none converged naturally within a small round budget. This looks like a property of the design rather than bad luck: the Contrarian is built to always attack the ledger's strongest current claim and steelman the underdog, which keeps surfacing new angles instead of running out of things to say. A round with zero new claims and zero resolutions is architecturally rare when one of the four voices is explicitly rewarded for finding one.

Natural convergence is easiest to observe on narrow, low-stakes decisions with `min_rounds`/`max_rounds` set close together, or with a higher `max_rounds` ceiling and the patience (and token budget) to let the debate actually run dry.

## Worked example

[`examples/forced-convergence-example.md`](examples/forced-convergence-example.md) is a real debate: a 3-person team deciding whether to adopt Prettier, converged at round 4 with 66 tracked claims still unresolved. It shows the full claims ledger, the pro/con tradeoff table, and a recommendation that explicitly weighs which side's arguments actually held up under the Pragmatist's grounding checks versus which were flagged as unsupported inference.

## Project layout

```
backend/
  app/
    api/            REST endpoints, WebSocket endpoint, the debate manager
    graph/           LangGraph nodes, state schema, convergence logic
    mcp_servers/     evidence-server and document-generator-server
    models/          Pydantic schemas for structured LLM outputs
  tests/unit/        table-driven tests for convergence and stance normalization
frontend/
  src/
    components/      DebateView, Ledger, StatusBar, ReviewPanel
    hooks/           useDebateSocket: the single WebSocket connection
    state/           event reducer
examples/            a real, curated debate report
reports/             live-generated exports (not committed)
```

## Setup

### Backend

```
cd backend
cp .env.example .env
# fill in ANTHROPIC_API_KEY and SERPER_API_KEY in .env
uv sync
uv run uvicorn app.main:app --reload
```

The server listens on `http://localhost:8000`. Serper powers the evidence-server's web search tool; Anthropic powers every LLM call.

### Frontend

```
cd frontend
npm install
npm run dev
```

The dev server listens on `http://localhost:5173` and expects the backend at `localhost:8000`.

### Running just the graph (no API/UI)

```
cd backend
uv run python -m app.cli
```

Runs one sample debate end to end and prints the transcript, ledger, and recommendation to the terminal. Useful for checking the pipeline without a browser.

## API

- `POST /debates` starts a debate asynchronously and returns `{thread_id}`.
- `GET /debates/{thread_id}` returns the current state snapshot, used on page load and reconnect.
- `POST /debates/{thread_id}/resume` takes `{action: "approve" | "edit" | "reopen", payload}` and resumes the paused graph.
- `WS /debates/{thread_id}/stream` streams live events: `token`, `claim_added`, `claim_resolved`, `round_complete`, `converged`, `recommendation_ready`, `exported`.

## Testing

```
cd backend
uv run pytest tests/unit/
```

Covers the convergence routing function (table-driven against `min_rounds`/`max_rounds`, new/resolved claim counts) and stance normalization in claim extraction (matching a persona's freeform phrasing back to the decision's exact option strings).

## Cost

A real 4-round, 66-claim debate (the one in `examples/`) used 228,124 input tokens and 47,811 output tokens on `claude-sonnet-5`: about $0.93 at current introductory pricing, or about $1.40 at standard rates. Each round costs 4 persona calls plus one extraction call; intake, evidence-query generation, and synthesis each add one more. A debate that runs the full `max_rounds = 6` will cost more than this 4-round example.

## Known limitations

- Document upload (PDF/text ingestion into a per-debate evidence store) is scoped out of this version; personas work from web search results and the user's typed context only.
- Evidence is fetched once before round 1 and not refreshed mid-debate, even if a later round's claims reference something outside that snapshot.
- `max_rounds` is a fixed cap, not adaptive to how productive the debate still is when the cap is reached.
