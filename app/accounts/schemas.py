# app/accounts/schemas.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    MODERATOR = "moderator"
    MANAGER = "manager"

# User Profile Schemas
class UserProfileBase(BaseModel):
    bio: Optional[str] = None
    education_level: Optional[str] = None
    institution: Optional[str] = None
    field_of_study: Optional[str] = None
    teaching_experience: Optional[int] = None
    expertise_areas: Optional[str] = None
    certifications: Optional[str] = None
    learning_goals: Optional[str] = None
    preferred_language: str = "en"
    time_zone: str = "UTC"
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    website_url: Optional[str] = None

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileUpdate(UserProfileBase):
    pass

class UserProfile(UserProfileBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    courses_completed: int = 0
    total_study_hours: int = 0
    points_earned: int = 0
    created_at: datetime
    updated_at: datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    role: UserRole = UserRole.STUDENT

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    confirm_password: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None

class UserInDB(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
    is_verified: bool = False
    avatar: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

class User(UserInDB):
    profile: Optional[UserProfile] = None

class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    avatar: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

# Authentication Schemas
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefresh(BaseModel):
    refresh_token: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    email: EmailStr
    reset_code: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str

class EmailVerification(BaseModel):
    email: EmailStr
    verification_code: str

class ResendVerification(BaseModel):
    email: EmailStr

# Response Schemas
class StandardResponse(BaseModel):
    status: str = "success"
    message: str
    data: Optional[dict] = None

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    error_code: Optional[str] = None