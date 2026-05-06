import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.database import engine
from app.logging_config import setup_logging
from app.telemetry import setup_tracing
from app.routers import users, messages, conversations
from app.routers import websocket as ws_router
from app.routers import health as health_router
from app.services.redis_service import close_redis

setup_logging(debug=settings.DEBUG)
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("app_startup", service=settings.OTEL_SERVICE_NAME)
    yield
    await close_redis()
    log.info("app_shutdown")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# ── Tracing (instrument 1) ────────────────────────────────────────────────────
setup_tracing(
    app=app,
    engine=engine,
    service_name=settings.OTEL_SERVICE_NAME,
    otlp_endpoint=settings.OTLP_ENDPOINT,
)

# ── RED metrics — auto-instruments all routes (instrument 2) ──────────────────
Instrumentator(
    should_ignore_untemplated=True,
    excluded_handlers=["/metrics", "/health/live", "/health/ready"],
).instrument(app).expose(app, include_in_schema=False)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router.router)
app.include_router(users.router,         prefix="/users",         tags=["Users"])
app.include_router(messages.router,      prefix="/messages",      tags=["Messages"])
app.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
app.include_router(ws_router.router,     tags=["WebSocket"])
