from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user_schemas import UserCreate


@pytest.fixture
def mock_db_session():
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_user_create():
    return UserCreate(
        email="newuser@example.com", password="SecurePassword123!", is_admin=False
    )


@pytest.fixture
def mock_user_credentials():
    credentials = MagicMock()
    credentials.username = "test@example.com"
    credentials.password = "password123"
    return credentials


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    user.password = "$2b$12$hashed_password_example"
    user.is_admin = False
    user.created_at = "2025-10-11 18:12:13.140951+02"
    return user


@pytest.fixture
def mock_admin_user():
    user = MagicMock()
    user.id = 2
    user.email = "admin@example.com"
    user.password = "$2b$12$hashed_password_example"
    user.is_admin = True
    user.created_at = "2025-10-12 18:12:13.140951+02"
    return user


@pytest.fixture
def sample_users_list(mock_user, mock_admin_user):
    return [mock_user, mock_admin_user]
