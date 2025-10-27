from datetime import datetime
from typing import Dict, Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.user_schemas import UserOut


class QuizBase(BaseModel):
    title: str
    content: str
    published: bool = True


class QuizCreate(QuizBase):
    pass


class Quiz(QuizBase):
    id: int
    created_at: datetime
    owner_id: int
    owner: UserOut

    class Config:
        orm_mode = True


class QuizOut(BaseModel):
    Quiz: Quiz
    favourites: int

    class Config:
        orm_mode = True


class FavouriteCreate(BaseModel):
    quiz_id: int
    dir: Literal[0, 1]


class QuestionUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    question_text: str
    answers: Dict[str, str]
    correct_answer: str


class QuestionOut(QuestionUpdate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    quiz_id: int
    question_text: str
    answers: Dict[str, str]
    correct_answer: str


class MessageResponse(BaseModel):
    message: str
