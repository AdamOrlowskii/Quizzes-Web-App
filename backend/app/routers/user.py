from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.oauth2 import get_current_user
from app.schemas import UserCreate, UserOut
from app.services.user_services import create_new_user, delete_account, get_one_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UserOut)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
     
    return await create_new_user(user, db)


@router.delete("/delete_account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    await delete_account(db, current_user)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{id}", response_model=UserOut)
async def get_user(id: int, db: AsyncSession = Depends(get_db)):

    return await get_one_user(id, db)
