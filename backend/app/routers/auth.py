from fastapi import APIRouter, Depends
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings.database import get_db
from app.oauth2 import create_access_token
from app.schemas.token_schemas import Token
from app.services.auth_services import get_user_for_loging

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=Token, summary="Log in",
    responses={403: {"description": "Invalid credentials"}},)
async def login(
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_for_loging(user_credentials, db)

    access_token = create_access_token(data={"user_id": user.id})

    return {"access_token": access_token, "token_type": "bearer", "is_admin": user.is_admin}
