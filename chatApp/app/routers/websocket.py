import asyncio
import json
import time

import structlog
import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.config import settings
from app.database import SessionLocal
from app.auth import decode_token
from app import models
from app.services.redis_service import publish
from app.services.chat_service import ChatService
from app.domain_metrics import active_ws_connections, ws_message_latency

router = APIRouter()
log    = structlog.get_logger()


@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    token: str = Query(...),
):
    await websocket.accept()

    # ── Authenticate ──────────────────────────────────────────────────────────
    try:
        user_id = decode_token(token)
    except ValueError:
        log.warning("ws_auth_failed", reason="invalid_token", conversation_id=conversation_id)
        await websocket.close(code=4001)
        return

    # ── Verify participant membership ─────────────────────────────────────────
    db = SessionLocal()
    try:
        conversation = db.get(models.Conversation, conversation_id)
        if not conversation:
            log.warning("ws_conversation_not_found", conversation_id=conversation_id, user_id=user_id)
            await websocket.close(code=4004)
            return
        participant_ids = {u.id for u in conversation.participants}
        if user_id not in participant_ids:
            log.warning("ws_unauthorized", user_id=user_id, conversation_id=conversation_id)
            await websocket.close(code=4003)
            return
    finally:
        db.close()

    active_ws_connections.inc()
    log.info("ws_connected", user_id=user_id, conversation_id=conversation_id)

    channel = f"conversation:{conversation_id}"

    # Each connection gets a dedicated Redis client so subscriptions
    # don't compete on a shared connection and miss messages.
    pubsub_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = pubsub_client.pubsub()
    await pubsub.subscribe(channel)

    async def listen_redis():
        try:
            async for raw in pubsub.listen():
                if raw["type"] == "message":
                    await websocket.send_json(json.loads(raw["data"]))
        except Exception:
            pass

    async def listen_ws():
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            content = (data.get("content") or "").strip()
            if not content:
                continue

            t0 = time.perf_counter()
            db = SessionLocal()
            try:
                message = ChatService.send_message(
                    db=db,
                    sender_id=user_id,
                    conversation_id=conversation_id,
                    content=content,
                )
                payload = {
                    "id":              message.id,
                    "content":         message.content,
                    "sender_id":       message.sender_id,
                    "conversation_id": message.conversation_id,
                    "created_at":      message.created_at.isoformat(),
                    "is_read":         message.is_read,
                }
            finally:
                db.close()

            await publish(channel, payload)
            ws_message_latency.observe(time.perf_counter() - t0)

    redis_task = asyncio.create_task(listen_redis())
    ws_task    = asyncio.create_task(listen_ws())

    try:
        done, pending = await asyncio.wait(
            [ws_task, redis_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    finally:
        active_ws_connections.dec()
        log.info("ws_disconnected", user_id=user_id, conversation_id=conversation_id)
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await pubsub_client.aclose()
