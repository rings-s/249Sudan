# app/accounts/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from datetime import datetime, timedelta
import secrets
import string

from app.accounts.models import User, UserProfile
from app.accounts.schemas import UserCreate, UserUpdate, UserProfileUpdate
from app.utils.security import get_password_hash, verify_password, generate_verification_code
from app.utils.email import send_verification_email, send_password_reset_email, send_welcome_email

class UserService:
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> User:
        """Get user by ID"""
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    
    @staticmethod
    async def get_user_by_uuid(db: AsyncSession, uuid: str) -> User:
        """Get user by UUID"""
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.uuid == uuid)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User:
        """Get user by email"""
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
        """Create new user"""
        # Check if user already exists
        existing_user = await UserService.get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="User with this email already exists"
            )
        
        # Validate password confirmation
        if user_data.password != user_data.confirm_password:
            raise HTTPException(
                status_code=400,
                detail="Passwords do not match"
            )
        
        # Create user
        hashed_password = get_password_hash(user_data.password)
        
        user = User(
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone_number=user_data.phone_number,
            date_of_birth=user_data.date_of_birth,
            role=user_data.role,
            hashed_password=hashed_password,
            verification_code=generate_verification_code(),
            verification_code_created=datetime.utcnow()
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Create user profile
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        await db.commit()
        
        # Send verification email
        await send_verification_email(
            email=user.email,
            verification_code=user.verification_code,
            user_name=user.get_full_name()
        )
        
        return user
    
    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
        """Authenticate user with email and password"""
        user = await UserService.get_user_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=400,
                detail="Account is disabled"
            )
        
        # Update last login
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(last_login=datetime.utcnow())
        )
        await db.commit()
        
        return user
    
    @staticmethod
    async def verify_email(db: AsyncSession, email: str, verification_code: str) -> User:
        """Verify user email with code"""
        user = await UserService.get_user_by_email(db, email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user.is_verified:
            raise HTTPException(status_code=400, detail="Email already verified")
        
        if (not user.verification_code or 
            user.verification_code != verification_code or
            not user.verification_code_created):
            raise HTTPException(status_code=400, detail="Invalid verification code")
        
        # Check if code has expired (24 hours)
        expiry_time = user.verification_code_created + timedelta(hours=24)
        if datetime.utcnow() > expiry_time:
            raise HTTPException(status_code=400, detail="Verification code has expired")
        
        # Verify user
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                is_verified=True,
                verification_code=None,
                verification_code_created=None
            )
        )
        await db.commit()
        
        # Send welcome email
        await send_welcome_email(user.email, user.get_full_name())
        
        await db.refresh(user)
        return user
    
    @staticmethod
    async def resend_verification(db: AsyncSession, email: str) -> bool:
        """Resend verification email"""
        user = await UserService.get_user_by_email(db, email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user.is_verified:
            raise HTTPException(status_code=400, detail="Email already verified")
        
        # Generate new verification code
        new_code = generate_verification_code()
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                verification_code=new_code,
                verification_code_created=datetime.utcnow()
            )
        )
        await db.commit()
        
        # Send verification email
        await send_verification_email(
            email=user.email,
            verification_code=new_code,
            user_name=user.get_full_name()
        )
        
        return True
    
    @staticmethod
    async def request_password_reset(db: AsyncSession, email: str) -> bool:
        """Request password reset"""
        user = await UserService.get_user_by_email(db, email)
        if not user:
            # Don't reveal if user exists
            return True
        
        # Generate reset code
        reset_code = generate_verification_code()
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                reset_code=reset_code,
                reset_code_created=datetime.utcnow()
            )
        )
        await db.commit()
        
        # Send reset email
        await send_password_reset_email(
            email=user.email,
            reset_code=reset_code,
            user_name=user.get_full_name()
        )
        
        return True
    
    @staticmethod
    async def reset_password(
        db: AsyncSession, 
        email: str, 
        reset_code: str, 
        new_password: str
    ) -> bool:
        """Reset password with code"""
        user = await UserService.get_user_by_email(db, email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if (not user.reset_code or 
            user.reset_code != reset_code or
            not user.reset_code_created):
            raise HTTPException(status_code=400, detail="Invalid reset code")
        
        # Check if code has expired (1 hour)
        expiry_time = user.reset_code_created + timedelta(hours=1)
        if datetime.utcnow() > expiry_time:
            raise HTTPException(status_code=400, detail="Reset code has expired")
        
        # Reset password
        hashed_password = get_password_hash(new_password)
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                hashed_password=hashed_password,
                reset_code=None,
                reset_code_created=None
            )
        )
        await db.commit()
        
        return True
    
    @staticmethod
    async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdate) -> User:
        """Update user information"""
        # Get user
        user = await UserService.get_user_by_id(db, user_id)
        
        # Update user fields
        update_data = user_data.model_dump(exclude_unset=True)
        if update_data:
            await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(**update_data)
            )
            await db.commit()
            await db.refresh(user)
        
        return user
    
    @staticmethod
    async def update_user_profile(
        db: AsyncSession, 
        user_id: int, 
        profile_data: UserProfileUpdate
    ) -> UserProfile:
        """Update user profile"""
        # Get or create profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.add(profile)
        
        # Update profile fields
        update_data = profile_data.model_dump(exclude_unset=True)
        if update_data:
            for field, value in update_data.items():
                setattr(profile, field, value)
        
        await db.commit()
        await db.refresh(profile)
        
        return profile
    
    @staticmethod
    async def change_password(
        db: AsyncSession,
        user_id: int,
        current_password: str,
        new_password: str
    ) -> bool:
        """Change user password"""
        user = await UserService.get_user_by_id(db, user_id)
        
        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect"
            )
        
        # Update password
        hashed_password = get_password_hash(new_password)
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(hashed_password=hashed_password)
        )
        await db.commit()
        
        return True
    
    @staticmethod
    async def update_avatar(db: AsyncSession, user_id: int, avatar_path: str) -> User:
        """Update user avatar"""
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(avatar=avatar_path)
        )
        await db.commit()
        
        return await UserService.get_user_by_id(db, user_id)