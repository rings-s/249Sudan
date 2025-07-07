# app/courses/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

# Enums
class CourseLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class CourseStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class EnrollmentStatus(str, Enum):
    ENROLLED = "enrolled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DROPPED = "dropped"

class ContentType(str, Enum):
    VIDEO = "video"
    TEXT = "text"
    PDF = "pdf"
    SLIDES = "slides"
    INTERACTIVE = "interactive"
    ASSIGNMENT = "assignment"

class QuizType(str, Enum):
    PRACTICE = "practice"
    GRADED = "graded"
    FINAL = "final"
    SURVEY = "survey"

class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"

# Category Schemas
class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    order: int = 0
    is_active: bool = True

class CategoryCreate(CategoryBase):
    parent_id: Optional[int] = None

class CategoryUpdate(CategoryBase):
    name: Optional[str] = None
    slug: Optional[str] = None

class Category(CategoryBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    parent_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    subcategories: List['Category'] = []

# Tag Schemas
class TagBase(BaseModel):
    name: str
    slug: str

class TagCreate(TagBase):
    pass

class Tag(TagBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int

# Course Schemas
class CourseBase(BaseModel):
    title: str
    slug: str
    description: str
    short_description: str
    level: CourseLevel = CourseLevel.BEGINNER
    language: str = "en"
    thumbnail: Optional[str] = None
    preview_video: Optional[str] = None
    duration_hours: int = 0
    prerequisites: Optional[str] = None
    learning_outcomes: str
    is_featured: bool = False
    enrollment_limit: Optional[int] = None

class CourseCreate(CourseBase):
    category_id: Optional[int] = None
    tags: List[str] = []

class CourseUpdate(CourseBase):
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    learning_outcomes: Optional[str] = None
    category_id: Optional[int] = None
    tags: List[str] = []

class CourseList(CourseBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    instructor_id: int
    category_id: Optional[int] = None
    status: CourseStatus
    views_count: int = 0
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    
    # Computed fields
    instructor_name: Optional[str] = None
    category_name: Optional[str] = None
    enrolled_count: int = 0
    average_rating: float = 0.0

class Course(CourseList):
    # Full course details with relationships
    instructor: Optional[dict] = None
    co_instructors: List[dict] = []
    category: Optional[Category] = None
    tags: List[Tag] = []
    modules: List['Module'] = []
    reviews: List['CourseReview'] = []
    is_enrolled: bool = False

# Module Schemas
class ModuleBase(BaseModel):
    title: str
    description: Optional[str] = None
    order: int = 0
    is_published: bool = True

class ModuleCreate(ModuleBase):
    course_id: int

class ModuleUpdate(ModuleBase):
    title: Optional[str] = None

class Module(ModuleBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    course_id: int
    created_at: datetime
    updated_at: datetime
    lessons: List['Lesson'] = []

# Lesson Schemas
class LessonBase(BaseModel):
    title: str
    slug: str
    description: Optional[str] = None
    content_type: ContentType = ContentType.VIDEO
    video_url: Optional[str] = None
    video_duration: Optional[int] = None
    text_content: Optional[str] = None
    order: int = 0
    estimated_time_minutes: int = 10
    is_preview: bool = False
    is_published: bool = True
    requires_submission: bool = False
    points: int = 0

class LessonCreate(LessonBase):
    module_id: int

class LessonUpdate(LessonBase):
    title: Optional[str] = None
    slug: Optional[str] = None

class Lesson(LessonBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    module_id: int
    file_attachment: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resources: List['Resource'] = []
    is_completed: bool = False

# Resource Schemas
class ResourceBase(BaseModel):
    title: str
    description: Optional[str] = None
    resource_type: str = "document"
    url: Optional[str] = None
    order: int = 0
    is_required: bool = False

class ResourceCreate(ResourceBase):
    lesson_id: int

class Resource(ResourceBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    lesson_id: int
    file: Optional[str] = None
    created_at: datetime

# Enrollment Schemas
class EnrollmentCreate(BaseModel):
    course_id: int

class Enrollment(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    student_id: int
    course_id: int
    enrolled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    progress_percentage: Decimal
    status: EnrollmentStatus
    is_active: bool
    certificate_issued: bool
    certificate_issued_at: Optional[datetime] = None

# Progress Schemas
class LessonProgressUpdate(BaseModel):
    last_position: int = 0
    time_spent_seconds: int = 0
    notes: Optional[str] = None

class LessonProgress(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    enrollment_id: int
    lesson_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    last_position: int = 0
    is_completed: bool = False
    time_spent_seconds: int = 0
    notes: Optional[str] = None

# Quiz Schemas
class AnswerBase(BaseModel):
    answer_text: str
    is_correct: bool = False
    order: int = 0
    feedback: Optional[str] = None

class AnswerCreate(AnswerBase):
    pass

class Answer(AnswerBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    question_id: int

class QuestionBase(BaseModel):
    question_text: str
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE
    explanation: Optional[str] = None
    points: int = 1
    order: int = 0
    is_required: bool = True

class QuestionCreate(QuestionBase):
    answers: List[AnswerCreate] = []

class QuestionUpdate(QuestionBase):
    question_text: Optional[str] = None
    answers: List[AnswerCreate] = []

class Question(QuestionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    quiz_id: int
    created_at: datetime
    updated_at: datetime
    answers: List[Answer] = []

class QuizBase(BaseModel):
    title: str
    instructions: Optional[str] = None
    quiz_type: QuizType = QuizType.PRACTICE
    passing_score: int = 60
    max_attempts: int = 3
    time_limit_minutes: Optional[int] = None
    randomize_questions: bool = True
    randomize_answers: bool = True
    show_correct_answers: bool = True
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    is_published: bool = False

class QuizCreate(QuizBase):
    course_id: int
    module_id: Optional[int] = None
    lesson_id: Optional[int] = None

class QuizUpdate(QuizBase):
    title: Optional[str] = None

class Quiz(QuizBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    course_id: int
    module_id: Optional[int] = None
    lesson_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    questions: List[Question] = []

# Quiz Attempt Schemas
class QuizAttemptResponse(BaseModel):
    question_id: int
    selected_answer_id: Optional[int] = None
    text_response: Optional[str] = None

class QuizSubmission(BaseModel):
    quiz_id: int
    responses: List[QuizAttemptResponse]

class QuizAttempt(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    quiz_id: int
    student_id: int
    enrollment_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    score: Optional[Decimal] = None
    passed: bool = False
    time_taken_seconds: Optional[int] = None
    attempt_number: int = 1

# Certificate Schemas
class Certificate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    certificate_number: str
    student_id: int
    course_id: int
    enrollment_id: int
    issue_date: date
    expiry_date: Optional[date] = None
    completion_date: date
    final_score: Optional[Decimal] = None
    pdf_file: Optional[str] = None
    qr_code: Optional[str] = None
    verification_url: Optional[str] = None
    is_valid: bool = True
    created_at: datetime
    updated_at: datetime

# Review Schemas
class CourseReviewBase(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str

class CourseReviewCreate(CourseReviewBase):
    course_id: int

class CourseReviewUpdate(CourseReviewBase):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None

class CourseReview(CourseReviewBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    course_id: int
    student_id: int
    is_verified: bool = True
    helpful_count: int = 0
    created_at: datetime
    updated_at: datetime
    student_name: Optional[str] = None
    student_avatar: Optional[str] = None

# Response Schemas
class StandardResponse(BaseModel):
    status: str = "success"
    message: str
    data: Optional[dict] = None

# Update forward references
Category.model_rebuild()
Module.model_rebuild()
Lesson.model_rebuild()
Resource.model_rebuild()