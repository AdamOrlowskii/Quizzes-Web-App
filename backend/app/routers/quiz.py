from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions.quiz_exceptions import (
    ActionAlreadyDoneException,
    CreatingQuizException,
    QuestionsNotFoundException,
    QuizNotFoundException,
    UserNotAuthorizedException,
    WrongFileTypeException,
)
from app.models import User as User_model
from app.oauth2 import get_current_user
from app.schemas import FavouriteCreate, QuestionUpdate, Quiz, QuizCreate, QuizOut
from app.services.quiz_services import (
    get_all_quizzes,
    get_my_favourite_quizzes,
    get_my_quizzes,
    get_one_quiz,
    get_questions,
    insert_new_quiz,
    remove_quiz,
    update_questions,
    update_quiz_values,
)

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])


@router.get("", response_model=List[QuizOut])
async def get_quizzes(
    db: AsyncSession = Depends(get_db),
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = "",
):
    return await get_all_quizzes(db, limit, skip, search)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Quiz)
async def create_quiz(
    file: UploadFile,
    title: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
    published: bool = True,
):
    try:
        return await insert_new_quiz(file, title, db, current_user, published)
    except WrongFileTypeException:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Wrong file type, please send only txt or pdf",
        )
    except CreatingQuizException:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Creating quiz error",
        )


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
    try:
        return await get_questions(id, db, current_user)
    except QuizNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {id} was not found",
        )
    except UserNotAuthorizedException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform requested action",
        )
    except QuestionsNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No questions found for quiz with id: {id}",
        )


@router.get("/{id}", response_model=QuizOut)
async def get_quiz(id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await get_one_quiz(id, db)
    except QuizNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {id} was not found",
        )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
):
    try:
        await remove_quiz(id, db, current_user)
    except QuizNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {id} does not exist",
        )
    except UserNotAuthorizedException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform requested action",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{id}", response_model=Quiz)
async def update_quiz(
    id: int,
    updated_quiz: QuizCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
):
    try:
        return await update_quiz_values(id, updated_quiz, db, current_user)
    except QuizNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {id} does not exist",
        )
    except UserNotAuthorizedException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform requested action",
        )


@router.put("/{id}/questions", status_code=status.HTTP_200_OK)
async def update_quiz_questions(
    id: int,
    questions: List[QuestionUpdate],
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
):
    try:
        result = await update_questions(id, questions, db, current_user)
        return result
    except QuizNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {id} was not found",
        )
    except UserNotAuthorizedException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform requested action",
        )


@router.post("/favourites", status_code=status.HTTP_201_CREATED)
async def add_quiz_to_favourites(
    favourite: FavouriteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
):
    try:
        return await add_quiz_to_favourites(favourite, db, current_user)
    except QuizNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {favourite.quiz_id} does not exist",
        )
    except ActionAlreadyDoneException:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User {current_user.id} has already added this quiz to favourites {favourite.quiz_id}",
        )
