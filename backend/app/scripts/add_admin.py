from app.models.user_models import User, Base
from app.models.quiz_models import *
import asyncio

from psycopg2 import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.exceptions.user_exceptions import UserCreatingException
from app.models.user_models import User
from app.settings.config import settings
from app.settings.database import SQLALCHEMY_DATABASE_URL
from app.utils import hash

DEFAULT_ADMIN_EMAIL = settings.default_admin_email
DEFAULT_ADMIN_PASSWORD = settings.default_admin_password


async def create_admin() -> User:
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == "admin@main.com"))
        existing = result.scalar_one_or_none()

        if existing:
            print("Admin already exists!")
            return

        try:
            admin = User(
                email=DEFAULT_ADMIN_EMAIL,
                password=hash(DEFAULT_ADMIN_PASSWORD),
                is_admin=True,
            )

            if not admin:
                raise UserCreatingException()

            db.add(admin)
            await db.commit()
            await db.refresh(admin)

            return admin
        except IntegrityError:
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(create_admin())
