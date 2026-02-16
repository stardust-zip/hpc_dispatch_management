from collections.abc import Generator

import httpx
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .settings import settings

# Define the path for SQLite db.
# It will be created in the project root as 'hpc_dispatch.db'
# DATABASE_FILE = "hpc_dispatch.db"
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
print(f"Connecting to database: {SQLALCHEMY_DATABASE_URL}")

# Create the SQLAlchemy engine.
# The logic for SQLite's 'check_same_thread should only apply if we're using SQLite.
connect_args = (
    {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
)

# Create the SQLAlchey engine.
# connect_args is needed only for SQLite to allow multithreaded access.
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

# Create a SessionLocal class.
# This is a facotry for new database sessions.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create a Base class.
# Our databse models with inherit from this class.
class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get a db session.
    Yields a sesion for a single request and ensure it's
    closed afterward.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_http_client(request: Request) -> httpx.AsyncClient:
    """
    Dependency to get the shared httpx.AsyncClient instance.
    """
    return request.state.http_client


def create_db_and_tables():
    """
    Function to create all db tables.
    Only create table if using SQLite(for local dev).
    In production, migrations should handle the MySQL schema.
    """
    if settings.DATABASE_URL.startswith("sqlite"):
        print("Creating SQLite database tables...")
        Base.metadata.create_all(bind=engine)
