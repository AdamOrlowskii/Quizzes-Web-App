from app.models import User
from app.schemas import UserCreate
from app.utils import hash
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_one_user(id: int, db: AsyncSession):
    result = await db.execute(select(User).where(User.id == id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id: {id} does not exist",
        )

    return user


async def create_new_user(user: UserCreate, db: AsyncSession):
    hashed_password = hash(user.password)
    user.password = hashed_password

    new_user = User(**user.model_dump())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


async def delete_account(db: AsyncSession, current_user: User):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You do not exist. This should not have happened, so there is a bug somewhere",
        )

    await db.delete(user)
    await db.commit()
