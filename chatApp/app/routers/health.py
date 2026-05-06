import structlog
import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal
from app.domain_metrics import dependency_healthy

router = APIRouter(tags=["Health"])
log = structlog.get_logger()


def _check_db() -> bool:
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    # Fresh client with short timeouts — avoids hanging on the shared pool
    # when Redis is unreachable.
    try:
        r = aioredis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        result = await r.ping()
        await r.aclose()
        return bool(result)
    except Exception:
        return False


@router.get("/health/live")
def liveness():
    """Process is alive."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness():
    """All dependencies are reachable."""
    db_ok    = _check_db()
    redis_ok = await _check_redis()

    dependency_healthy.labels(dependency="mysql").set(1 if db_ok    else 0)
    dependency_healthy.labels(dependency="redis").set(1 if redis_ok else 0)

    if not db_ok or not redis_ok:
        status = {
            "mysql": "ok" if db_ok    else "unreachable",
            "redis": "ok" if redis_ok else "unreachable",
        }
        log.error("readiness_check_failed", **status)
        raise HTTPException(status_code=503, detail=status)

    return {"mysql": "ok", "redis": "ok"}
