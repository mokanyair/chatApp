import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.database import SessionLocal
from app.auth import decode_token
from app import models
from app.services.redis_service import get_redis, publish
from app.services.chat_service import ChatService

router = APIRouter()


@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    token: str = Query(...),
):
    await websocket.accept()

    # Authenticate
    try:
        user_id = decode_token(token)
    except ValueError:
        await websocket.close(code=4001)
        return

    # Verify participant membership
    db = SessionLocal()
    try:
        conversation = db.get(models.Conversation, conversation_id)
        if not conversation:
            await websocket.close(code=4004)
            return
        participant_ids = {u.id for u in conversation.participants}
        if user_id not in participant_ids:
            await websocket.close(code=4003)
            return
    finally:
        db.close()

    # Subscribe to this conversation's Redis channel
    channel = f"conversation:{conversation_id}"
    redis_client = await get_redis()
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    async def listen_redis():
        # Forward every Redis pub/sub message to this WebSocket client
        async for raw in pubsub.listen():
            if raw["type"] == "message":
                await websocket.send_json(json.loads(raw["data"]))

    async def listen_ws():
        # Receive messages from client, persist, and publish to Redis
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            content = (data.get("content") or "").strip()
            if not content:
                continue
            db = SessionLocal()
            try:
                message = ChatService.send_message(
                    db=db,
                    sender_id=user_id,
                    conversation_id=conversation_id,
                    content=content,
                )
                payload = {
                    "id": message.id,
                    "content": message.content,
                    "sender_id": message.sender_id,
                    "conversation_id": message.conversation_id,
                    "created_at": message.created_at.isoformat(),
                    "is_read": message.is_read,
                }
            finally:
                db.close()
            await publish(channel, payload)

    ws_task = asyncio.create_task(listen_ws())
    redis_task = asyncio.create_task(listen_redis())

    try:
        done, pending = await asyncio.wait(
            [ws_task, redis_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()


#app/routers/websocket.py                                                                                                       
#  - WS /ws/{conversation_id}?token=<JWT> endpoint                                                                                
#  - Accepts the connection, then validates the JWT and participant membership                                                    
#  - Subscribes to the Redis channel conversation:{id}                                                                            
#  - Runs two concurrent tasks:                                                                                                   
#    - listen_ws() — receives messages from the client, saves to DB via ChatService, publishes to Redis                           
#    - listen_redis() — receives from Redis pub/sub and forwards to the WebSocket client                                          
#  - When either task finishes (client disconnects), the other is cancelled and the pubsub is cleaned up 