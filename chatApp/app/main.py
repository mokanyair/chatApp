from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import users, messages, conversations
from app.routers import websocket as ws_router
from app.services.redis_service import close_redis


# =====================================================
# APP INSTANCE
# =====================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)


# =====================================================
# CORS
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# HEALTH CHECK
# =====================================================

@app.get("/health")
def health_check():
    return {"status": "ok"}


# =====================================================
# ROUTERS
# =====================================================

app.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)

app.include_router(
    messages.router,
    prefix="/messages",
    tags=["Messages"]
)

app.include_router(
    conversations.router,
    prefix="/conversations",
    tags=["Conversations"]
)

app.include_router(
    ws_router.router,
    tags=["WebSocket"]
)