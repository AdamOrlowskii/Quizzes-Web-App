from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.oauth2 import get_current_user
from app.schemas import FavouriteCreate
from app.services.favourites_services import add_quiz_to_favourites

router = APIRouter(prefix="/favourites", tags=["Favourite"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_to_favourites(
    favourite: FavouriteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await add_quiz_to_favourites(favourite, db, current_user)
