from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User as User_model
from app.oauth2 import get_current_user
from app.schemas import Quiz, QuizCreate, QuizOut
from app.services.quiz_services import (
    get_all_quizzes,
    get_my_favourite_quizzes,
    get_my_quizzes,
    get_one_quiz,
    get_questions,
    insert_new_quiz,
    remove_quiz,
    update_quiz_values,
)

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])


@router.get("/", response_model=List[QuizOut])
async def get_quizzes(
    db: AsyncSession = Depends(get_db),
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = "",
):

    return await get_all_quizzes(db, limit, skip, search)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Quiz)
async def create_quiz(
    file: UploadFile,
    title: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
    published: bool = True,
):

    return await insert_new_quiz(file, title, db, current_user, published)


@router.get("/my_favourite_quizzes", response_model=List[QuizOut])
async def my_favourite_quizzes(
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = "",
):

    return await get_my_favourite_quizzes(db, current_user, limit, skip, search)


@router.get("/my_quizzes", response_model=List[QuizOut])
async def my_quizzes(
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = "",
):

    return await get_my_quizzes(db, current_user, limit, skip, search)


@router.get("/play/{id}")
async def play_the_quiz(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
):

    return await get_questions(id, db, current_user)


@router.get("/{id}", response_model=QuizOut)
async def get_quiz(id: int, db: AsyncSession = Depends(get_db)):

    return await get_one_quiz(id, db)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
):
    await remove_quiz(id, db, current_user)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{id}", response_model=Quiz)
async def update_quiz(
    id: int,
    updated_quiz: QuizCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
):
    return await update_quiz_values(id, updated_quiz, db, current_user)
