from psycopg2 import IntegrityError
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

async def get_users(db: AsyncSession) -> User:
    result = await db.execute(select(User))
    users = result.scalars()

    return users

async def create_new_user(user: UserCreate, db: AsyncSession) -> User:
    try:
        hashed_password = hash(user.password)
        user.password = hashed_password

        new_user = User(**user.model_dump())

        if not new_user:
            raise UserCreatingException()

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        return new_user
    except IntegrityError:
        await db.rollback()
        raise


async def delete_account(db: AsyncSession, user: User):
    result = await db.execute(select(User).where(User.id == user.id))
    user = result.scalar_one_or_none()
 
    if not user:
        raise UserNotFoundException()

    await db.delete(user)
    await db.commit()
