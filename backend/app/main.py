from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, quiz, user
from app.settings.config import settings

print(settings.database_username)

app = FastAPI()

origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(quiz.router)
app.include_router(user.router)
app.include_router(auth.router)
