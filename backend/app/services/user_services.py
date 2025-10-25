from app.exceptions.user_exceptions import UserCreatingException, UserNotFoundException
from app.models import User
from app.schemas import UserCreate
from app.utils import hash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_one_user(id: int, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == id))
    user = result.scalar_one_or_none()

    if not user:
        raise UserNotFoundException()

    return user


async def create_new_user(user: UserCreate, db: AsyncSession) -> User:
    hashed_password = hash(user.password)
    user.password = hashed_password

    new_user = User(**user.model_dump())

    if not new_user:
        raise UserCreatingException()

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


async def delete_account(db: AsyncSession, current_user: User):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    if not user:
        raise UserNotFoundException()

    await db.delete(user)
    await db.commit()
