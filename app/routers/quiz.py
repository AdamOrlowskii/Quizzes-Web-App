from fastapi import FastAPI, Form, Response, status, HTTPException, Depends, APIRouter, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Annotated
from .. import models, schemas, oauth2, utils
from ..database import get_db
import re
from ..config import settings

MAX_NUMBER_OF_SENTENCES_IN_ONE_CHUNK = settings.max_number_of_sentences_in_one_chunk

router = APIRouter(
    prefix="/quizzes",
    tags=['Quizzes']
)


@router.get("/", response_model=List[schemas.QuizOut])
def get_quizzes(db: Session = Depends(get_db), limit: int = 10, skip: int = 0, search: Optional[str] = ""):

    quizzes = db.query(models.Quiz, func.count(models.Vote.quiz_id).label("votes")).join(models.Vote, models.Vote.quiz_id == models.Quiz.id, isouter=True).group_by(models.Quiz.id).filter(models.Quiz.title.contains(search)).limit(limit).offset(skip).all()

    return quizzes


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Quiz)
async def create_quiz(file: UploadFile, title: str = Form(...), db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user), published: bool = True):

    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="Wrong file format. Only accepts .txt")
    if not file.size > 1:
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="File is empty")
    
    content = await file.read()
    text_content = content.decode('utf-8')
    new_quiz = models.Quiz(title=title, content=text_content, owner_id=current_user.id, published=published)
    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)

    text_in_chunks = utils.split_text(text_content, MAX_NUMBER_OF_SENTENCES_IN_ONE_CHUNK)
    #print(text_in_chunks)

    return new_quiz


@router.get("/my_favourite_quizzes", response_model=List[schemas.QuizOut])
def get_my_favourite_quizzes(db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user), limit: int = 10, skip: int = 0, search: Optional[str] = ""):

    quizzes = db.query(models.Quiz, func.count(models.Vote.quiz_id).label("votes")).join(models.Vote, models.Vote.quiz_id == models.Quiz.id, isouter=True).group_by(models.Quiz.id).filter(models.Vote.user_id == current_user.id, models.Quiz.title.contains(search)).limit(limit).offset(skip).all()
    return quizzes


@router.get("/my_quizzes", response_model=List[schemas.QuizOut])
def get_my_quizzes(db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user), limit: int = 10, skip: int = 0, search: Optional[str] = ""):

    quizzes = db.query(models.Quiz, func.count(models.Vote.quiz_id).label("votes")).join(models.Vote, models.Vote.quiz_id == models.Quiz.id, isouter=True).group_by(models.Quiz.id).filter(models.Quiz.owner_id == current_user.id, models.Quiz.title.contains(search)).limit(limit).offset(skip).all()
    return quizzes


@router.get("/my_quizzes/{id}", response_model=schemas.QuizOut)
def get_my_quiz(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):

    quiz = db.query(models.Quiz, func.count(models.Vote.quiz_id).label("votes")).join(models.Vote, models.Vote.quiz_id == models.Quiz.id, isouter=True).group_by(models.Quiz.id).filter(models.Quiz.id == id).first()

    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quiz with id: {id} was not found")
    if quiz[0].owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform requested action")

    return quiz


@router.get("/{id}", response_model=schemas.QuizOut)
def get_quiz(id: int, db: Session = Depends(get_db)):

    quiz = db.query(models.Quiz, func.count(models.Vote.quiz_id).label("votes")).join(models.Vote, models.Vote.quiz_id == models.Quiz.id, isouter=True).group_by(models.Quiz.id).filter(models.Quiz.id == id).first()

    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quiz with id: {id} was not found")

    return quiz


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quiz(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):

    quiz_query = db.query(models.Quiz).filter(models.Quiz.id == id)
    quiz = quiz_query.first()

    if quiz == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quiz with id: {id} does not exist")
    
    if quiz.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform requested action")

    quiz_query.delete(synchronize_session=False)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{id}", response_model=schemas.Quiz)
def update_quiz(id: int, updated_quiz: schemas.QuizCreate, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):

    quiz_query = db.query(models.Quiz).filter(models.Quiz.id == id)
    quiz = quiz_query.first()

    if quiz == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quiz with id: {id} does not exist")
    
    if quiz.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform requested action")

    quiz_query.update(updated_quiz.dict(), synchronize_session=False)

    db.commit()

    return quiz_query.first()