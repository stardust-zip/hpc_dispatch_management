import logging
from collections.abc import Generator

import httpx
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .settings import settings

logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Ensure the connection is alive before using.
    pool_size=10,  # Keep up to 10 persistent connections open in the connection pool to handles request quickly wihout constantly reopening connections
    max_overflow=20,  # Allows the pool to temproraility to create up to 20 extra connecitons if there is a sudden spike in traffic
)

# Create a factory for generating new database sessions.
SessionLocal = sessionmaker(
    autocommit=False,  # Ensures the changes aren't saved to db unless you db.commit().
    autoflush=False,  # Prevents SQLAlchemy from auto pushing changes to db before executing queries.
    bind=engine,
)


# Defines the foudational class for all db models.
# In SQLAlchemy 2.0+, classes that inherit from Declartive Base auto mapped to db tables.
class Base(DeclarativeBase):
    pass


# A FastAPI Dependency. When an endpoiint need to talk to the db,
# it injects this functions.
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get a db sessions.
    """
    # Creates a fresh db session
    db = SessionLocal()
    try:
        # yields it to the route
        yield db
    # use finally to guarantee the session is closed after the route finished even if error occured.
    # , prevents memory leaks and exhausted connection pools
    finally:
        db.close()


# As main.py create http client and store it in app state,
# this function allows endpoints to grab that shared client
# to make requests to otehr microservices.
async def get_http_client(request: Request) -> httpx.AsyncClient:
    """Dependency to get the shared httpx.AsyncClient instance."""
    return request.state.http_client


def create_db_and_tables():
    """
    Function to create all db tables.
    If using Albemic migration in production, remove this.
    For local dev, this ensure tables are created in MySQL
    """
    logger.info("Ensure MySQL db exists...")
    Base.metadata.create_all(bind=engine)
