# app/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from app.config import settings

# =====================================================
# 1. DATABASE URL
# =====================================================
# Priority:
# 1. Environment variable from Docker / Production
# 2. Local fallback for development

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# =====================================================
# 2. SQLALCHEMY ENGINE
# =====================================================
# This is the actual connection manager to PostgreSQL.

engine = create_engine(
    DATABASE_URL,

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
# Every API request gets its own DB session.

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# =====================================================
# 4. BASE MODEL CLASS
# =====================================================
# All SQLAlchemy models inherit from this.

Base = declarative_base()

# =====================================================
# 5. FASTAPI DEPENDENCY
# =====================================================
# Inject DB session into routes safely.

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()