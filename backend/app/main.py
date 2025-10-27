# uvicorn app.main:app --reload --port 7000

# alembic revision --autogenerate -m ""
# alembic upgrade head

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.settings.config import settings
from app.routers import auth, quiz, user

print(settings.database_username)
# models.Base.metadata.create_all(bind=engine)

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


@app.get("/")
def root():
    return {"message": "Hello World"}
