# app/utils/file_upload.py
import aiofiles
import os
from fastapi import UploadFile, HTTPException
from PIL import Image
import uuid
from typing import Optional, List
import magic

from app.config import settings

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv', 'webm'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'ppt', 'pptx'}

async def save_upload_file(
    upload_file: UploadFile,
    destination_dir: str,
    allowed_extensions: Optional[List[str]] = None,
    max_size: int = settings.MAX_UPLOAD_SIZE,
    resize_image: bool = False,
    image_size: tuple = (800, 600)
) -> str:
    """Save uploaded file with validation"""
    
    # Validate file size
    contents = await upload_file.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {max_size // (1024*1024)}MB"
        )
    
    # Validate file extension
    file_extension = upload_file.filename.split('.')[-1].lower()
    if allowed_extensions and file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(destination_dir, unique_filename)
    
    # Ensure directory exists
    os.makedirs(destination_dir, exist_ok=True)
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(contents)
    
    # Resize image if needed
    if resize_image and file_extension in ALLOWED_IMAGE_EXTENSIONS:
        try:
            with Image.open(file_path) as img:
                img.thumbnail(image_size, Image.Resampling.LANCZOS)
                img.save(file_path, optimize=True, quality=85)
        except Exception as e:
            # If image processing fails, keep original
            pass
    
    return f"/static/uploads/{os.path.basename(destination_dir)}/{unique_filename}"

async def save_avatar(upload_file: UploadFile) -> str:
    """Save user avatar with resizing"""
    return await save_upload_file(
        upload_file=upload_file,
        destination_dir=f"{settings.UPLOAD_DIR}/avatars",
        allowed_extensions=list(ALLOWED_IMAGE_EXTENSIONS),
        max_size=10 * 1024 * 1024,  # 10MB
        resize_image=True,
        image_size=(400, 400)
    )

async def save_course_content(upload_file: UploadFile) -> str:
    """Save course content file"""
    allowed_extensions = list(ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS)
    return await save_upload_file(
        upload_file=upload_file,
        destination_dir=f"{settings.UPLOAD_DIR}/courses",
        allowed_extensions=allowed_extensions,
        max_size=settings.MAX_UPLOAD_SIZE
    )

def validate_file_type(file_path: str, expected_types: List[str]) -> bool:
    """Validate file type using python-magic"""
    try:
        file_mime = magic.from_file(file_path, mime=True)
        return any(expected_type in file_mime for expected_type in expected_types)
    except:
        return False