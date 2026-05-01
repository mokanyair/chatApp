from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import users, messages, conversations


# =====================================================
# APP INSTANCE
# =====================================================

app = FastAPI(title=settings.APP_NAME)


# =====================================================
# CORS
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
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