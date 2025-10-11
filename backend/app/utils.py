import re

from passlib.context import CryptContext

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
