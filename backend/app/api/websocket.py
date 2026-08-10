"""WebSocket endpoint: on connect, subscribes to a debate's live custom-event
stream and relays every event to the browser; also accepts client actions
(approve/edit/reopen) inline on the same connection.
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["stream"])
logger = logging.getLogger(__name__)


async def _forward_to_client(websocket: WebSocket, queue: asyncio.Queue) -> None:
    while True:
        message = await queue.get()
        await websocket.send_json(message)


async def _handle_client_message(thread_id: str, message: dict, manager) -> None:
    msg_type = message.get("type")
    if msg_type == "approve":
        await manager.resume_approve(thread_id)
    elif msg_type == "edit":
        await manager.resume_approve(thread_id, recommendation_edits=message.get("recommendation"))
    elif msg_type == "reopen":
        await manager.reopen(thread_id, message.get("follow_up_question", ""))


@router.websocket("/debates/{thread_id}/stream")
async def debate_stream(websocket: WebSocket, thread_id: str) -> None:
    manager = websocket.app.state.manager
    await websocket.accept()
    queue = manager.subscribe(thread_id)
    forward_task = asyncio.create_task(_forward_to_client(websocket, queue))

    try:
        while True:
            message = await websocket.receive_json()
            await _handle_client_message(thread_id, message, manager)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - don't let a bad client message kill the process
        logger.exception("error handling message on debate %s", thread_id)
    finally:
        forward_task.cancel()
        manager.unsubscribe(thread_id, queue)
