from unittest.mock import MagicMock, patch

import pytest
from app.services.auth_services import get_user_for_loging
from fastapi import HTTPException, status


@pytest.mark.asyncio
@patch("app.services.auth_services.verify")
async def test_successful_login(
    mock_verify, mock_db_session, mock_user_credentials, mock_user
):
    mock_verify.return_value = True
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db_session.execute.return_value = mock_result

    result = await get_user_for_loging(mock_user_credentials, mock_db_session)

    assert result == mock_user
    assert result.email == "test@example.com"


@pytest.mark.asyncio
async def test_login_user_not_found(mock_db_session, mock_user_credentials):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await get_user_for_loging(mock_user_credentials, mock_db_session)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "Invalid Credentials"
