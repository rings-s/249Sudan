# app/core/schemas.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class DiscussionType(str, Enum):
    QUESTION = "question"
    DISCUSSION = "discussion"
    ANNOUNCEMENT = "announcement"

class NotificationType(str, Enum):
    ENROLLMENT = "enrollment"
    COURSE_UPDATE = "course_update"
    LESSON_AVAILABLE = "lesson_available"
    ASSIGNMENT_DUE = "assignment_due"
    QUIZ_RESULT = "quiz_result"
    CERTIFICATE_READY = "certificate_ready"
    FORUM_REPLY = "forum_reply"
    ANNOUNCEMENT = "announcement"
    SYSTEM = "system"

class ActivityType(str, Enum):
    LOGIN = "login"
    COURSE_VIEW = "course_view"
    LESSON_START = "lesson_start"
    LESSON_COMPLETE = "lesson_complete"
    QUIZ_START = "quiz_start"
    QUIZ_SUBMIT = "quiz_submit"
    RESOURCE_DOWNLOAD = "resource_download"
    FORUM_POST = "forum_post"
    FORUM_REPLY = "forum_reply"
    ASSIGNMENT_SUBMIT = "assignment_submit"

class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

# Forum Schemas
class ForumBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True
    is_moderated: bool = False
    rules: Optional[str] = None

class ForumCreate(ForumBase):
    course_id: int

class Forum(ForumBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    course_id: int
    created_at: datetime
    updated_at: datetime
    discussions_count: int = 0

# Discussion Schemas
class DiscussionBase(BaseModel):
    title: str
    content: str
    discussion_type: DiscussionType = DiscussionType.DISCUSSION

class DiscussionCreate(DiscussionBase):
    forum_id: int

class DiscussionUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    discussion_type: Optional[DiscussionType] = None

class Discussion(DiscussionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    forum_id: int
    author_id: int
    is_pinned: bool = False
    is_locked: bool = False
    is_resolved: bool = False
    views_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    # Additional fields
    author_name: Optional[str] = None
    author_avatar: Optional[str] = None
    author_role: Optional[str] = None
    replies_count: int = 0
    latest_reply: Optional[dict] = None

class DiscussionDetail(Discussion):
    replies: List['Reply'] = []

# Reply Schemas
class ReplyBase(BaseModel):
    content: str

class ReplyCreate(ReplyBase):
    discussion_id: int
    parent_id: Optional[int] = None

class ReplyUpdate(BaseModel):
    content: Optional[str] = None

class Reply(ReplyBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    discussion_id: int
    author_id: int
    parent_id: Optional[int] = None
    is_solution: bool = False
    is_instructor_reply: bool = False
    upvotes: int = 0
    created_at: datetime
    updated_at: datetime
    edited_at: Optional[datetime] = None
    
    # Additional fields
    author_name: Optional[str] = None
    author_avatar: Optional[str] = None
    author_role: Optional[str] = None
    children: List['Reply'] = []

# Notification Schemas
class NotificationBase(BaseModel):
    notification_type: NotificationType
    title: str
    message: str
    action_url: Optional[str] = None

class NotificationCreate(NotificationBase):
    recipient_id: int
    course_id: Optional[int] = None
    lesson_id: Optional[int] = None
    discussion_id: Optional[int] = None
    expires_at: Optional[datetime] = None

class NotificationUpdate(BaseModel):
    is_read: bool

class Notification(NotificationBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    recipient_id: int
    course_id: Optional[int] = None
    lesson_id: Optional[int] = None
    discussion_id: Optional[int] = None
    is_read: bool = False
    read_at: Optional[datetime] = None
    email_sent: bool = False
    email_sent_at: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    # Additional fields
    course_title: Optional[str] = None
    lesson_title: Optional[str] = None

# Activity Log Schemas
class ActivityLogCreate(BaseModel):
    activity_type: ActivityType
    course_id: Optional[int] = None
    lesson_id: Optional[int] = None
    quiz_id: Optional[int] = None
    metadata: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class ActivityLog(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    user_id: int
    activity_type: str
    course_id: Optional[int] = None
    lesson_id: Optional[int] = None
    quiz_id: Optional[int] = None
    metadata: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    
    # Additional fields
    user_name: Optional[str] = None
    course_title: Optional[str] = None
    lesson_title: Optional[str] = None
    quiz_title: Optional[str] = None

# Analytics Schemas
class LearningAnalytics(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    user_id: int
    course_id: int
    enrollment_id: int
    total_time_spent_seconds: int = 0
    last_activity: datetime
    lessons_completed: int = 0
    quizzes_attempted: int = 0
    quizzes_passed: int = 0
    assignments_submitted: int = 0
    average_quiz_score: int = 0
    highest_quiz_score: int = 0
    forum_posts: int = 0
    forum_replies: int = 0
    resources_accessed: int = 0
    learning_path_data: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

# Dashboard Schemas
class StudentDashboard(BaseModel):
    summary: Dict[str, Any]
    performance: Dict[str, Any]
    study_time: Dict[str, Any]
    courses: List[Dict[str, Any]]
    charts: Dict[str, Any]
    subject_performance: List[Dict[str, Any]]

class TeacherDashboard(BaseModel):
    summary: Dict[str, Any]
    course_performance: List[Dict[str, Any]]
    student_activity: Dict[str, Any]
    charts: Dict[str, Any]

class PlatformDashboard(BaseModel):
    platform_health: Dict[str, Any]
    growth_metrics: List[Dict[str, Any]]
    category_insights: List[Dict[str, Any]]
    user_distribution: List[Dict[str, Any]]
    charts: Dict[str, Any]

# Announcement Schemas
class AnnouncementBase(BaseModel):
    title: str
    content: str
    announcement_type: str = "general"
    target_roles: List[str] = []
    is_pinned: bool = False
    show_from: Optional[datetime] = None
    show_until: Optional[datetime] = None

class AnnouncementCreate(AnnouncementBase):
    course_id: Optional[int] = None

class AnnouncementUpdate(AnnouncementBase):
    title: Optional[str] = None
    content: Optional[str] = None

class Announcement(AnnouncementBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    author_id: Optional[int] = None
    course_id: Optional[int] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    # Additional fields
    author_name: Optional[str] = None
    course_title: Optional[str] = None

# Support Ticket Schemas
class SupportTicketBase(BaseModel):
    subject: str
    description: str
    priority: TicketPriority = TicketPriority.MEDIUM

class SupportTicketCreate(SupportTicketBase):
    course_id: Optional[int] = None

class SupportTicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assigned_to_id: Optional[int] = None

class SupportTicket(SupportTicketBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    ticket_number: str
    user_id: int
    course_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    status: TicketStatus = TicketStatus.OPEN
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    
    # Additional fields
    user_name: Optional[str] = None
    assigned_to_name: Optional[str] = None
    course_title: Optional[str] = None

# Media Content Schemas
class MediaContentBase(BaseModel):
    title: str
    description: Optional[str] = None
    content_type: str

class MediaContentCreate(MediaContentBase):
    course_id: Optional[int] = None
    lesson_id: Optional[int] = None

class MediaContent(MediaContentBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uuid: str
    file: str
    file_size: int
    mime_type: Optional[str] = None
    duration_seconds: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    course_id: Optional[int] = None
    lesson_id: Optional[int] = None
    uploaded_by_id: Optional[int] = None
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    # Additional fields
    uploaded_by_name: Optional[str] = None
    file_size_mb: Optional[float] = None

# Response Schemas
class StandardResponse(BaseModel):
    status: str = "success"
    message: str
    data: Optional[Dict[str, Any]] = None

# Update forward references
Reply.model_rebuild()
DiscussionDetail.model_rebuild()