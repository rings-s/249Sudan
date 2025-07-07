# app/courses/router.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.deps import get_current_user, get_verified_user, get_teacher_user
from app.accounts.models import User
from app.courses.service import CourseService
from app.courses.schemas import (
    Category, CategoryCreate, Course, CourseCreate, CourseUpdate, CourseList,
    Module, ModuleCreate, ModuleUpdate, Lesson, LessonCreate, LessonUpdate,
    Quiz, QuizCreate, QuizUpdate, Question, QuestionCreate,
    Enrollment, EnrollmentCreate, LessonProgress, LessonProgressUpdate,
    QuizAttempt, QuizSubmission, Certificate, CourseReview, CourseReviewCreate,
    StandardResponse, Tag
)
from app.utils.file_upload import save_course_content, save_avatar
from app.utils.security import validate_uuid

router = APIRouter()

# Categories
@router.get("/categories", response_model=List[Category])
async def get_categories(
    db: AsyncSession = Depends(get_db)
):
    """Get all active categories"""
    return await CourseService.get_categories(db)

@router.post("/categories", response_model=Category)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_teacher_user)
):
    """Create new category (teachers and above)"""
    return await CourseService.create_category(db, category_data)

@router.get("/categories/{slug}", response_model=Category)
async def get_category(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get category by slug"""
    return await CourseService.get_category_by_slug(db, slug)

# Courses
@router.get("/courses", response_model=List[CourseList])
async def get_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
    instructor_id: Optional[int] = None,
    featured_only: bool = False,
    my_courses: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get courses with filtering and pagination"""
    instructor_filter = None
    published_only = True
    
    if my_courses and current_user:
        instructor_filter = current_user.id
        published_only = False  # Show all courses for the instructor
    elif instructor_id:
        instructor_filter = instructor_id
    
    courses = await CourseService.get_courses(
        db=db,
        skip=skip,
        limit=limit,
        category_id=category_id,
        level=level,
        search=search,
        instructor_id=instructor_filter,
        featured_only=featured_only,
        published_only=published_only
    )
    
    # Add computed fields
    for course in courses:
        course.instructor_name = course.instructor.get_full_name() if course.instructor else None
        course.category_name = course.category.name if course.category else None
        course.enrolled_count = len([e for e in course.enrollments if e.is_active])
        
        # Calculate average rating
        if course.reviews:
            course.average_rating = sum(r.rating for r in course.reviews) / len(course.reviews)
    
    return courses

@router.post("/courses", response_model=Course)
async def create_course(
    course_data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_teacher_user)
):
    """Create new course (teachers and above)"""
    return await CourseService.create_course(db, course_data, current_user.id)

@router.get("/courses/{uuid}", response_model=Course)
async def get_course(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get course details by UUID"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    user_id = current_user.id if current_user else None
    course = await CourseService.get_course_by_uuid(db, uuid, user_id)
    
    # Add computed fields for response
    course.instructor_name = course.instructor.get_full_name() if course.instructor else None
    course.category_name = course.category.name if course.category else None
    course.enrolled_count = len([e for e in course.enrollments if e.is_active])
    
    if course.reviews:
        course.average_rating = sum(r.rating for r in course.reviews) / len(course.reviews)
    
    return course

@router.put("/courses/{uuid}", response_model=Course)
async def update_course(
    uuid: str,
    course_data: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Update course (instructor or admin only)"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    course = await CourseService.get_course_by_uuid(db, uuid)
    
    # Check permissions
    if (course.instructor_id != current_user.id and 
        current_user not in course.co_instructors and 
        not current_user.is_staff):
        raise HTTPException(status_code=403, detail="Not authorized to update this course")
    
    return await CourseService.update_course(db, course.id, course_data)

@router.post("/courses/{uuid}/enroll", response_model=StandardResponse)
async def enroll_in_course(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Enroll in course"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    course = await CourseService.get_course_by_uuid(db, uuid)
    enrollment = await CourseService.enroll_user(db, current_user.id, course.id)
    
    return StandardResponse(
        message="Successfully enrolled in course",
        data={"enrollment_id": str(enrollment.uuid)}
    )

@router.post("/courses/{uuid}/upload-thumbnail", response_model=StandardResponse)
async def upload_course_thumbnail(
    uuid: str,
    thumbnail: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Upload course thumbnail"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    course = await CourseService.get_course_by_uuid(db, uuid)
    
    # Check permissions
    if (course.instructor_id != current_user.id and 
        current_user not in course.co_instructors and 
        not current_user.is_staff):
        raise HTTPException(status_code=403, detail="Not authorized to update this course")
    
    thumbnail_path = await save_course_content(thumbnail)
    
    # Update course thumbnail
    from app.courses.schemas import CourseUpdate
    await CourseService.update_course(
        db, 
        course.id, 
        CourseUpdate(thumbnail=thumbnail_path)
    )
    
    return StandardResponse(
        message="Thumbnail uploaded successfully",
        data={"thumbnail_url": thumbnail_path}
    )

# Enrollments
@router.get("/enrollments/my-courses", response_model=List[Enrollment])
async def get_my_enrollments(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Get current user's enrollments"""
    return await CourseService.get_user_enrollments(db, current_user.id, status)

# Modules
@router.post("/modules", response_model=Module)
async def create_module(
    module_data: ModuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_teacher_user)
):
    """Create course module"""
    # Verify user can create modules for this course
    course = await CourseService._get_course_by_id(db, module_data.course_id)
    if (course.instructor_id != current_user.id and 
        current_user not in course.co_instructors and 
        not current_user.is_staff):
        raise HTTPException(status_code=403, detail="Not authorized to create modules for this course")
    
    return await CourseService.create_module(db, module_data)

# Lessons
@router.post("/lessons", response_model=Lesson)
async def create_lesson(
    lesson_data: LessonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_teacher_user)
):
    """Create lesson"""
    # Get module and verify permissions
    from sqlalchemy import select
    from app.courses.models import Module
    
    result = await db.execute(
        select(Module).where(Module.id == lesson_data.module_id)
    )
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    course = await CourseService._get_course_by_id(db, module.course_id)
    if (course.instructor_id != current_user.id and 
        current_user not in course.co_instructors and 
        not current_user.is_staff):
        raise HTTPException(status_code=403, detail="Not authorized to create lessons for this course")
    
    return await CourseService.create_lesson(db, lesson_data)

@router.get("/lessons/{uuid}", response_model=Lesson)
async def get_lesson(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Get lesson details"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    lesson = await CourseService.get_lesson_by_uuid(db, uuid)
    
    # Check if user is enrolled or is instructor
    course_id = lesson.module.course_id
    from sqlalchemy import select, and_
    from app.courses.models import Enrollment, Course
    
    # Check enrollment or instructor access
    enrollment_check = await db.execute(
        select(Enrollment).where(
            and_(
                Enrollment.student_id == current_user.id,
                Enrollment.course_id == course_id,
                Enrollment.is_active == True
            )
        )
    )
    
    course_check = await db.execute(
        select(Course).where(Course.id == course_id)
    )
    course = course_check.scalar_one()
    
    if (not enrollment_check.scalar_one_or_none() and 
        course.instructor_id != current_user.id and 
        current_user not in course.co_instructors and 
        not current_user.is_staff):
        raise HTTPException(status_code=403, detail="Not enrolled in this course")
    
    return lesson

@router.post("/lessons/{uuid}/complete", response_model=StandardResponse)
async def complete_lesson(
    uuid: str,
    progress_data: Optional[LessonProgressUpdate] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Mark lesson as completed"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    lesson = await CourseService.get_lesson_by_uuid(db, uuid)
    
    if not progress_data:
        progress_data = LessonProgressUpdate()
    
    progress = await CourseService.update_lesson_progress(
        db, current_user.id, lesson.id, progress_data, completed=True
    )
    
    return StandardResponse(
        message="Lesson completed successfully",
        data={"progress_id": str(progress.uuid)}
    )

@router.post("/lessons/{uuid}/upload-content", response_model=StandardResponse)
async def upload_lesson_content(
    uuid: str,
    content_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_teacher_user)
):
    """Upload lesson content file"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    lesson = await CourseService.get_lesson_by_uuid(db, uuid)
    course_id = lesson.module.course_id
    
    # Check permissions
    course = await CourseService._get_course_by_id(db, course_id)
    if (course.instructor_id != current_user.id and 
        current_user not in course.co_instructors and 
        not current_user.is_staff):
        raise HTTPException(status_code=403, detail="Not authorized to upload content for this lesson")
    
    file_path = await save_course_content(content_file)
    
    # Update lesson with file path
    from sqlalchemy import update
    from app.courses.models import Lesson as LessonModel
    
    await db.execute(
        update(LessonModel)
        .where(LessonModel.id == lesson.id)
        .values(file_attachment=file_path)
    )
    await db.commit()
    
    return StandardResponse(
        message="Content uploaded successfully",
        data={"file_url": file_path}
    )

# Quizzes
@router.post("/quizzes", response_model=Quiz)
async def create_quiz(
    quiz_data: QuizCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_teacher_user)
):
    """Create quiz"""
    # Verify permissions
    course = await CourseService._get_course_by_id(db, quiz_data.course_id)
    if (course.instructor_id != current_user.id and 
        current_user not in course.co_instructors and 
        not current_user.is_staff):
        raise HTTPException(status_code=403, detail="Not authorized to create quizzes for this course")
    
    return await CourseService.create_quiz(db, quiz_data)

@router.post("/quizzes/submit", response_model=QuizAttempt)
async def submit_quiz(
    submission: QuizSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Submit quiz attempt"""
    return await CourseService.submit_quiz(db, current_user.id, submission)

@router.get("/quizzes/{uuid}/attempts", response_model=List[QuizAttempt])
async def get_quiz_attempts(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Get user's quiz attempts"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    from sqlalchemy import select, and_
    from app.courses.models import Quiz as QuizModel, QuizAttempt as QuizAttemptModel
    
    # Get quiz
    quiz_result = await db.execute(
        select(QuizModel).where(QuizModel.uuid == uuid)
    )
    quiz = quiz_result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Get attempts
    attempts_result = await db.execute(
        select(QuizAttemptModel).where(
            and_(
                QuizAttemptModel.quiz_id == quiz.id,
                QuizAttemptModel.student_id == current_user.id
            )
        ).order_by(QuizAttemptModel.started_at.desc())
    )
    
    return attempts_result.scalars().all()

# Reviews
@router.post("/reviews", response_model=CourseReview)
async def create_course_review(
    review_data: CourseReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Create course review"""
    return await CourseService.create_review(db, current_user.id, review_data)

@router.get("/courses/{uuid}/reviews", response_model=List[CourseReview])
async def get_course_reviews(
    uuid: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get course reviews"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    course = await CourseService.get_course_by_uuid(db, uuid)
    
    from sqlalchemy import select
    from app.courses.models import CourseReview as CourseReviewModel
    
    result = await db.execute(
        select(CourseReviewModel)
        .where(
            and_(
                CourseReviewModel.course_id == course.id,
                CourseReviewModel.is_verified == True
            )
        )
        .order_by(CourseReviewModel.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    reviews = result.scalars().all()
    
    # Add student names
    for review in reviews:
        if review.student:
            review.student_name = review.student.get_full_name()
            review.student_avatar = review.student.avatar
    
    return reviews

# Certificates
@router.get("/certificates", response_model=List[Certificate])
async def get_user_certificates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Get user's certificates"""
    from sqlalchemy import select
    from app.courses.models import Certificate as CertificateModel
    
    result = await db.execute(
        select(CertificateModel)
        .where(CertificateModel.student_id == current_user.id)
        .order_by(CertificateModel.issue_date.desc())
    )
    
    return result.scalars().all()

@router.get("/certificates/{uuid}", response_model=Certificate)
async def get_certificate(
    uuid: str,
    db: AsyncSession = Depends(get_db)
):
    """Get certificate details (public endpoint for verification)"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    from sqlalchemy import select
    from app.courses.models import Certificate as CertificateModel
    
    result = await db.execute(
        select(CertificateModel).where(CertificateModel.uuid == uuid)
    )
    certificate = result.scalar_one_or_none()
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    return certificate

@router.get("/certificates/{uuid}/verify", response_model=dict)
async def verify_certificate(
    uuid: str,
    db: AsyncSession = Depends(get_db)
):
    """Verify certificate authenticity"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    from sqlalchemy import select
    from app.courses.models import Certificate as CertificateModel
    
    result = await db.execute(
        select(CertificateModel)
        .options(
            joinedload(CertificateModel.student),
            joinedload(CertificateModel.course)
        )
        .where(CertificateModel.uuid == uuid)
    )
    certificate = result.scalar_one_or_none()
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    return {
        "valid": certificate.is_valid,
        "certificate_number": certificate.certificate_number,
        "student_name": certificate.student.get_full_name(),
        "course_title": certificate.course.title,
        "issue_date": certificate.issue_date.isoformat(),
        "completion_date": certificate.completion_date.isoformat(),
        "final_score": float(certificate.final_score) if certificate.final_score else None
    }

# Analytics endpoints
@router.get("/courses/{uuid}/analytics", response_model=dict)
async def get_course_analytics(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Get course analytics (instructor only)"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    course = await CourseService.get_course_by_uuid(db, uuid)
    
    # Check permissions
    if (course.instructor_id != current_user.id and 
        current_user not in course.co_instructors and 
        not current_user.is_staff):
        raise HTTPException(status_code=403, detail="Not authorized to view analytics for this course")
    
    from sqlalchemy import select, func
    from app.courses.models import Enrollment as EnrollmentModel
    
    # Get enrollment statistics
    total_enrollments = await db.execute(
        select(func.count(EnrollmentModel.id))
        .where(EnrollmentModel.course_id == course.id)
    )
    
    active_enrollments = await db.execute(
        select(func.count(EnrollmentModel.id))
        .where(
            and_(
                EnrollmentModel.course_id == course.id,
                EnrollmentModel.is_active == True
            )
        )
    )
    
    completed_enrollments = await db.execute(
        select(func.count(EnrollmentModel.id))
        .where(
            and_(
                EnrollmentModel.course_id == course.id,
                EnrollmentModel.status == "completed"
            )
        )
    )
    
    avg_progress = await db.execute(
        select(func.avg(EnrollmentModel.progress_percentage))
        .where(
            and_(
                EnrollmentModel.course_id == course.id,
                EnrollmentModel.is_active == True
            )
        )
    )
    
    avg_rating = 0
    if course.reviews:
        avg_rating = sum(r.rating for r in course.reviews) / len(course.reviews)
    
    return {
        "total_enrollments": total_enrollments.scalar() or 0,
        "active_enrollments": active_enrollments.scalar() or 0,
        "completed_enrollments": completed_enrollments.scalar() or 0,
        "completion_rate": (completed_enrollments.scalar() or 0) / max(total_enrollments.scalar() or 1, 1) * 100,
        "average_progress": float(avg_progress.scalar() or 0),
        "average_rating": avg_rating,
        "total_reviews": len(course.reviews),
        "views_count": course.views_count
    }