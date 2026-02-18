import os

os.environ["DATABASE_URL"] = (
    "mysql+pymysql://test_user:test_password@localhost:3309/dispatch_test"
)

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from hpc_dispatch_management.database import Base, get_db
from hpc_dispatch_management.main import app
from hpc_dispatch_management.schemas import User, UserType
from hpc_dispatch_management.security import get_current_user

engine = create_engine(
    "mysql+pymysql://test_user:test_password@localhost:3309/dispatch_test"
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        return db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_auth_client(client: TestClient) -> Generator[TestClient, None, None]:
    client.headers.update({"Authorization": "Bearer admin"})
    yield client


@pytest.fixture(scope="function")
def lecturer1_auth_client(client: TestClient) -> Generator[TestClient, None, None]:
    client.headers.update({"Authorization": "Bearer lecturer1"})
    yield client


@pytest.fixture(scope="function")
def lecturer2_auth_client(client: TestClient) -> Generator[TestClient, None, None]:
    client.headers.update({"Authorization": "Bearer lecturer2"})
    yield client
