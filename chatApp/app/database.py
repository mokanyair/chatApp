# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# =====================================================
# 1. DATABASE URL
# =====================================================

if not settings.DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

# =====================================================
# 2. SQLALCHEMY ENGINE
# =====================================================

engine = create_engine(
    settings.DATABASE_URL,

    # verifies stale connections automatically
    pool_pre_ping=True,

    # number of permanent open connections
    pool_size=10,

    # extra temporary connections allowed
    max_overflow=20,

    # recycles dead connections every 30 mins
    pool_recycle=1800,

    # useful during development
    echo=False
)

# =====================================================
# 3. SESSION FACTORY
# =====================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# =====================================================
# 4. BASE MODEL CLASS
# =====================================================

Base = declarative_base()

# =====================================================
# 5. FASTAPI DEPENDENCY
# =====================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
