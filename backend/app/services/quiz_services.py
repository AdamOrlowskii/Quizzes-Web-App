import json
import tempfile
from typing import List, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom

import pymupdf
import pymupdf4llm
from reportlab.lib.pagesizes import letter
from fastapi import Response, UploadFile
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
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
from app.utils import smart_split, split_text

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

    return {"items": quizzes, "total": total}


async def insert_new_quiz(
    file: UploadFile,
    title: str,
    questions_total: str,
    db: AsyncSession,
    current_user: User_model,
    published: bool,
):
    text_content = None
    content = await file.read()

    if file.filename.endswith(".txt"):
        text_content = content.decode("utf-8")
    elif file.filename.endswith(".pdf"):
        # parser = PDFParser(content, debug=True)
        # text_content = parser.parse()
        pdf_doc = pymupdf.open(stream=content, filetype="pdf")

        text_content = pymupdf4llm.to_markdown(pdf_doc)

        pdf_doc.close()
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
        quiz_questions = send_text_to_llm(text_in_chunks, questions_total)

        if not quiz_questions:
            print("Warning: No questions generated, using fallback")
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


async def get_my_favourite_quizzes(
    db: AsyncSession, current_user: User_model, limit: int, skip: int, search: str
):
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

    return {"items": quizzes, "total": total}


async def get_my_quizzes(
    db: AsyncSession, current_user: User_model, limit: int, skip: int, search: str
):
    count_query = select(func.count(Quiz_model.id)).where(
        Quiz_model.owner_id == current_user.id
    )
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

    return {"items": quizzes, "total": total}


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


async def export_moodle_xml(quiz_id, db):
    result = await db.execute(select(Quiz_model).where(Quiz_model.id == quiz_id))
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundException
    
    questions_result = await db.execute(
        select(Question_model).where(Question_model.quiz_id == quiz_id)
    )
    questions = questions_result.scalars().all()
    
    root = ET.Element("quiz")
    
    for idx, q in enumerate(questions, 1):
        answers_dict = json.loads(q.answers) if isinstance(q.answers, str) else q.answers
        
        question = ET.SubElement(root, "question", type="multichoice")
        
        name = ET.SubElement(question, "name")
        name_text = ET.SubElement(name, "text")
        name_text.text = f"Question {idx}"
        
        questiontext = ET.SubElement(question, "questiontext", format="html")
        questiontext_text = ET.SubElement(questiontext, "text")
        questiontext_text.text = q.question_text
        
        ET.SubElement(question, "defaultgrade").text = "1"
        ET.SubElement(question, "penalty").text = "0.3333333"
        ET.SubElement(question, "shuffleanswers").text = "true"
        ET.SubElement(question, "single").text = "true"
        ET.SubElement(question, "answernumbering").text = "abc"
        
        for answer_key, answer_text in answers_dict.items():
            is_correct = answer_key == q.correct_answer
            fraction = "100" if is_correct else "0"
            
            answer = ET.SubElement(question, "answer", fraction=fraction, format="html")
            answer_text_elem = ET.SubElement(answer, "text")
            answer_text_elem.text = answer_text

    xml_string = ET.tostring(root, encoding='unicode')
    
    dom = minidom.parseString(xml_string)
    pretty_xml = dom.toprettyxml(indent="  ", encoding="UTF-8")
    
    return Response(
        content=pretty_xml,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{quiz.title}_moodle.xml"'
        },
    )


async def export_json(quiz_id, db):
    result = await db.execute(select(Quiz_model).where(Quiz_model.id == quiz_id))
    quiz = result.scalar_one_or_none()

    if not quiz:
        raise QuizNotFoundException

    questions_result = await db.execute(
        select(Question_model).where(Question_model.quiz_id == quiz_id)
    )
    questions = questions_result.scalars().all()

    export_data = {
        "quiz_title": quiz.title,
        "created_at": str(quiz.created_at),
        "total_questions": len(questions),
        "questions": [
            {
                "question": q.question_text,
                "answers": json.loads(q.answers)
                if isinstance(q.answers, str)
                else q.answers,
                "correct_answer": q.correct_answer,
            }
            for q in questions
        ],
    }

    return Response(
        content=json.dumps(export_data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{quiz.title}_questions.json"'
        },
    )


async def export_pdf(quiz_id: int, db: AsyncSession):
    try:
        pdfmetrics.registerFont(
            TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        )
        pdfmetrics.registerFont(
            TTFont(
                "DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            )
        )
        FONT_REGULAR = "DejaVu"
        FONT_BOLD = "DejaVu-Bold"
    except Exception:
        FONT_REGULAR = "Helvetica"
        FONT_BOLD = "Helvetica-Bold"
    result = await db.execute(select(Quiz_model).where(Quiz_model.id == quiz_id))
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise QuizNotFoundException
    questions_result = await db.execute(
        select(Question_model).where(Question_model.quiz_id == quiz_id)
    )
    questions = questions_result.scalars().all()
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_path = tmp_file.name
    tmp_file.close()
    c = canvas.Canvas(tmp_path, pagesize=letter)
    width, height = letter
    c.setFont(FONT_BOLD, 12)
    c.drawString(1 * inch, height - 0.8 * inch, f"Quiz: {quiz.title}")
    c.setFont(FONT_REGULAR, 10)
    c.drawString(1 * inch, height - 1.1 * inch, f"Total Questions: {len(questions)}")
    c.drawString(1 * inch, height - 1.35 * inch, "Name: ____________________________")
    c.drawString(4 * inch, height - 1.35 * inch, "Date: ____________________________")
    c.line(0.75 * inch, height - 1.5 * inch, width - 0.75 * inch, height - 1.5 * inch)
    y_position = height - 2 * inch
    answer_key = []
    
    number_to_letter = {'1': 'A', '2': 'B', '3': 'C', '4': 'D', '5': 'E', '6': 'F'}
    
    for idx, q in enumerate(questions, 1):
        if y_position < 2.5 * inch:
            c.showPage()
            y_position = height - 1 * inch
        c.setFont(FONT_BOLD, 8)
        question_text = f"{idx}. {q.question_text}"
        lines = smart_split(question_text, 70)
        for line in lines:
            c.drawString(1 * inch, y_position, line)
            y_position -= 0.2 * inch
        c.setFont(FONT_REGULAR, 8)
        answers = json.loads(q.answers) if isinstance(q.answers, str) else q.answers
        
        sorted_keys = sorted(answers.keys())
        for i, key in enumerate(sorted_keys):
            answer_letter = chr(65 + i)
            answer_text = f"   {answer_letter}. {answers[key]}"
            lines = smart_split(answer_text, 95)
            for line in lines:
                c.drawString(1.2 * inch, y_position, line)
                y_position -= 0.2 * inch
        
        correct_num = q.correct_answer
        correct_letter = number_to_letter.get(str(correct_num), correct_num)
        answer_key.append(f"{idx}. {correct_letter}")
        y_position -= 0.1 * inch
        
    c.showPage()
    c.setFont(FONT_BOLD, 10)
    title_width = c.stringWidth("ANSWER KEY", FONT_BOLD, 10)
    c.drawString((width - title_width) / 2, height - 1 * inch, "ANSWER KEY")
    c.line(0.75 * inch, height - 1.2 * inch, width - 0.75 * inch, height - 1.2 * inch)
    y_position = height - 1.6 * inch
    c.setFont(FONT_REGULAR, 8)
    page_center = width / 2
    col_spacing = 2 * inch
    col1_x = page_center - col_spacing
    col2_x = page_center
    col3_x = page_center + col_spacing
    for idx, answer in enumerate(answer_key):
        if idx % 3 == 0:
            x_pos = col1_x
        elif idx % 3 == 1:
            x_pos = col2_x
        else:
            x_pos = col3_x
        c.drawString(x_pos, y_position, answer)
        if (idx + 1) % 3 == 0:
            y_position -= 0.2 * inch
            if y_position < 1 * inch:
                c.showPage()
                c.setFont(FONT_BOLD, 12)
                title_width = c.stringWidth("ANSWER KEY (continued)", FONT_BOLD, 12)
                c.drawString((width - title_width) / 2, height - 1 * inch, "ANSWER KEY (continued)")
                c.setFont(FONT_REGULAR, 8)
                y_position = height - 1.5 * inch
    c.save()

    return FileResponse(
        tmp_path,
        media_type="application/pdf",
        filename=f"{quiz.title}_test.pdf",
        background=None,
    )
