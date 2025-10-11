# uvicorn app.main:app --reload

# alembic revision --autogenerate -m ""
# alembic upgrade head

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import auth, favourite, quiz, user

print(settings.database_username)
# models.Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = ["*"]

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
app.include_router(favourite.router)


@app.get("/")
def root():
    return {"message": "Hello World"}
