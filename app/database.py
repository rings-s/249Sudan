# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
class Base(DeclarativeBase):
    pass

# Database dependency
async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

# Create tables
async def create_tables():
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from app.accounts.models import User, UserProfile
        from app.courses.models import (
            Category, Tag, Course, Enrollment, Module, Lesson,
            LessonProgress, Resource, Quiz, Question, Answer,
            QuizAttempt, QuestionResponse, Certificate, CourseReview
        )
        from app.core.models import (
            Forum, Discussion, Reply, Notification, LearningAnalytics,
            ActivityLog, MediaContent, Announcement, SupportTicket
        )
        
        await conn.run_sync(Base.metadata.create_all)