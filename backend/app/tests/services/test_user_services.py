from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.exceptions.user_exceptions import UserCreatingException, UserNotFoundException
from app.services.user_services import (
    create_new_user,
    delete_account,
    get_one_user,
    get_users,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_one_user_success(mock_db_session, mock_user):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db_session.execute.return_value = mock_result

    result = await get_one_user(1, mock_db_session)

    assert result == mock_user
    assert result.id == mock_user.id
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_one_user_not_found(mock_db_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    with pytest.raises(UserNotFoundException):
        await get_one_user(999, mock_db_session)

    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_one_user_with_different_ids(mock_db_session):
    user_ids = [1, 5, 100, 999]

    for user_id in user_ids:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(UserNotFoundException):
            await get_one_user(user_id, mock_db_session)


@pytest.mark.asyncio
async def test_get_users_success(mock_db_session, sample_users_list):
    mock_result = MagicMock()
    mock_result.scalars.return_value = sample_users_list
    mock_db_session.execute.return_value = mock_result

    result = await get_users(mock_db_session)

    assert result == sample_users_list
    assert len(result) == len(sample_users_list)
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_users_empty_list(mock_db_session):
    mock_result = MagicMock()
    mock_result.scalars.return_value = []
    mock_db_session.execute.return_value = mock_result

    result = await get_users(mock_db_session)

    assert result == []
    assert len(result) == 0
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_users_multiple_users(mock_db_session):
    users = [MagicMock(id=i, email=f"user{i}@test.com") for i in range(1, 11)]
    mock_result = MagicMock()
    mock_result.scalars.return_value = users
    mock_db_session.execute.return_value = mock_result

    result = await get_users(mock_db_session)

    assert len(result) == 10
    assert result[0].id == 1
    assert result[9].id == 10


@pytest.mark.asyncio
@patch("app.services.user_services.User")
@patch("app.services.user_services.hash")
async def test_create_new_user_success(
    mock_hash, mock_user_class, mock_db_session, mock_user_create
):
    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock()
    mock_db_session.add = MagicMock()

    mock_hash.return_value = "hashed_password"
    mock_new_user = MagicMock()
    mock_new_user.id = 1
    mock_new_user.email = mock_user_create.email
    mock_new_user.password = "hashed_password"
    mock_user_class.return_value = mock_new_user

    result = await create_new_user(mock_user_create, mock_db_session)

    assert result is not None
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.user_services.User")
@patch("app.services.user_services.hash")
async def test_create_new_user_not_new_user(
    mock_hash, mock_user_class, mock_user_create
):
    mock_db_session = AsyncMock(spec=AsyncSession)
    mock_db_session.add = MagicMock()

    mock_hash.return_value = "hashed_password"
    mock_user_class.return_value = None

    with pytest.raises(UserCreatingException):
        await create_new_user(mock_user_create, mock_db_session)


@pytest.mark.asyncio
@patch("app.services.user_services.User")
@patch("app.services.user_services.hash")
async def test_create_new_user_password_hashed(
    mock_hash, mock_user_class, mock_db_session, mock_user_create
):
    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock()
    mock_db_session.add = MagicMock()
    original_password = mock_user_create.password

    mock_hash.return_value = "hashed_password"
    mock_new_user = MagicMock()
    mock_new_user.password = "hashed_password"
    mock_user_class.return_value = mock_new_user

    await create_new_user(mock_user_create, mock_db_session)

    mock_hash.assert_called_once_with(original_password)
    assert mock_user_create.password == "hashed_password"


@pytest.mark.asyncio
@patch("app.services.user_services.User")
@patch("app.services.user_services.hash")
async def test_create_new_user_db_operations_order(
    mock_hash, mock_user_class, mock_db_session, mock_user_create
):
    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock()
    mock_db_session.add = MagicMock()

    operations = []
    mock_db_session.add.side_effect = lambda x: operations.append("add")
    mock_db_session.commit.side_effect = lambda: operations.append("commit")
    mock_db_session.refresh.side_effect = lambda x: operations.append("refresh")

    mock_hash.return_value = "hashed_password"
    mock_new_user = MagicMock()
    mock_user_class.return_value = mock_new_user

    await create_new_user(mock_user_create, mock_db_session)

    assert operations == ["add", "commit", "refresh"]


@pytest.mark.asyncio
async def test_delete_account_success(mock_db_session, mock_user):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db_session.execute.return_value = mock_result
    mock_db_session.delete = AsyncMock()
    mock_db_session.commit = AsyncMock()

    await delete_account(mock_db_session, mock_user)

    mock_db_session.execute.assert_called_once()
    mock_db_session.delete.assert_called_once_with(mock_user)
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_account_user_not_found(mock_db_session, mock_user):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    with pytest.raises(UserNotFoundException):
        await delete_account(mock_db_session, mock_user)

    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_delete_account_operations_order(mock_db_session, mock_user):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db_session.execute.return_value = mock_result

    operations = []
    mock_db_session.delete = AsyncMock(
        side_effect=lambda x: operations.append("delete")
    )
    mock_db_session.commit = AsyncMock(side_effect=lambda: operations.append("commit"))

    await delete_account(mock_db_session, mock_user)

    assert operations == ["delete", "commit"]


@pytest.mark.asyncio
async def test_delete_account_deletes_correct_user(mock_db_session, mock_user):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db_session.execute.return_value = mock_result
    mock_db_session.delete = AsyncMock()
    mock_db_session.commit = AsyncMock()

    await delete_account(mock_db_session, mock_user)

    mock_db_session.delete.assert_called_once_with(mock_user)
