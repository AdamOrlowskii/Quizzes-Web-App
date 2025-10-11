from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode["user_id"] = str(to_encode["user_id"])
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    print(f"Current time: {datetime.utcnow()}")  # DEBUG
    print(f"Token expires at: {expire}")  # DEBUG
    print(f"Minutes until expiration: {ACCESS_TOKEN_EXPIRE_MINUTES}")  # DEBUG

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str, credentials_exception) -> TokenData:
    try:
        print("Verifying token: {token[:50]}...")  # DEBUG
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print("Decoded payload: {payload}")  # DEBUG

        id: str = payload.get("user_id")
        print("Extracted user_id: {id}")  # DEBUG

        if id is None:
            print("ERROR: user_id is None!")  # DEBUG
            raise credentials_exception

        token_data = TokenData(id=id)
        print("Created token_data successfully")  # DEBUG
        return token_data

    except JWTError as e:
        print(f"JWT ERROR: {e}")  # DEBUG
        raise credentials_exception


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    print(f"Received token: {token}")  # DEBUG

    token_data = verify_access_token(token, credentials_exception)

    print(f"Token data ID: {token_data.id}, type: {type(token_data.id)}")  # DEBUG

    user_id = int(token_data.id)
    print(f"Querying for user_id: {user_id}")  # DEBUG

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    print(f"Found user: {user}")  # DEBUG

    if user is None:
        raise credentials_exception

    return user
