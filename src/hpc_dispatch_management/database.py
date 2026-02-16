from collections.abc import Generator

import httpx
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .settings import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
print(f"Connection to database: {SQLALCHEMY_DATABASE_URL}")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Ensure the connection is alive before using.
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get a db sessions.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_http_client(request: Request) -> httpx.AsyncClient:
    """Dependency to get the shared httpx.AsyncClient instance."""
    return request.state.http_client


def create_db_and_tables():
    """
    Function to create all db tables.
    If using Albemic migration in production, remove this.
    For local dev, this ensure tables are created in MySQL
    """
    print("Ensure MySQL db exists...")
    Base.metadata.create_all(bind=engine)
