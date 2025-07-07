# app/accounts/router.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.deps import get_current_user, get_verified_user
from app.accounts.service import UserService
from app.accounts.schemas import (
    UserCreate, User, UserLogin, Token, UserUpdate, UserBrief,
    EmailVerification, ResendVerification, PasswordChange,
    PasswordResetRequest, PasswordResetConfirm, StandardResponse,
    UserProfileUpdate, TokenRefresh
)
from app.utils.security import create_access_token, create_refresh_token, verify_token
from app.utils.file_upload import save_avatar

router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=StandardResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    await UserService.create_user(db, user_data)
    return StandardResponse(
        message="Registration successful. Please check your email for verification.",
    )

@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login user and return JWT tokens"""
    user = await UserService.authenticate_user(db, user_data.email, user_data.password)
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id), "email": user.email})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token"""
    payload = verify_token(token_data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    user = await UserService.get_user_by_id(db, int(user_id))
    
    # Create new tokens
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id), "email": user.email})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/verify-email", response_model=StandardResponse)
async def verify_email(
    verification_data: EmailVerification,
    db: AsyncSession = Depends(get_db)
):
    """Verify user email with code"""
    await UserService.verify_email(
        db, 
        verification_data.email, 
        verification_data.verification_code
    )
    return StandardResponse(message="Email verified successfully")

@router.post("/resend-verification", response_model=StandardResponse)
async def resend_verification(
    resend_data: ResendVerification,
    db: AsyncSession = Depends(get_db)
):
    """Resend verification email"""
    await UserService.resend_verification(db, resend_data.email)
    return StandardResponse(message="Verification email sent")

@router.post("/password-reset", response_model=StandardResponse)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset"""
    await UserService.request_password_reset(db, reset_data.email)
    return StandardResponse(
        message="If an account exists with this email, password reset instructions have been sent"
    )

@router.post("/password-reset-confirm", response_model=StandardResponse)
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """Confirm password reset with code"""
    if reset_data.new_password != reset_data.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )
    
    await UserService.reset_password(
        db,
        reset_data.email,
        reset_data.reset_code,
        reset_data.new_password
    )
    return StandardResponse(message="Password reset successfully")

@router.post("/change-password", response_model=StandardResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="New passwords do not match"
        )
    
    await UserService.change_password(
        db,
        current_user.id,
        password_data.current_password,
        password_data.new_password
    )
    return StandardResponse(message="Password changed successfully")

@router.get("/users/me", response_model=User)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user profile"""
    return await UserService.get_user_by_id(db, current_user.id)

@router.put("/users/me", response_model=User)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user information"""
    return await UserService.update_user(db, current_user.id, user_data)

@router.put("/users/me/profile", response_model=StandardResponse)
async def update_current_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile"""
    await UserService.update_user_profile(db, current_user.id, profile_data)
    return StandardResponse(message="Profile updated successfully")

@router.post("/users/me/avatar", response_model=StandardResponse)
async def upload_avatar(
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload user avatar"""
    avatar_path = await save_avatar(avatar)
    await UserService.update_avatar(db, current_user.id, avatar_path)
    return StandardResponse(
        message="Avatar uploaded successfully",
        data={"avatar_url": avatar_path}
    )

@router.get("/users/{uuid}", response_model=User)
async def get_user_by_uuid(
    uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user by UUID"""
    return await UserService.get_user_by_uuid(db, uuid)

@router.get("/users", response_model=List[UserBrief])
async def list_users(
    skip: int = 0,
    limit: int = 20,
    search: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List users with search and pagination"""
    from sqlalchemy import select, or_
    
    query = select(User).where(User.is_active == True, User.is_verified == True)
    
    if search:
        query = query.where(
            or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [UserBrief.model_validate(user) for user in users]