import re

from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext

from app.models.user_models import User
from app.oauth2 import get_current_user

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash(password: str):
    return pwd_context.hash(password)


def verify(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def split_text(text: str, max_chunk_length: int):
    sentences = re.split(r"(?<=[.!?]) +", text)

    chunks = [""]

    i = 0
    sentences_in_chunk = 0

    for sentence in sentences:
        if sentences_in_chunk < max_chunk_length:
            if chunks[i]:
                chunks[i] += " "
            chunks[i] += sentence
            sentences_in_chunk += 1
        else:
            i += 1
            sentences_in_chunk = 1
            chunks.append(sentence)

    return chunks


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator permissions required",
        )
    return current_user
