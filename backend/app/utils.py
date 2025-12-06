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


def smart_split(text, max_length):
    """Dzieli tekst po słowach, nie w środku"""
    if len(text) <= max_length:
        return [text]

    lines = []
    words = text.split(" ")
    current_line = []
    current_length = 0

    for word in words:
        word_length = len(word) + 1

        if current_length + word_length <= max_length:
            current_line.append(word)
            current_length += word_length
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word) + 1

    if current_line:
        lines.append(" ".join(current_line))

    return lines


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator permissions required",
        )
    return current_user
