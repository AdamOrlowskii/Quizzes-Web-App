from fastapi import Depends, HTTPException, status

from app.models import User
from app.oauth2 import get_current_user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator permissions required",
        )
    return current_user
