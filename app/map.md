app/
├── main.py                    # FastAPI application entry point
├── config.py                  # Configuration settings
├── database.py                # SQLAlchemy database setup
├── deps.py                    # Dependency injection
├── accounts/                  # User management module
│   ├── models.py             # User, UserProfile SQLAlchemy models
│   ├── schemas.py            # Pydantic request/response models
│   ├── router.py             # Authentication & user API routes
│   ├── service.py            # Business logic layer
│   └── utils.py              # Email verification, password utils
├── courses/                   # Course management module
│   ├── models.py             # Course, Lesson, Quiz models
│   ├── schemas.py            # Course-related Pydantic schemas
│   ├── router.py             # Course management API routes
│   └── service.py            # Course business logic
├── core/                      # Core functionality module
│   ├── models.py             # Forum, Analytics, Notification models
│   ├── schemas.py            # Core functionality schemas
│   ├── router.py             # Forum, analytics API routes
│   └── service.py            # Core business logic
└── utils/                     # Shared utilities
    ├── auth.py               # JWT utilities and dependencies
    ├── email.py              # Email sending functionality
    ├── security.py           # Password hashing, verification
    └── file_upload.py        # File upload handling