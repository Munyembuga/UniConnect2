# =============================================================================
# Authentication Schemas - Pydantic Validation Models
# Request/response schemas for auth endpoints
# =============================================================================

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import uuid
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    STUDENT = "student"


class UserRegisterRequest(BaseModel):
    """User registration request schema."""
    
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name")
    password: str = Field(..., min_length=8, max_length=255, description="Password (min 8 chars)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "student@example.com",
                "full_name": "John Doe",
                "password": "SecurePass123!",
            }
        }


class UserLoginRequest(BaseModel):
    """User login request schema."""
    
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "student@example.com",
                "password": "SecurePass123!",
            }
        }


class TokenResponse(BaseModel):
    """Authentication token response."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
                "expires_in": 1800,
            }
        }


class UserResponse(BaseModel):
    """User profile response schema."""
    
    id: uuid.UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="Full name")
    role: UserRole = Field(..., description="User role")
    is_active: bool = Field(..., description="Is user active")
    is_verified: bool = Field(..., description="Is email verified")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "student@example.com",
                "full_name": "John Doe",
                "role": "student",
                "is_active": True,
                "is_verified": False,
                "created_at": "2026-05-14T10:30:00+00:00",
                "last_login": None,
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    
    refresh_token: str = Field(..., description="Refresh token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
            }
        }


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=255, description="New password (min 8 chars)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "old_password": "OldPass123!",
                "new_password": "NewPass456!",
            }
        }
