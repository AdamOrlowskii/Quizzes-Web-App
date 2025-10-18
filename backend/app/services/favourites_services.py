from app.models import Favourite as FavouriteModel
from app.models import Quiz, User
from app.schemas import FavouriteCreate
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def add_quiz_to_favourites(
    favourite: FavouriteCreate,
    db: AsyncSession,
    current_user: User,
):
    result = await db.execute(select(Quiz).where(Quiz.id == favourite.quiz_id))

    quiz = result.scalar_one_or_none()

    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {favourite.quiz_id} does not exist",
        )

    result = await db.execute(
        select(FavouriteModel).where(
            FavouriteModel.quiz_id == favourite.quiz_id,
            FavouriteModel.user_id == current_user.id,
        )
    )

    found_favourite = result.scalar_one_or_none()

    if favourite.dir == 1:
        if found_favourite:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User {current_user.id} has already added this quiz to favourites {favourite.quiz_id}",
            )
        new_favourite = FavouriteModel(quiz_id=favourite.quiz_id, user_id=current_user.id)
        db.add(new_favourite)
        await db.commit()
        await db.refresh(new_favourite)
        return {"message": "successfully added to favourites"}
    else:
        if not found_favourite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Favourite does not exist"
            )

        await db.delete(found_favourite)
        await db.commit()

        return {"message": "successfully deleted from favourites"}