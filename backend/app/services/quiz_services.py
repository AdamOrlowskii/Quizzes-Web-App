from typing import List, Optional

from fastapi import (
    UploadFile,
)
from sqlalchemy import Result, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions.quiz_exceptions import (
    ActionAlreadyDoneException,
    CreatingQuizException,
    QuestionsNotFoundException,
    QuizNotFoundException,
    UserNotAuthorizedException,
    WrongFileTypeException,
)
from app.models.quiz_models import Favourite as Favourite_model
from app.models.quiz_models import Question as Question_model
from app.models.quiz_models import Quiz as Quiz_model
from app.models.user_models import User as User_model
from app.pdf_parser.parser import PDFParser
from app.schemas.quiz_schemas import FavouriteCreate, QuestionUpdate, QuizCreate
from app.services.llm_service import send_text_to_llm
from app.settings.config import settings
from app.utils import split_text

MAX_NUMBER_OF_SENTENCES_IN_ONE_CHUNK = settings.max_number_of_sentences_in_one_chunk


async def get_quiz_by_id(id, db) -> Quiz_model:
    result = await db.execute(select(Quiz_model).where(Quiz_model.id == id))
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundException()
    return quiz


async def get_all_quizzes(
    db: AsyncSession, limit: int, skip: int, search: Optional[str]
):
    
    count_query = select(func.count(Quiz_model.id)).where(Quiz_model.published)
    if search:
        count_query = count_query.where(Quiz_model.title.ilike(f"%{search}%"))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = (
        select(Quiz_model, func.count(Favourite_model.quiz_id).label("favourites"))
        .outerjoin(Favourite_model, Favourite_model.quiz_id == Quiz_model.id)
        .options(selectinload(Quiz_model.owner))
        .group_by(Quiz_model.id)
        .where(Quiz_model.published)
        .limit(limit)
        .offset(skip)
    )

    if search:
        query = query.where(Quiz_model.title.ilike(f"%{search}%"))

    result = await db.execute(query)
    quizzes = result.all()
    
    return {
        "items": quizzes,
        "total": total
    }


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
        raise WrongFileTypeException()

    new_quiz = Quiz_model(
        title=title, content=text_content, owner_id=current_user.id, published=published
    )
    db.add(new_quiz)
    await db.commit()
    await db.refresh(new_quiz)

    text_in_chunks = split_text(text_content, MAX_NUMBER_OF_SENTENCES_IN_ONE_CHUNK)

    try:
        quiz_questions = send_text_to_llm(text_in_chunks)
        
        if not quiz_questions:
            print("Warning: No questions generated, using fallback")
            # Opcjonalnie: dodaj fallback pytania lub rzuć wyjątek
            raise Exception("No questions generated from text")


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
    except Exception:
        raise CreatingQuizException()


async def get_my_favourite_quizzes(db: AsyncSession, current_user: User_model, limit: int, skip: int, search: str):
    count_query = (
        select(func.count(Quiz_model.id))
        .join(Favourite_model, Favourite_model.quiz_id == Quiz_model.id)
        .where(Favourite_model.user_id == current_user.id)
    )
    if search:
        count_query = count_query.where(Quiz_model.title.ilike(f"%{search}%"))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = (
        select(Quiz_model, func.count(Favourite_model.quiz_id).label("favourites"))
        .join(Favourite_model, Favourite_model.quiz_id == Quiz_model.id)
        .where(Favourite_model.user_id == current_user.id)
        .options(selectinload(Quiz_model.owner))
        .group_by(Quiz_model.id)
        .limit(limit)
        .offset(skip)
    )
    
    if search:
        query = query.where(Quiz_model.title.ilike(f"%{search}%"))
    
    result = await db.execute(query)
    quizzes = result.all()
    
    return {
        "items": quizzes,
        "total": total
    }


async def get_my_quizzes(db: AsyncSession, current_user: User_model, limit: int, skip: int, search: str):
    count_query = select(func.count(Quiz_model.id)).where(Quiz_model.owner_id == current_user.id)
    if search:
        count_query = count_query.where(Quiz_model.title.ilike(f"%{search}%"))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = (
        select(Quiz_model, func.count(Favourite_model.quiz_id).label("favourites"))
        .outerjoin(Favourite_model, Favourite_model.quiz_id == Quiz_model.id)
        .options(selectinload(Quiz_model.owner))
        .group_by(Quiz_model.id)
        .where(Quiz_model.owner_id == current_user.id)
        .limit(limit)
        .offset(skip)
    )
    
    if search:
        query = query.where(Quiz_model.title.ilike(f"%{search}%"))
    
    result = await db.execute(query)
    quizzes = result.all()
    
    return {
        "items": quizzes,
        "total": total
    }


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
        raise QuizNotFoundException()

    return quiz


async def get_questions(id, db, current_user) -> List[Question_model]:
    quiz = await get_quiz_by_id(id, db)

    if not quiz.published:
        if quiz.owner_id != current_user.id:
            raise UserNotAuthorizedException()

    result = await db.execute(
        select(Question_model).where(Question_model.quiz_id == id)
    )
    questions = result.scalars().all()

    if not questions:
        raise QuestionsNotFoundException()
    return questions


async def remove_quiz(id, db, current_user):
    quiz = await get_quiz_by_id(id, db)

    if quiz is None:
        raise QuizNotFoundException()

    if quiz.owner_id != current_user.id and not current_user.is_admin:
        raise UserNotAuthorizedException()

    await db.delete(quiz)
    await db.commit()


async def update_quiz_values(
    id: int,
    updated_quiz: QuizCreate,
    db: AsyncSession,
    current_user: User_model,
):
    quiz = await get_quiz_by_id(id, db)

    if quiz is None:
        raise QuizNotFoundException()

    if quiz.owner_id != current_user.id:
        raise UserNotAuthorizedException()

    for key, value in updated_quiz.dict().items():
        setattr(quiz, key, value)

    await db.commit()
    await db.refresh(quiz)
    return quiz


async def update_questions(
    id: int,
    questions: List[QuestionUpdate],
    db: AsyncSession,
    current_user: User_model,
):
    quiz = await get_quiz_by_id(id, db)
    if not quiz:
        raise QuizNotFoundException()

    if quiz.owner_id != current_user.id:
        raise UserNotAuthorizedException()

    await db.execute(delete(Question_model).where(Question_model.quiz_id == id))

    for question_data in questions:
        new_question = Question_model(
            quiz_id=id,
            question_text=question_data.question_text,
            answers=question_data.answers,
            correct_answer=question_data.correct_answer,
        )
        db.add(new_question)

    await db.commit()

    return {"message": f"Updated {len(questions)} questions"}


async def add_to_favourites(
    favourite: FavouriteCreate,
    db: AsyncSession,
    current_user: User_model,
):
    result = await db.execute(
        select(Quiz_model).where(Quiz_model.id == favourite.quiz_id)
    )

    quiz = result.scalar_one_or_none()

    if not quiz:
        raise QuizNotFoundException()

    result = await db.execute(
        select(Favourite_model).where(
            Favourite_model.quiz_id == favourite.quiz_id,
            Favourite_model.user_id == current_user.id,
        )
    )

    found_favourite = result.scalar_one_or_none()

    if favourite.dir == 1:
        if found_favourite:
            raise ActionAlreadyDoneException()

        new_favourite = Favourite_model(
            quiz_id=favourite.quiz_id, user_id=current_user.id
        )
        db.add(new_favourite)
        await db.commit()
        await db.refresh(new_favourite)
        return {"message": "Successfully added to favourites"}
    else:
        if not found_favourite:
            raise QuizNotFoundException()

        await db.delete(found_favourite)
        await db.commit()

        return {"message": "Successfully deleted from favourites"}
