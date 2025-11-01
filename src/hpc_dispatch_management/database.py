import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator

# Define the path for SQLite db.
# It will be created in the project root as 'hpc_dispatch.db'
DATABASE_FILE = "hpc_dispatch.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///./{DATABASE_FILE}"

# Create the SQLAlchey engine.
# connect_args is needed only for SQLite to allow multithreaded access.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create a SessionLocal class.
# This is a facotry for new database sessions.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class.
# Our databse models with inherit from this class.
Base = declarative_base()


def get_db() -> Generator:
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


def create_db_and_tables():
    """
    Function to create all db tables.
    """
    print(f"Creating databse tables at {os.path.abspath(DATABASE_FILE)}")
    Base.metadata.create_all(bind=engine)
