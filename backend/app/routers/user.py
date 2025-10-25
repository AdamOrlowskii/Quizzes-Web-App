from fastapi import APIRouter, Depends, HTTPException, Response, status
from psycopg2 import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions.user_exceptions import UserNotFoundException
from app.models import User
from app.oauth2 import get_current_user
from app.schemas import UserCreate, UserOut
from app.services.user_services import create_new_user, delete_account, get_one_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=UserOut,
    summary="Sign up",
    responses={500: {"description": "User creation failed"}},
)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await create_new_user(user, db)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User already exists"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User creation failed: {e}",
        )


@router.delete(
    "/delete_account",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete users account",
    responses={404: {"description": "User not found"}},
)
async def delete_user(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        await delete_account(db, current_user)
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{id}", response_model=UserOut, summary="Get user data",
    responses={404: {"description": "User not found"}},)
async def get_user(id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await get_one_user(id, db)
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id: {id} does not exist",
        )
