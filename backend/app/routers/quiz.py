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
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import models, oauth2, schemas, utils
from ..config import settings
from ..database import get_db
from ..llm import send_text_to_llm
from ..pdf_parser.parser import PDFParser

MAX_NUMBER_OF_SENTENCES_IN_ONE_CHUNK = settings.max_number_of_sentences_in_one_chunk

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])


@router.get("/testauth")
async def test_auth(current_user: models.User = Depends(oauth2.get_current_user)):
    return {"user_id": current_user.id, "email": current_user.email}


@router.get("/", response_model=List[schemas.QuizOut])
async def get_quizzes(
    db: AsyncSession = Depends(get_db),
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = "",
):
    query = (
        select(models.Quiz, func.count(models.Favourite.quiz_id).label("favourites"))
        .outerjoin(models.Favourite, models.Favourite.quiz_id == models.Quiz.id)
        .options(selectinload(models.Quiz.owner))
        .group_by(models.Quiz.id)
        .where(models.Quiz.title.contains(search))
        .limit(limit)
        .offset(skip)
    )

    result = await db.execute(query)
    quizzes = result.all()

    return quizzes


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Quiz)
async def create_quiz(
    file: UploadFile,
    title: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    published: bool = True,
):
    content = await file.read()
    if file.filename.endswith(".txt"):
        text_content = content.decode("utf-8")
    elif file.filename.endswith(".pdf"):
        parser = PDFParser(content, debug=True)
        text_content = parser.parse()
        if text_content:
            print(f"Successfully extracted {len(text_content)} characters")
            preview = text_content[:200].replace("\n", " ")
            print(f"Preview: {preview}")
        else:
            print("No text extracted")

    if not text_content or len(text_content.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract text from PDF. Try a different file",
        )

    new_quiz = models.Quiz(
        title=title, content=text_content, owner_id=current_user.id, published=published
    )
    db.add(new_quiz)
    await db.commit()
    await db.refresh(new_quiz)

    text_in_chunks = utils.split_text(
        text_content, MAX_NUMBER_OF_SENTENCES_IN_ONE_CHUNK
    )

    quiz_questions = send_text_to_llm(text_in_chunks)

    result = await db.execute(select(func.max(models.Quiz.id)))
    max_quiz_id = result.scalar()

    for question in quiz_questions:
        new_question_to_database = models.Question(
            quiz_id=max_quiz_id,  # or simply use new_quiz.id
            question_text=question["Q"],
            answers=question["A"],
            correct_answer=question["C"],
        )
        db.add(new_question_to_database)

    await db.commit()
    # await db.refresh(new_question_to_database)

    return new_quiz


@router.get("/my_favourite_quizzes", response_model=List[schemas.QuizOut])
async def get_my_favourite_quizzes(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = "",
):
    query = (
        select(models.Quiz, func.count(models.Favourite.quiz_id).label("favourites"))
        .outerjoin(models.Favourite, models.Favourite.quiz_id == models.Quiz.id)
        .options(selectinload(models.Quiz.owner))
        .group_by(models.Quiz.id)
        .where(
            models.Favourite.user_id == current_user.id,
            models.Quiz.title.contains(search),
        )
        .limit(limit)
        .offset(skip)
    )

    result = await db.execute(query)
    quizzes = result.all()

    return quizzes


@router.get("/my_quizzes", response_model=List[schemas.QuizOut])
async def get_my_quizzes(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = "",
):
    query = (
        select(models.Quiz, func.count(models.Favourite.quiz_id).label("favourites"))
        .outerjoin(models.Favourite, models.Favourite.quiz_id == models.Quiz.id)
        .options(selectinload(models.Quiz.owner))
        .group_by(models.Quiz.id)
        .where(
            models.Quiz.owner_id == current_user.id,
            models.Quiz.title.contains(search),
        )
        .limit(limit)
        .offset(skip)
    )

    result = await db.execute(query)
    quizzes = result.all()

    return quizzes


@router.get("/my_quizzes/{id}", response_model=schemas.QuizOut)
async def get_my_quiz(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    query = (
        select(models.Quiz, func.count(models.Favourite.quiz_id).label("favourites"))
        .outerjoin(models.Favourite, models.Favourite.quiz_id == models.Quiz.id)
        .options(selectinload(models.Quiz.owner))
        .group_by(models.Quiz.id)
        .where(models.Quiz.id == id)
    )

    result = await db.execute(query)
    quiz = result.first()

    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {id} was not found",
        )
    if quiz[0].owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform requested action",
        )
    return quiz


@router.get("/play/{id}")
async def play_the_quiz(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    # Get the quiz
    result = await db.execute(select(models.Quiz).where(models.Quiz.id == id))
    quiz = result.scalar_one_or_none()

    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {id} was not found",
        )

    if not quiz.published:
        if quiz.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to perform requested action",
            )

    # Get the questions
    result = await db.execute(
        select(models.Question).where(models.Question.quiz_id == id)
    )
    questions = result.scalars().all()

    if not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No questions found for quiz with id: {id}",
        )

    return questions


@router.get("/{id}", response_model=schemas.QuizOut)
async def get_quiz(id: int, db: AsyncSession = Depends(get_db)):
    query = (
        select(models.Quiz, func.count(models.Favourite.quiz_id).label("favourites"))
        .outerjoin(models.Favourite, models.Favourite.quiz_id == models.Quiz.id)
        .options(selectinload(models.Quiz.owner))
        .group_by(models.Quiz.id)
        .where(models.Quiz.id == id)
    )

    result = await db.execute(query)
    quiz = result.first()

    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {id} was not found",
        )

    return quiz


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    result = db.execute(select(models.Quiz).where(models.Quiz.id == id))

    quiz = result.scalar_one_or_none()

    if quiz is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {id} does not exist",
        )

    if quiz.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform requested action",
        )

    await db.delete(quiz)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{id}", response_model=schemas.Quiz)
async def update_quiz(
    id: int,
    updated_quiz: schemas.QuizCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    result = await db.execute(select(models.Quiz).where(models.Quiz.id == id))

    quiz = result.scalar_one_or_none()

    if quiz is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {id} does not exist",
        )

    if quiz.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform requested action",
        )

    for key, value in updated_quiz.dict().items():
        setattr(quiz, key, value)

    await db.commit()
    await db.refresh(quiz)

    return quiz
