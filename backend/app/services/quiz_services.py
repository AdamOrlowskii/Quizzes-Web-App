from typing import Optional

from app.config import settings
from app.llm import send_text_to_llm
from app.models import Favourite as Favourite_model
from app.models import Question as Question_model
from app.models import Quiz as Quiz_model
from app.models import User as User_model
from app.pdf_parser.parser import PDFParser
from app.schemas import QuizCreate
from app.utils import split_text
from fastapi import (
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import Result, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

MAX_NUMBER_OF_SENTENCES_IN_ONE_CHUNK = settings.max_number_of_sentences_in_one_chunk


async def get_all_quizzes(
    db: AsyncSession, limit: int, skip: int, search: Optional[str]
) -> Result:
    query = (
        select(Quiz_model, func.count(Favourite_model.quiz_id).label("favourites"))
        .outerjoin(Favourite_model, Favourite_model.quiz_id == Quiz_model.id)
        .options(selectinload(Quiz_model.owner))
        .group_by(Quiz_model.id)
        .where(Quiz_model.title.contains(search))
        .limit(limit)
        .offset(skip)
    )

    result = await db.execute(query)
    return result


async def insert_new_quiz(
    file: UploadFile,
    title: str,
    db: AsyncSession,
    current_user: User_model,
    published: bool,
):
    text_content = None
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
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract text from PDF. Try a different file",
        )

    new_quiz = Quiz_model(
        title=title, content=text_content, owner_id=current_user.id, published=published
    )
    db.add(new_quiz)
    await db.commit()
    await db.refresh(new_quiz)

    text_in_chunks = split_text(text_content, MAX_NUMBER_OF_SENTENCES_IN_ONE_CHUNK)

    quiz_questions = send_text_to_llm(text_in_chunks)

    for question in quiz_questions:
        new_question_to_database = Question_model(
            quiz_id=new_quiz.id,
            question_text=question["Q"],
            answers=question["A"],
            correct_answer=question["C"],
        )
        db.add(new_question_to_database)

    await db.commit()
    await db.refresh(new_question_to_database)

    return new_quiz


async def get_my_favourite_quizzes(
    db: AsyncSession,
    current_user: User_model,
    limit: int,
    skip: int,
    search: Optional[str],
):
    query = (
        select(Quiz_model, func.count(Favourite_model.quiz_id).label("favourites"))
        .outerjoin(Favourite_model, Favourite_model.quiz_id == Quiz_model.id)
        .options(selectinload(Quiz_model.owner))
        .group_by(Quiz_model.id)
        .where(
            Favourite_model.user_id == current_user.id,
            Quiz_model.title.contains(search),
        )
        .limit(limit)
        .offset(skip)
    )

    result = await db.execute(query)
    return result


async def get_my_quizzes(
    db: AsyncSession,
    current_user: User_model,
    limit: int,
    skip: int,
    search: Optional[str],
) -> Result:
    query = (
        select(Quiz_model, func.count(Favourite_model.quiz_id).label("favourites"))
        .outerjoin(Favourite_model, Favourite_model.quiz_id == Quiz_model.id)
        .options(selectinload(Quiz_model.owner))
        .group_by(Quiz_model.id)
        .where(
            Quiz_model.owner_id == current_user.id,
            Quiz_model.title.contains(search),
        )
        .limit(limit)
        .offset(skip)
    )

    result = await db.execute(query)

    return result


async def get_one_quiz(id, db) -> Result:
    query = (
        select(Quiz_model, func.count(Favourite_model.quiz_id).label("favourites"))
        .outerjoin(Favourite_model, Favourite_model.quiz_id == Quiz_model.id)
        .options(selectinload(Quiz_model.owner))
        .group_by(Quiz_model.id)
        .where(Quiz_model.id == id)
    )

    result = await db.execute(query)
    quiz = result.first()

    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with id: {id} was not found",
        )

    return quiz


async def get_questions(id, db, current_user):
    result = await db.execute(select(Quiz_model).where(Quiz_model.id == id))
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

    result = await db.execute(
        select(Question_model).where(Question_model.quiz_id == id)
    )
    questions = result.scalars().all()

    if not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No questions found for quiz with id: {id}",
        )
    return questions


async def remove_quiz(id, db, current_user):
    result = await db.execute(select(Quiz_model).where(Quiz_model.id == id))

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


async def update_quiz_values(
    id: int,
    updated_quiz: QuizCreate,
    db: AsyncSession,
    current_user: User_model,
):
    result = await db.execute(select(Quiz_model).where(Quiz_model.id == id))

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
