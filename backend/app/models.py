from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.database import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, nullable=False)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    published = Column(Boolean, server_default="TRUE", nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    owner_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    owner = relationship("User", back_populates="quizzes")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    quizzes = relationship("Quiz", back_populates="owner", cascade="all, delete-orphan")


class Favourite(Base):
    __tablename__ = "favourites"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    quiz_id = Column(
        Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), primary_key=True
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, nullable=False)
    quiz_id = Column(
        Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False
    )
    question_text = Column(String, nullable=False)
    answers = Column(JSON, nullable=False)
    correct_answer = Column(String, nullable=False)

    quiz = relationship("Quiz", back_populates="questions")
