# =============================================================================
# User Model - SQLAlchemy ORM
# Defines the users table with authentication fields
# =============================================================================

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum


class UserRole(str, enum.Enum):
    """User role enumeration for role-based access control."""
    ADMIN = "admin"
    STUDENT = "student"


class User(Base):
    """User model for authentication and role management."""
    
    __tablename__ = "users"

    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # User Information
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Authentication & Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    role = Column(
        Enum(
            UserRole,
            name="userrole",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=UserRole.STUDENT,
        nullable=False,
        index=True,
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Last login
    last_login = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN

    def is_student(self) -> bool:
        """Check if user is student."""
        return self.role == UserRole.STUDENT
