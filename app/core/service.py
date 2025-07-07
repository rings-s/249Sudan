# app/core/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database import get_db
from app.deps import get_current_user, get_verified_user, get_moderator_user, get_manager_user
from app.accounts.models import User
from app.core.service import CoreService
from app.core.schemas import (
    Forum, ForumCreate, Discussion, DiscussionCreate, DiscussionUpdate, DiscussionDetail,
    Reply, ReplyCreate, ReplyUpdate, Notification, NotificationUpdate,
    ActivityLog, StudentDashboard, TeacherDashboard, PlatformDashboard,
    Announcement, AnnouncementCreate, AnnouncementUpdate,
    SupportTicket, SupportTicketCreate, SupportTicketUpdate,
    StandardResponse, ActivityLogCreate
)
from app.utils.security import validate_uuid

router = APIRouter()

# =============================================================================
# FORUM ENDPOINTS
# =============================================================================

@router.get("/forums", response_model=List[Forum])
async def get_forums(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all active forums"""
    return await CoreService.get_forums(db)

@router.post("/forums", response_model=Forum)
async def create_forum(
    forum_data: ForumCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_moderator_user)
):
    """Create forum for course (moderators and above)"""
    return await CoreService.create_forum(db, forum_data)

@router.get("/forums/{uuid}", response_model=Forum)
async def get_forum(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get forum details"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    return await CoreService.get_forum_by_uuid(db, uuid)

# =============================================================================
# DISCUSSION ENDPOINTS
# =============================================================================

@router.get("/discussions", response_model=List[Discussion])
async def get_discussions(
    forum_id: Optional[int] = None,
    discussion_type: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get discussions with filtering"""
    return await CoreService.get_discussions(
        db=db,
        forum_id=forum_id,
        discussion_type=discussion_type,
        search=search,
        skip=skip,
        limit=limit
    )

@router.post("/discussions", response_model=Discussion)
async def create_discussion(
    discussion_data: DiscussionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Create new discussion"""
    return await CoreService.create_discussion(db, discussion_data, current_user.id)

@router.get("/discussions/{uuid}", response_model=DiscussionDetail)
async def get_discussion(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get discussion with replies"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    discussion = await CoreService.get_discussion_by_uuid(db, uuid)
    
    # Add computed fields for response
    discussion.author_name = discussion.author.get_full_name()
    discussion.author_avatar = discussion.author.avatar
    discussion.author_role = discussion.author.role
    discussion.replies_count = len(discussion.replies)
    
    # Process replies
    for reply in discussion.replies:
        reply.author_name = reply.author.get_full_name()
        reply.author_avatar = reply.author.avatar
        reply.author_role = reply.author.role
    
    return discussion

@router.put("/discussions/{uuid}", response_model=Discussion)
async def update_discussion(
    uuid: str,
    discussion_data: DiscussionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Update discussion (author only)"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    discussion = await CoreService.get_discussion_by_uuid(db, uuid)
    return await CoreService.update_discussion(db, discussion.id, discussion_data, current_user.id)

@router.post("/discussions/{uuid}/pin", response_model=StandardResponse)
async def pin_discussion(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_moderator_user)
):
    """Pin/unpin discussion (moderators and above)"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    discussion = await CoreService.get_discussion_by_uuid(db, uuid)
    updated_discussion = await CoreService.pin_discussion(db, discussion.id, current_user.id)
    
    action = "pinned" if updated_discussion.is_pinned else "unpinned"
    return StandardResponse(message=f"Discussion {action} successfully")

@router.post("/discussions/{uuid}/resolve", response_model=StandardResponse)
async def resolve_discussion(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Mark discussion as resolved"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    discussion = await CoreService.get_discussion_by_uuid(db, uuid)
    await CoreService.resolve_discussion(db, discussion.id, current_user.id)
    
    return StandardResponse(message="Discussion marked as resolved")

# =============================================================================
# REPLY ENDPOINTS
# =============================================================================

@router.post("/replies", response_model=Reply)
async def create_reply(
    reply_data: ReplyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Create reply to discussion"""
    return await CoreService.create_reply(db, reply_data, current_user.id)

@router.get("/replies/{uuid}", response_model=Reply)
async def get_reply(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get reply details"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    reply = await CoreService.get_reply_by_uuid(db, uuid)
    
    # Add computed fields
    reply.author_name = reply.author.get_full_name()
    reply.author_avatar = reply.author.avatar
    reply.author_role = reply.author.role
    
    return reply

@router.post("/replies/{uuid}/upvote", response_model=StandardResponse)
async def upvote_reply(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Upvote reply"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    from sqlalchemy import update
    from app.core.models import Reply as ReplyModel
    
    reply = await CoreService.get_reply_by_uuid(db, uuid)
    
    # Increment upvotes
    await db.execute(
        update(ReplyModel)
        .where(ReplyModel.id == reply.id)
        .values(upvotes=ReplyModel.upvotes + 1)
    )
    await db.commit()
    
    return StandardResponse(
        message="Reply upvoted",
        data={"upvotes": reply.upvotes + 1}
    )

@router.post("/replies/{uuid}/mark-solution", response_model=StandardResponse)
async def mark_reply_as_solution(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Mark reply as solution"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    reply = await CoreService.get_reply_by_uuid(db, uuid)
    await CoreService.mark_reply_as_solution(db, reply.id, current_user.id)
    
    return StandardResponse(message="Reply marked as solution")

# =============================================================================
# NOTIFICATION ENDPOINTS
# =============================================================================

@router.get("/notifications", response_model=List[Notification])
async def get_notifications(
    unread_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user notifications"""
    notifications = await CoreService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
        skip=skip,
        limit=limit
    )
    
    # Add computed fields
    for notification in notifications:
        if notification.course:
            notification.course_title = notification.course.title
        if notification.lesson:
            notification.lesson_title = notification.lesson.title
    
    return notifications

@router.put("/notifications/{uuid}", response_model=StandardResponse)
async def mark_notification_read(
    uuid: str,
    notification_data: NotificationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark notification as read"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    from sqlalchemy import select
    from app.core.models import Notification as NotificationModel
    
    # Get notification
    result = await db.execute(
        select(NotificationModel).where(NotificationModel.uuid == uuid)
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Check ownership
    if notification.recipient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    success = await CoreService.mark_notification_read(db, notification.id, current_user.id)
    
    if success:
        return StandardResponse(message="Notification marked as read")
    else:
        raise HTTPException(status_code=404, detail="Notification not found")

@router.post("/notifications/mark-all-read", response_model=StandardResponse)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all notifications as read"""
    count = await CoreService.mark_all_notifications_read(db, current_user.id)
    return StandardResponse(
        message=f"{count} notifications marked as read"
    )

@router.get("/notifications/unread-count", response_model=dict)
async def get_unread_notification_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get unread notification count"""
    count = await CoreService.get_unread_count(db, current_user.id)
    return {"unread_count": count}

# =============================================================================
# ACTIVITY LOG ENDPOINTS
# =============================================================================

@router.get("/activities", response_model=List[ActivityLog])
async def get_activities(
    activity_type: Optional[str] = None,
    course_id: Optional[int] = None,
    days: int = Query(30, ge=1, le=365),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user activities"""
    user_id = current_user.id if current_user.role == "student" else None
    
    return await CoreService.get_user_activities(
        db=db,
        user_id=user_id,
        activity_type=activity_type,
        course_id=course_id,
        days=days,
        skip=skip,
        limit=limit
    )

@router.post("/activities", response_model=StandardResponse)
async def track_activity(
    activity_data: ActivityLogCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Track user activity"""
    # Add request metadata
    activity_data.ip_address = request.client.host if request.client else None
    activity_data.user_agent = request.headers.get("user-agent", "")
    
    await CoreService.track_activity(db, activity_data, current_user.id)
    return StandardResponse(message="Activity tracked successfully")

# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/dashboard", response_model=dict)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user dashboard based on role"""
    if current_user.role == "student":
        return await CoreService.get_student_analytics(db, current_user.id)
    elif current_user.role == "teacher":
        return await CoreService.get_teacher_analytics(db, current_user.id)
    elif current_user.role in ["manager", "admin"] or current_user.is_staff:
        return await CoreService.get_platform_analytics(db)
    else:
        raise HTTPException(status_code=403, detail="Access denied")

@router.get("/student-analytics", response_model=StudentDashboard)
async def get_student_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Get detailed student analytics"""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")
    
    return await CoreService.get_student_analytics(db, current_user.id)

@router.get("/teacher-analytics", response_model=TeacherDashboard)
async def get_teacher_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Get detailed teacher analytics"""
    if current_user.role != "teacher" and not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Teacher access only")
    
    return await CoreService.get_teacher_analytics(db, current_user.id)

@router.get("/platform-analytics", response_model=PlatformDashboard)
async def get_platform_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_manager_user)
):
    """Get platform-wide analytics (managers and above)"""
    return await CoreService.get_platform_analytics(db)

# =============================================================================
# ANNOUNCEMENT ENDPOINTS
# =============================================================================

@router.get("/announcements", response_model=List[Announcement])
async def get_announcements(
    course_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get announcements for user"""
    return await CoreService.get_announcements(
        db=db,
        user_role=current_user.role,
        course_id=course_id,
        skip=skip,
        limit=limit
    )

@router.post("/announcements", response_model=Announcement)
async def create_announcement(
    announcement_data: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_manager_user)
):
    """Create announcement (managers and above)"""
    return await CoreService.create_announcement(db, announcement_data, current_user.id)

@router.get("/announcements/{uuid}", response_model=Announcement)
async def get_announcement(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get announcement details"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    from sqlalchemy import select
    from app.core.models import Announcement as AnnouncementModel
    
    result = await db.execute(
        select(AnnouncementModel)
        .options(
            joinedload(AnnouncementModel.author),
            joinedload(AnnouncementModel.course)
        )
        .where(AnnouncementModel.uuid == uuid)
    )
    announcement = result.scalar_one_or_none()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Add computed fields
    announcement.author_name = announcement.author.get_full_name() if announcement.author else None
    announcement.course_title = announcement.course.title if announcement.course else None
    
    return announcement

# =============================================================================
# SUPPORT TICKET ENDPOINTS
# =============================================================================

@router.get("/support-tickets", response_model=List[SupportTicket])
async def get_support_tickets(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get support tickets"""
    return await CoreService.get_support_tickets(
        db=db,
        user_id=current_user.id,
        user_role=current_user.role,
        status=status,
        skip=skip,
        limit=limit
    )

@router.post("/support-tickets", response_model=SupportTicket)
async def create_support_ticket(
    ticket_data: SupportTicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """Create support ticket"""
    return await CoreService.create_support_ticket(db, ticket_data, current_user.id)

@router.get("/support-tickets/{uuid}", response_model=SupportTicket)
async def get_support_ticket(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get support ticket details"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    from sqlalchemy import select, and_
    from app.core.models import SupportTicket as SupportTicketModel
    
    query = select(SupportTicketModel).options(
        joinedload(SupportTicketModel.user),
        joinedload(SupportTicketModel.assigned_to),
        joinedload(SupportTicketModel.course)
    ).where(SupportTicketModel.uuid == uuid)
    
    # Students can only see their own tickets
    if current_user.role == "student":
        query = query.where(SupportTicketModel.user_id == current_user.id)
    
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found")
    
    # Add computed fields
    ticket.user_name = ticket.user.get_full_name()
    ticket.assigned_to_name = ticket.assigned_to.get_full_name() if ticket.assigned_to else None
    ticket.course_title = ticket.course.title if ticket.course else None
    
    return ticket

@router.put("/support-tickets/{uuid}", response_model=StandardResponse)
async def update_support_ticket(
    uuid: str,
    ticket_data: SupportTicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_moderator_user)
):
    """Update support ticket (moderators and above)"""
    if not validate_uuid(uuid):
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    from sqlalchemy import update
    from app.core.models import SupportTicket as SupportTicketModel
    
    # Get ticket
    result = await db.execute(
        select(SupportTicketModel).where(SupportTicketModel.uuid == uuid)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found")
    
    # Update ticket
    update_data = ticket_data.model_dump(exclude_unset=True)
    if ticket_data.status == "resolved" and "resolved_at" not in update_data:
        update_data["resolved_at"] = datetime.utcnow()
    
    if update_data:
        await db.execute(
            update(SupportTicketModel)
            .where(SupportTicketModel.id == ticket.id)
            .values(**update_data)
        )
        await db.commit()
    
    return StandardResponse(message="Support ticket updated successfully")