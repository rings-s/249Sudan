# app/accounts/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, date
import uuid as uuid_lib

from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    avatar = Column(String, nullable=True)
    
    # Authentication
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_staff = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    
    # Verification
    verification_code = Column(String, nullable=True)
    verification_code_created = Column(DateTime, nullable=True)
    reset_code = Column(String, nullable=True)
    reset_code_created = Column(DateTime, nullable=True)
    
    # Role
    role = Column(String, default="student")  # student, teacher, moderator, manager
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="student")
    teaching_courses = relationship("Course", back_populates="instructor")
    quiz_attempts = relationship("QuizAttempt", back_populates="student")
    certificates = relationship("Certificate", back_populates="student")
    notifications = relationship("Notification", back_populates="recipient")
    activity_logs = relationship("ActivityLog", back_populates="user")
    discussions = relationship("Discussion", back_populates="author")
    replies = relationship("Reply", back_populates="author")
    course_reviews = relationship("CourseReview", back_populates="student")
    
    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    
    def has_role(self, role_name: str) -> bool:
        return self.role == role_name or self.is_superuser

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Personal Information
    bio = Column(Text, nullable=True)
    
    # Educational Background
    education_level = Column(String, nullable=True)
    institution = Column(String, nullable=True)
    field_of_study = Column(String, nullable=True)
    
    # Teacher specific
    teaching_experience = Column(Integer, nullable=True)
    expertise_areas = Column(Text, nullable=True)
    certifications = Column(Text, nullable=True)
    
    # Student preferences
    learning_goals = Column(Text, nullable=True)
    preferred_language = Column(String, default="en")
    time_zone = Column(String, default="UTC")
    
    # Address
    address = Column(Text, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    country = Column(String, nullable=True)
    
    # Statistics
    courses_completed = Column(Integer, default=0)
    total_study_hours = Column(Integer, default=0)
    points_earned = Column(Integer, default=0)
    
    # Social
    linkedin_url = Column(String, nullable=True)
    github_url = Column(String, nullable=True)
    website_url = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="profile")