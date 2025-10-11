from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.oauth2 import create_access_token
from app.schemas import Token
from app.utils import verify

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.email == user_credentials.username)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials"
        )
    if not verify(user_credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials"
        )

    access_token = create_access_token(data={"user_id": user.id})

    print(f"CREATED TOKEN: {access_token}")  # DEBUG - CHECK THIS
    print(f"TOKEN LENGTH: {len(access_token)}")  # DEBUG

    return {"access_token": access_token, "token_type": "bearer"}
