# app/core/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid as uuid_lib

from app.database import Base

class Forum(Base):
    __tablename__ = "forums"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), unique=True)
    
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_moderated = Column(Boolean, default=False)
    rules = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    course = relationship("Course")
    discussions = relationship("Discussion", back_populates="forum", cascade="all, delete-orphan")

class Discussion(Base):
    __tablename__ = "discussions"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    forum_id = Column(Integer, ForeignKey("forums.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    discussion_type = Column(String, default="discussion")  # question, discussion, announcement
    
    is_pinned = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    views_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    forum = relationship("Forum", back_populates="discussions")
    author = relationship("User", back_populates="discussions")
    replies = relationship("Reply", back_populates="discussion", cascade="all, delete-orphan")

class Reply(Base):
    __tablename__ = "replies"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    discussion_id = Column(Integer, ForeignKey("discussions.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("replies.id"), nullable=True)
    
    content = Column(Text, nullable=False)
    is_solution = Column(Boolean, default=False)
    is_instructor_reply = Column(Boolean, default=False)
    upvotes = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    edited_at = Column(DateTime, nullable=True)
    
    # Relationships
    discussion = relationship("Discussion", back_populates="replies")
    author = relationship("User", back_populates="replies")
    parent = relationship("Reply", remote_side=[id])
    children = relationship("Reply")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    notification_type = Column(String, nullable=False)  # enrollment, course_update, etc.
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    # Related objects
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    discussion_id = Column(Integer, ForeignKey("discussions.id"), nullable=True)
    
    action_url = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    recipient = relationship("User", back_populates="notifications")
    course = relationship("Course")
    lesson = relationship("Lesson")
    discussion = relationship("Discussion")

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    activity_type = Column(String, nullable=False)  # course_view, lesson_start, etc.
    
    # Related objects
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=True)
    
    metadata = Column(JSON, default=dict)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="activity_logs")
    course = relationship("Course")
    lesson = relationship("Lesson")
    quiz = relationship("Quiz")

class LearningAnalytics(Base):
    __tablename__ = "learning_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    
    # Time tracking
    total_time_spent_seconds = Column(Integer, default=0)
    last_activity = Column(DateTime, server_default=func.now())
    
    # Progress metrics
    lessons_completed = Column(Integer, default=0)
    quizzes_attempted = Column(Integer, default=0)
    quizzes_passed = Column(Integer, default=0)
    assignments_submitted = Column(Integer, default=0)
    
    # Performance metrics
    average_quiz_score = Column(Integer, default=0)
    highest_quiz_score = Column(Integer, default=0)
    
    # Engagement metrics
    forum_posts = Column(Integer, default=0)
    forum_replies = Column(Integer, default=0)
    resources_accessed = Column(Integer, default=0)
    
    learning_path_data = Column(JSON, default=dict)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    course = relationship("Course")
    enrollment = relationship("Enrollment")

class Announcement(Base):
    __tablename__ = "announcements"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    announcement_type = Column(String, default="general")  # general, course, system, maintenance
    
    # Target audience
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    target_roles = Column(JSON, default=list)  # ['student', 'teacher', etc.]
    
    # Display settings
    is_active = Column(Boolean, default=True)
    is_pinned = Column(Boolean, default=False)
    show_from = Column(DateTime, nullable=True)
    show_until = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    author = relationship("User")
    course = relationship("Course")

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    ticket_number = Column(String, unique=True, nullable=False)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    
    priority = Column(String, default="medium")  # low, medium, high, urgent
    status = Column(String, default="open")  # open, in_progress, resolved, closed
    
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    course = relationship("Course")

class MediaContent(Base):
    __tablename__ = "media_contents"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    content_type = Column(String, nullable=False)  # video, audio, image, document, etc.
    
    file = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    mime_type = Column(String, nullable=True)
    
    # Video/Audio specific
    duration_seconds = Column(Integer, nullable=True)
    
    # Image specific
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    # Relationships
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    usage_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    course = relationship("Course")
    lesson = relationship("Lesson")
    uploaded_by = relationship("User")