from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool
    created_at: datetime

    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    is_admin: bool = False


class UserLogin(BaseModel):
    email: EmailStr
    password: str
