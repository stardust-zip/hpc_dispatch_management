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

    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_client(client: TestClient) -> Generator[TestClient, None, None]:
    user = User(
        sub=1,
        full_name="Mock Admin",
        user_type=UserType.LECTURER,
        is_admin=True,
        username="admin",
        email="admin@mock.com",
        department_id=1,
    )

    def override_get_current_user():
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield client

    del app.dependency_overrides[get_current_user]
