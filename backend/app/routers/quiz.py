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
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.quiz_exceptions import (
    ActionAlreadyDoneException,
    CreatingQuizException,
    QuestionsNotFoundException,
    QuizNotFoundException,
    UserNotAuthorizedException,
    WrongFileTypeException,
)
from app.models.quiz_models import Question as Question_model
from app.models.quiz_models import Quiz as Quiz_model
from app.models.user_models import User as User_model
from app.oauth2 import get_current_user
from app.schemas.quiz_schemas import (
    FavouriteCreate,
    MessageResponse,
    PaginatedQuizResponse,
    QuestionOut,
    QuestionUpdate,
    Quiz,
    QuizCreate,
    QuizOut,
)
from app.services.quiz_services import (
    add_to_favourites,
    export_json,
    export_pdf,
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
from app.settings.database import get_db

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])


@router.get("", response_model=PaginatedQuizResponse, summary="Get all public quizzes")
async def get_quizzes(
    db: AsyncSession = Depends(get_db),
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = "",
):
    return await get_all_quizzes(db, limit, skip, search)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=Quiz,
    summary="Create new quiz",
    responses={
        422: {"description": "Wrong file type"},
        500: {"description": "Creating quiz error"},
    },
)
async def create_quiz(
    file: UploadFile,
    title: str = Form(...),
    total_questions: str = Form(default="20"),
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
    published: bool = True,
):
    total_questions = int(total_questions)
    try:
        return await insert_new_quiz(
            file, title, total_questions, db, current_user, published
        )
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


@router.get(
    "/my_favourite_quizzes",
    response_model=PaginatedQuizResponse,
    summary="Get quizzes marked as favourites",
)
async def my_favourite_quizzes(
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = "",
):
    return await get_my_favourite_quizzes(db, current_user, limit, skip, search)


@router.get(
    "/my_quizzes",
    response_model=PaginatedQuizResponse,
    summary="Get quizzes created by user",
)
async def my_quizzes(
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = "",
):
    return await get_my_quizzes(db, current_user, limit, skip, search)


@router.post(
    "/favourites",
    status_code=status.HTTP_201_CREATED,
    summary="Mark quiz as favourite",
    responses={
        404: {"description": "Quiz not found"},
        409: {"description": "User has already added this quiz to favourites"},
    },
)
async def add_quiz_to_favourites(
    favourite: FavouriteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
):
    try:
        return await add_to_favourites(favourite, db, current_user)
    except QuizNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {favourite.quiz_id} does not exist",
        )
    except ActionAlreadyDoneException:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User {current_user.id} has already added this quiz({favourite.quiz_id}) to favourites ",
        )


@router.get(
    "/play/{id}",
    response_model=List[QuestionOut],
    summary="Get all quiz quiestions",
    responses={
        403: {"description": "User not authorized to perform this action"},
        404: {"description": "Not found"},
    },
)
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


@router.get(
    "/{id}",
    response_model=QuizOut,
    summary="Get one quiz",
    responses={404: {"description": "Quiz not found"}},
)
async def get_quiz(id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await get_one_quiz(id, db)
    except QuizNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {id} was not found",
        )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove quiz",
    responses={
        403: {"description": "User not authorized to perform this action"},
        404: {"description": "Quiz not found"},
    },
)
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


@router.put(
    "/{id}",
    response_model=Quiz,
    summary="Update quiz description values",
    responses={
        403: {"description": "User not authorized to perform this action"},
        404: {"description": "Quiz not found"},
    },
)
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


@router.put(
    "/{id}/questions",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Update quiz questions",
    responses={
        403: {"description": "User not authorized to perform this action"},
        404: {"description": "Quiz not found"},
    },
)
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


@router.get(
    "/{quiz_id}/export/json",
    status_code=status.HTTP_201_CREATED,
    responses={404: {"description": "Quiz not found"}},
)
async def export_quiz_json(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
):
    try:
        return await export_json(quiz_id, db)
    except QuizNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {quiz_id} was not found",
        )


@router.get(
    "/{quiz_id}/export/pdf",
    status_code=status.HTTP_201_CREATED,
    responses={404: {"description": "Quiz not found"}},
)
async def export_quiz_pdf(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User_model = Depends(get_current_user),
):
    try:
        return await export_pdf(quiz_id, db)
    except QuizNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {quiz_id} was not found",
        )
