# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import engine, create_tables
from app.accounts.router import router as accounts_router
from app.courses.router import router as courses_router
from app.core.router import router as core_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_tables()
    logger.info("Application startup complete")
    yield
    # Shutdown
    logger.info("Application shutdown")

# Create FastAPI application
app = FastAPI(
    title="E-Learning Platform API",
    description="A comprehensive e-learning platform with courses, quizzes, and analytics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Add trusted host middleware
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(accounts_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(courses_router, prefix="/api", tags=["Courses"])
app.include_router(core_router, prefix="/api/core", tags=["Core"])

@app.get("/")
async def root():
    return {
        "message": "E-Learning Platform API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": settings.ENVIRONMENT}

# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "error": True,
        "message": exc.detail,
        "status_code": exc.status_code
    }