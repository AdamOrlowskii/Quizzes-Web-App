from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, EmailStr, Field


class QuizBase(BaseModel):
    title: str
    content: str
    published: bool = True


class QuizCreate(QuizBase):
    pass


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        orm_mode = True


# Response model
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


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: Optional[str] = None


class Favourite(BaseModel):
    quiz_id: int
    dir: Annotated[int, Field(le=1)]
