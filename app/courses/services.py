# app/courses/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, or_, and_
from sqlalchemy.orm import selectinload, joinedload
from fastapi import HTTPException, status
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import uuid
import qrcode
from io import BytesIO
import base64

from app.courses.models import (
    Category, Tag, Course, Module, Lesson, LessonProgress, Resource,
    Quiz, Question, Answer, QuizAttempt, QuestionResponse,
    Enrollment, Certificate, CourseReview, course_tags
)
from app.courses.schemas import (
    CategoryCreate, CategoryUpdate, CourseCreate, CourseUpdate,
    ModuleCreate, ModuleUpdate, LessonCreate, LessonUpdate,
    QuizCreate, QuizUpdate, QuestionCreate, EnrollmentCreate,
    CourseReviewCreate, QuizSubmission, LessonProgressUpdate
)
from app.accounts.models import User

class CourseService:
    
    @staticmethod
    async def create_category(db: AsyncSession, category_data: CategoryCreate) -> Category:
        """Create new category"""
        category = Category(**category_data.model_dump())
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category
    
    @staticmethod
    async def get_categories(db: AsyncSession, active_only: bool = True) -> List[Category]:
        """Get all categories"""
        query = select(Category).options(selectinload(Category.subcategories))
        if active_only:
            query = query.where(Category.is_active == True)
        query = query.order_by(Category.order, Category.name)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_category_by_slug(db: AsyncSession, slug: str) -> Category:
        """Get category by slug"""
        result = await db.execute(
            select(Category)
            .options(selectinload(Category.subcategories))
            .where(Category.slug == slug, Category.is_active == True)
        )
        category = result.scalar_one_or_none()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category
    
    @staticmethod
    async def create_course(db: AsyncSession, course_data: CourseCreate, instructor_id: int) -> Course:
        """Create new course"""
        # Handle tags
        tags_data = course_data.tags
        course_dict = course_data.model_dump(exclude={'tags'})
        course_dict['instructor_id'] = instructor_id
        
        course = Course(**course_dict)
        db.add(course)
        await db.commit()
        await db.refresh(course)
        
        # Add tags
        if tags_data:
            for tag_name in tags_data:
                tag = await CourseService._get_or_create_tag(db, tag_name)
                course.tags.append(tag)
        
        await db.commit()
        return course
    
    @staticmethod
    async def get_courses(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        category_id: Optional[int] = None,
        level: Optional[str] = None,
        search: Optional[str] = None,
        instructor_id: Optional[int] = None,
        featured_only: bool = False,
        published_only: bool = True
    ) -> List[Course]:
        """Get courses with filtering"""
        query = select(Course).options(
            joinedload(Course.instructor),
            joinedload(Course.category),
            selectinload(Course.tags)
        )
        
        if published_only:
            query = query.where(Course.status == "published")
        
        if category_id:
            query = query.where(Course.category_id == category_id)
        
        if level:
            query = query.where(Course.level == level)
        
        if instructor_id:
            query = query.where(Course.instructor_id == instructor_id)
        
        if featured_only:
            query = query.where(Course.is_featured == True)
        
        if search:
            query = query.where(
                or_(
                    Course.title.ilike(f"%{search}%"),
                    Course.description.ilike(f"%{search}%"),
                    Course.short_description.ilike(f"%{search}%")
                )
            )
        
        query = query.order_by(Course.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_course_by_uuid(db: AsyncSession, uuid: str, user_id: Optional[int] = None) -> Course:
        """Get course by UUID with all details"""
        result = await db.execute(
            select(Course)
            .options(
                joinedload(Course.instructor),
                selectinload(Course.co_instructors),
                joinedload(Course.category),
                selectinload(Course.tags),
                selectinload(Course.modules).selectinload(Module.lessons),
                selectinload(Course.reviews).joinedload(CourseReview.student)
            )
            .where(Course.uuid == uuid)
        )
        course = result.scalar_one_or_none()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Check if user is enrolled
        if user_id:
            enrollment_result = await db.execute(
                select(Enrollment).where(
                    and_(
                        Enrollment.course_id == course.id,
                        Enrollment.student_id == user_id,
                        Enrollment.is_active == True
                    )
                )
            )
            course.is_enrolled = enrollment_result.scalar_one_or_none() is not None
        
        return course
    
    @staticmethod
    async def update_course(
        db: AsyncSession, 
        course_id: int, 
        course_data: CourseUpdate
    ) -> Course:
        """Update course"""
        course = await CourseService._get_course_by_id(db, course_id)
        
        # Handle tags
        tags_data = course_data.tags if hasattr(course_data, 'tags') else None
        update_dict = course_data.model_dump(exclude={'tags'}, exclude_unset=True)
        
        if update_dict:
            await db.execute(
                update(Course).where(Course.id == course_id).values(**update_dict)
            )
        
        # Update tags if provided
        if tags_data is not None:
            # Clear existing tags
            course.tags.clear()
            # Add new tags
            for tag_name in tags_data:
                tag = await CourseService._get_or_create_tag(db, tag_name)
                course.tags.append(tag)
        
        await db.commit()
        await db.refresh(course)
        return course
    
    @staticmethod
    async def enroll_user(db: AsyncSession, user_id: int, course_id: int) -> Enrollment:
        """Enroll user in course"""
        # Check if already enrolled
        existing = await db.execute(
            select(Enrollment).where(
                and_(
                    Enrollment.student_id == user_id,
                    Enrollment.course_id == course_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Already enrolled in this course")
        
        # Check enrollment limit
        course = await CourseService._get_course_by_id(db, course_id)
        if course.enrollment_limit:
            current_count = await db.execute(
                select(func.count(Enrollment.id)).where(
                    and_(
                        Enrollment.course_id == course_id,
                        Enrollment.is_active == True
                    )
                )
            )
            if current_count.scalar() >= course.enrollment_limit:
                raise HTTPException(status_code=400, detail="Course enrollment limit reached")
        
        enrollment = Enrollment(student_id=user_id, course_id=course_id)
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)
        return enrollment
    
    @staticmethod
    async def get_user_enrollments(
        db: AsyncSession, 
        user_id: int,
        status: Optional[str] = None
    ) -> List[Enrollment]:
        """Get user enrollments"""
        query = select(Enrollment).options(
            joinedload(Enrollment.course).joinedload(Course.instructor),
            joinedload(Enrollment.course).joinedload(Course.category)
        ).where(Enrollment.student_id == user_id, Enrollment.is_active == True)
        
        if status:
            query = query.where(Enrollment.status == status)
        
        query = query.order_by(Enrollment.enrolled_at.desc())
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def create_module(db: AsyncSession, module_data: ModuleCreate) -> Module:
        """Create course module"""
        module = Module(**module_data.model_dump())
        db.add(module)
        await db.commit()
        await db.refresh(module)
        return module
    
    @staticmethod
    async def create_lesson(db: AsyncSession, lesson_data: LessonCreate) -> Lesson:
        """Create lesson"""
        lesson = Lesson(**lesson_data.model_dump())
        db.add(lesson)
        await db.commit()
        await db.refresh(lesson)
        return lesson
    
    @staticmethod
    async def get_lesson_by_uuid(db: AsyncSession, uuid: str) -> Lesson:
        """Get lesson by UUID"""
        result = await db.execute(
            select(Lesson)
            .options(
                joinedload(Lesson.module),
                selectinload(Lesson.resources)
            )
            .where(Lesson.uuid == uuid)
        )
        lesson = result.scalar_one_or_none()
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        return lesson
    
    @staticmethod
    async def update_lesson_progress(
        db: AsyncSession,
        user_id: int,
        lesson_id: int,
        progress_data: LessonProgressUpdate,
        completed: bool = False
    ) -> LessonProgress:
        """Update lesson progress"""
        # Get enrollment
        lesson = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
        lesson = lesson.scalar_one()
        
        enrollment = await db.execute(
            select(Enrollment).where(
                and_(
                    Enrollment.student_id == user_id,
                    Enrollment.course_id == lesson.module.course_id,
                    Enrollment.is_active == True
                )
            )
        )
        enrollment = enrollment.scalar_one_or_none()
        if not enrollment:
            raise HTTPException(status_code=404, detail="Enrollment not found")
        
        # Get or create progress
        progress_result = await db.execute(
            select(LessonProgress).where(
                and_(
                    LessonProgress.enrollment_id == enrollment.id,
                    LessonProgress.lesson_id == lesson_id
                )
            )
        )
        progress = progress_result.scalar_one_or_none()
        
        if not progress:
            progress = LessonProgress(
                enrollment_id=enrollment.id,
                lesson_id=lesson_id
            )
            db.add(progress)
        
        # Update progress
        update_dict = progress_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(progress, field, value)
        
        if completed and not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(progress)
        
        # Update enrollment progress
        await CourseService._update_enrollment_progress(db, enrollment.id)
        
        return progress
    
    @staticmethod
    async def create_quiz(db: AsyncSession, quiz_data: QuizCreate) -> Quiz:
        """Create quiz"""
        quiz = Quiz(**quiz_data.model_dump())
        db.add(quiz)
        await db.commit()
        await db.refresh(quiz)
        return quiz
    
    @staticmethod
    async def submit_quiz(
        db: AsyncSession,
        user_id: int,
        quiz_submission: QuizSubmission
    ) -> QuizAttempt:
        """Submit quiz attempt"""
        quiz = await CourseService._get_quiz_by_id(db, quiz_submission.quiz_id)
        
        # Get enrollment
        enrollment = await db.execute(
            select(Enrollment).where(
                and_(
                    Enrollment.student_id == user_id,
                    Enrollment.course_id == quiz.course_id,
                    Enrollment.is_active == True
                )
            )
        )
        enrollment = enrollment.scalar_one_or_none()
        if not enrollment:
            raise HTTPException(status_code=404, detail="Enrollment not found")
        
        # Check attempt limit
        attempt_count = await db.execute(
            select(func.count(QuizAttempt.id)).where(
                and_(
                    QuizAttempt.quiz_id == quiz.id,
                    QuizAttempt.student_id == user_id
                )
            )
        )
        if attempt_count.scalar() >= quiz.max_attempts:
            raise HTTPException(status_code=400, detail="Maximum attempts exceeded")
        
        # Create attempt
        attempt = QuizAttempt(
            quiz_id=quiz.id,
            student_id=user_id,
            enrollment_id=enrollment.id,
            attempt_number=attempt_count.scalar() + 1
        )
        db.add(attempt)
        await db.commit()
        await db.refresh(attempt)
        
        # Process responses and calculate score
        total_points = 0
        earned_points = 0
        
        for response_data in quiz_submission.responses:
            question = await db.execute(
                select(Question)
                .options(selectinload(Question.answers))
                .where(Question.id == response_data.question_id)
            )
            question = question.scalar_one()
            
            response = QuestionResponse(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_answer_id=response_data.selected_answer_id,
                text_response=response_data.text_response
            )
            
            # Auto-grade if possible
            if question.question_type in ["multiple_choice", "true_false"]:
                if response_data.selected_answer_id:
                    answer = next(
                        (a for a in question.answers if a.id == response_data.selected_answer_id),
                        None
                    )
                    if answer and answer.is_correct:
                        response.is_correct = True
                        response.points_earned = question.points
                    else:
                        response.is_correct = False
                        response.points_earned = 0
            
            total_points += question.points
            earned_points += float(response.points_earned or 0)
            
            db.add(response)
        
        # Calculate final score
        score = (earned_points / total_points * 100) if total_points > 0 else 0
        passed = score >= quiz.passing_score
        
        # Update attempt
        attempt.completed_at = datetime.utcnow()
        attempt.score = score
        attempt.passed = passed
        
        await db.commit()
        await db.refresh(attempt)
        return attempt
    
    @staticmethod
    async def create_review(
        db: AsyncSession,
        user_id: int,
        review_data: CourseReviewCreate
    ) -> CourseReview:
        """Create course review"""
        # Check if user completed the course
        enrollment = await db.execute(
            select(Enrollment).where(
                and_(
                    Enrollment.student_id == user_id,
                    Enrollment.course_id == review_data.course_id,
                    Enrollment.status == "completed"
                )
            )
        )
        if not enrollment.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Must complete course before reviewing"
            )
        
        # Check if already reviewed
        existing = await db.execute(
            select(CourseReview).where(
                and_(
                    CourseReview.student_id == user_id,
                    CourseReview.course_id == review_data.course_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Already reviewed this course")
        
        review = CourseReview(
            student_id=user_id,
            **review_data.model_dump()
        )
        db.add(review)
        await db.commit()
        await db.refresh(review)
        return review
    
    @staticmethod
    async def generate_certificate(db: AsyncSession, enrollment_id: int) -> Certificate:
        """Generate certificate for completed course"""
        enrollment = await db.execute(
            select(Enrollment)
            .options(
                joinedload(Enrollment.student),
                joinedload(Enrollment.course)
            )
            .where(Enrollment.id == enrollment_id)
        )
        enrollment = enrollment.scalar_one_or_none()
        if not enrollment:
            raise HTTPException(status_code=404, detail="Enrollment not found")
        
        if enrollment.status != "completed":
            raise HTTPException(status_code=400, detail="Course not completed")
        
        # Check if certificate already exists
        existing = await db.execute(
            select(Certificate).where(Certificate.enrollment_id == enrollment_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Certificate already exists")
        
        # Generate certificate number
        cert_number = f"CERT-{datetime.now().year}-{uuid.uuid4().hex[:8].upper()}"
        
        # Create certificate
        certificate = Certificate(
            certificate_number=cert_number,
            student_id=enrollment.student_id,
            course_id=enrollment.course_id,
            enrollment_id=enrollment_id,
            completion_date=enrollment.completed_at.date(),
            final_score=enrollment.progress_percentage
        )
        
        db.add(certificate)
        await db.commit()
        await db.refresh(certificate)
        
        # Generate QR code
        qr_data = f"VERIFY:{cert_number}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_b64 = base64.b64encode(qr_buffer.getvalue()).decode()
        
        certificate.qr_code = f"data:image/png;base64,{qr_b64}"
        certificate.verification_url = f"/certificates/{certificate.uuid}/verify"
        
        await db.commit()
        return certificate
    
    # Helper methods
    @staticmethod
    async def _get_course_by_id(db: AsyncSession, course_id: int) -> Course:
        """Get course by ID"""
        result = await db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        return course
    
    @staticmethod
    async def _get_quiz_by_id(db: AsyncSession, quiz_id: int) -> Quiz:
        """Get quiz by ID"""
        result = await db.execute(
            select(Quiz)
            .options(selectinload(Quiz.questions).selectinload(Question.answers))
            .where(Quiz.id == quiz_id)
        )
        quiz = result.scalar_one_or_none()
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        return quiz
    
    @staticmethod
    async def _get_or_create_tag(db: AsyncSession, tag_name: str) -> Tag:
        """Get or create tag"""
        slug = tag_name.lower().replace(' ', '-')
        result = await db.execute(select(Tag).where(Tag.slug == slug))
        tag = result.scalar_one_or_none()
        
        if not tag:
            tag = Tag(name=tag_name, slug=slug)
            db.add(tag)
            await db.commit()
            await db.refresh(tag)
        
        return tag
    
    @staticmethod
    async def _update_enrollment_progress(db: AsyncSession, enrollment_id: int):
        """Update enrollment progress percentage"""
        # Get total lessons and completed lessons
        enrollment = await db.execute(
            select(Enrollment)
            .options(joinedload(Enrollment.course))
            .where(Enrollment.id == enrollment_id)
        )
        enrollment = enrollment.scalar_one()
        
        total_lessons = await db.execute(
            select(func.count(Lesson.id))
            .join(Module)
            .where(
                and_(
                    Module.course_id == enrollment.course_id,
                    Lesson.is_published == True,
                    Module.is_published == True
                )
            )
        )
        total_lessons = total_lessons.scalar()
        
        if total_lessons == 0:
            return
        
        completed_lessons = await db.execute(
            select(func.count(LessonProgress.id))
            .join(Lesson).join(Module)
            .where(
                and_(
                    LessonProgress.enrollment_id == enrollment_id,
                    LessonProgress.is_completed == True,
                    Module.course_id == enrollment.course_id,
                    Lesson.is_published == True,
                    Module.is_published == True
                )
            )
        )
        completed_lessons = completed_lessons.scalar()
        
        progress = (completed_lessons / total_lessons) * 100
        
        # Update enrollment
        update_data = {"progress_percentage": progress}
        
        if progress >= 100 and enrollment.status != "completed":
            update_data["status"] = "completed"
            update_data["completed_at"] = datetime.utcnow()
        elif progress > 0 and enrollment.status == "enrolled":
            update_data["status"] = "in_progress"
            update_data["started_at"] = datetime.utcnow()
        
        await db.execute(
            update(Enrollment)
            .where(Enrollment.id == enrollment_id)
            .values(**update_data)
        )
        await db.commit()