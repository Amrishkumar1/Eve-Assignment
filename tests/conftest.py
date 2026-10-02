import os
import tempfile

# Set test environment before importing the application.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["AUTO_CREATE_TABLES"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app import models
from app.main import app


@pytest.fixture()
def client():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    test_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    # Register models and create tables in the test database.
    Base.metadata.create_all(bind=test_engine)

    tables = inspect(test_engine).get_table_names()
    assert "users" in tables, f"Missing users table. Found: {tables}"

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()
        os.unlink(db_path)