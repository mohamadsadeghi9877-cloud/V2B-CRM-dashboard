"""
CRM Database Connection & Session Management
Handles SQLite database initialization and sessions.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ghofreyar.crm_models import Base

# Database file location: in project root directory
DB_PATH = Path(__file__).resolve().parent.parent.parent / "ghofreyar_crm.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# create_engine: SQLite with multithreading support for FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# SessionLocal: database session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    جداول دیتابیس را در صورت عدم وجود می‌سازد.
    Creates all tables (companies, contacts, leads) if they don't exist.
    """
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Dependency injection generator for FastAPI endpoints.
    Provides a database session per request and safely closes it afterwards.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
