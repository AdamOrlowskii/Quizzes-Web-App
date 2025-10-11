from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Quiz, User
from app.oauth2 import get_current_user
from app.schemas import Favourite

router = APIRouter(prefix="/favourites", tags=["Favourite"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_to_favourites(
    favourite: Favourite,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Quiz).where(Quiz.id == favourite.quiz_id))

    quiz = result.scalar_one_or_none()

    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {favourite.quiz_id} does not exist",
        )

    result = await db.execute(
        select(Favourite).where(
            Favourite.quiz_id == favourite.quiz_id,
            Favourite.user_id == current_user.id,
        )
    )

    found_favourite = result.scalar_one_or_none()

    if favourite.dir == 1:
        if found_favourite:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User {current_user.id} has already added this quiz to favourites {favourite.quiz_id}",
            )
        new_favourite = Favourite(quiz_id=favourite.quiz_id, user_id=current_user.id)
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

        return {"messsage": "successfully deleted from favourites"}
