"""FastAPI app entry point.

A thin transport layer: it starts graph runs, streams their custom events to
the browser over WebSocket, and forwards resume actions back into the graph
via the checkpointer's thread_id. The LangGraph app remains the source of
truth for all state.

Usage: uv run uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.api import rest, websocket
from app.api.debate_manager import DebateManager
from app.config import settings
from app.graph.builder import build_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    # one checkpointer connection and one compiled graph for the app's
    # lifetime; the manager built on top of it is shared across requests
    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db_path) as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        app.state.manager = DebateManager(graph)
        yield


app = FastAPI(title="Expert Panel API", lifespan=lifespan)

# local Vite dev server; adjust if the frontend is deployed elsewhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rest.router)
app.include_router(websocket.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
