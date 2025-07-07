# app/courses/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Date, ForeignKey, Decimal, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid as uuid_lib

from app.database import Base

# Many-to-many association table for course tags
course_tags = Table(
    'course_tags',
    Base.metadata,
    Column('course_id', Integer, ForeignKey('courses.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

# Many-to-many association table for course co-instructors
course_co_instructors = Table(
    'course_co_instructors',
    Base.metadata,
    Column('course_id', Integer, ForeignKey('courses.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
)

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    name = Column(String, unique=True, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    icon = Column(String, nullable=True)
    order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    parent = relationship("Category", remote_side=[id], back_populates="subcategories")
    subcategories = relationship("Category", back_populates="parent")
    courses = relationship("Course", back_populates="category")

class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    
    # Relationships
    courses = relationship("Course", secondary=course_tags, back_populates="tags")

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=False)
    short_description = Column(String, nullable=False)
    
    # Instructor
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Category and tags
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    # Course details
    level = Column(String, default="beginner")  # beginner, intermediate, advanced
    language = Column(String, default="en")
    thumbnail = Column(String, nullable=True)
    preview_video = Column(String, nullable=True)
    duration_hours = Column(Integer, default=0)
    prerequisites = Column(Text, nullable=True)
    learning_outcomes = Column(Text, nullable=False)
    
    # Status and settings
    status = Column(String, default="draft")  # draft, published, archived
    is_featured = Column(Boolean, default=False)
    enrollment_limit = Column(Integer, nullable=True)
    certificate_template = Column(Text, nullable=True)
    views_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    published_at = Column(DateTime, nullable=True)
    
    # Relationships
    instructor = relationship("User", foreign_keys=[instructor_id], back_populates="teaching_courses")
    co_instructors = relationship("User", secondary=course_co_instructors)
    category = relationship("Category", back_populates="courses")
    tags = relationship("Tag", secondary=course_tags, back_populates="courses")
    
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="course")
    quizzes = relationship("Quiz", back_populates="course")
    reviews = relationship("CourseReview", back_populates="course")
    certificates = relationship("Certificate", back_populates="course")

class Enrollment(Base):
    __tablename__ = "enrollments"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    
    enrolled_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    last_accessed = Column(DateTime, nullable=True)
    
    progress_percentage = Column(Decimal(5, 2), default=0)
    status = Column(String, default="enrolled")  # enrolled, in_progress, completed, dropped
    is_active = Column(Boolean, default=True)
    
    certificate_issued = Column(Boolean, default=False)
    certificate_issued_at = Column(DateTime, nullable=True)
    
    # Relationships
    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    lesson_progress = relationship("LessonProgress", back_populates="enrollment")
    quiz_attempts = relationship("QuizAttempt", back_populates="enrollment")
    certificate = relationship("Certificate", back_populates="enrollment", uselist=False)

class Module(Base):
    __tablename__ = "modules"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, default=0)
    is_published = Column(Boolean, default=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="module")

class Lesson(Base):
    __tablename__ = "lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    title = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Content
    content_type = Column(String, default="video")  # video, text, pdf, slides, interactive, assignment
    video_url = Column(String, nullable=True)
    video_duration = Column(Integer, nullable=True)  # seconds
    text_content = Column(Text, nullable=True)
    file_attachment = Column(String, nullable=True)
    
    # Settings
    order = Column(Integer, default=0)
    estimated_time_minutes = Column(Integer, default=10)
    is_preview = Column(Boolean, default=False)
    is_published = Column(Boolean, default=True)
    requires_submission = Column(Boolean, default=False)
    points = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    module = relationship("Module", back_populates="lessons")
    resources = relationship("Resource", back_populates="lesson", cascade="all, delete-orphan")
    progress_records = relationship("LessonProgress", back_populates="lesson")
    quizzes = relationship("Quiz", back_populates="lesson")

class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    last_position = Column(Integer, default=0)  # seconds
    is_completed = Column(Boolean, default=False)
    time_spent_seconds = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    
    # Relationships
    enrollment = relationship("Enrollment", back_populates="lesson_progress")
    lesson = relationship("Lesson", back_populates="progress_records")

class Resource(Base):
    __tablename__ = "resources"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    resource_type = Column(String, default="document")  # document, link, download, code
    file = Column(String, nullable=True)
    url = Column(String, nullable=True)
    order = Column(Integer, default=0)
    is_required = Column(Boolean, default=False)
    
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    lesson = relationship("Lesson", back_populates="resources")

class Quiz(Base):
    __tablename__ = "quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    
    title = Column(String, nullable=False)
    instructions = Column(Text, nullable=True)
    quiz_type = Column(String, default="practice")  # practice, graded, final, survey
    
    passing_score = Column(Integer, default=60)
    max_attempts = Column(Integer, default=3)
    time_limit_minutes = Column(Integer, nullable=True)
    
    randomize_questions = Column(Boolean, default=True)
    randomize_answers = Column(Boolean, default=True)
    show_correct_answers = Column(Boolean, default=True)
    
    available_from = Column(DateTime, nullable=True)
    available_until = Column(DateTime, nullable=True)
    is_published = Column(Boolean, default=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    course = relationship("Course", back_populates="quizzes")
    module = relationship("Module", back_populates="quizzes")
    lesson = relationship("Lesson", back_populates="quizzes")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz")

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    
    question_text = Column(Text, nullable=False)
    question_type = Column(String, default="multiple_choice")  # multiple_choice, true_false, short_answer, essay
    explanation = Column(Text, nullable=True)
    points = Column(Integer, default=1)
    order = Column(Integer, default=0)
    is_required = Column(Boolean, default=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    quiz = relationship("Quiz", back_populates="questions")
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")
    responses = relationship("QuestionResponse", back_populates="question")

class Answer(Base):
    __tablename__ = "answers"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    
    answer_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)
    order = Column(Integer, default=0)
    feedback = Column(Text, nullable=True)
    
    # Relationships
    question = relationship("Question", back_populates="answers")
    responses = relationship("QuestionResponse", back_populates="selected_answer")

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    score = Column(Decimal(5, 2), nullable=True)
    passed = Column(Boolean, default=False)
    time_taken_seconds = Column(Integer, nullable=True)
    attempt_number = Column(Integer, default=1)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="attempts")
    student = relationship("User", back_populates="quiz_attempts")
    enrollment = relationship("Enrollment", back_populates="quiz_attempts")
    responses = relationship("QuestionResponse", back_populates="attempt")

class QuestionResponse(Base):
    __tablename__ = "question_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    selected_answer_id = Column(Integer, ForeignKey("answers.id"), nullable=True)
    
    text_response = Column(Text, nullable=True)
    points_earned = Column(Decimal(5, 2), default=0)
    is_correct = Column(Boolean, nullable=True)
    feedback = Column(Text, nullable=True)
    
    answered_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    attempt = relationship("QuizAttempt", back_populates="responses")
    question = relationship("Question", back_populates="responses")
    selected_answer = relationship("Answer", back_populates="responses")

class Certificate(Base):
    __tablename__ = "certificates"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    certificate_number = Column(String, unique=True, nullable=False)
    
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    
    issue_date = Column(Date, server_default=func.current_date())
    expiry_date = Column(Date, nullable=True)
    completion_date = Column(Date, nullable=False)
    final_score = Column(Decimal(5, 2), nullable=True)
    
    pdf_file = Column(String, nullable=True)
    qr_code = Column(String, nullable=True)
    verification_url = Column(String, nullable=True)
    is_valid = Column(Boolean, default=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    student = relationship("User", back_populates="certificates")
    course = relationship("Course", back_populates="certificates")
    enrollment = relationship("Enrollment", back_populates="certificate")

class CourseReview(Base):
    __tablename__ = "course_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=False)
    is_verified = Column(Boolean, default=True)
    helpful_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    course = relationship("Course", back_populates="reviews")
    student = relationship("User", back_populates="course_reviews")