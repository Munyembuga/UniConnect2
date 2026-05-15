# =============================================================================
# User Repository - Data Access Layer
# Handles all database operations for users
# =============================================================================

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from loguru import logger

from app.models.user import User, UserRole
from app.core.security import hash_password
from app.schemas.auth import UserRegisterRequest


class UserRepository:
    """Repository for user database operations."""
    
    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def create_user(self, user_data: UserRegisterRequest, role: UserRole = UserRole.STUDENT) -> User:
        """
        Create a new user in the database.
        
        Args:
            user_data: User registration data
            role: User role (default: STUDENT)
            
        Returns:
            Created User object
            
        Raises:
            IntegrityError: If email already exists
        """
        try:
            hashed_password = hash_password(user_data.password)
            
            db_user = User(
                email=user_data.email,
                full_name=user_data.full_name,
                hashed_password=hashed_password,
                role=role,
                is_active=True,
            )
            
            self.db.add(db_user)
            await self.db.flush()
            await self.db.commit()
            await self.db.refresh(db_user)
            
            logger.info(f"User created: {db_user.email}")
            return db_user
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"User creation failed - email may already exist: {user_data.email}")
            raise ValueError(f"Email {user_data.email} already exists")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating user: {e}")
            raise

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve user by email.
        
        Args:
            email: User email address
            
        Returns:
            User object if found, None otherwise
        """
        try:
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            return user
        except Exception as e:
            logger.error(f"Error retrieving user by email {email}: {e}")
            return None

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Retrieve user by ID.
        
        Args:
            user_id: User UUID
            
        Returns:
            User object if found, None otherwise
        """
        try:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            return user
        except Exception as e:
            logger.error(f"Error retrieving user by id {user_id}: {e}")
            return None

    async def update_user(self, user_id: UUID, **kwargs) -> Optional[User]:
        """
        Update user fields.
        
        Args:
            user_id: User UUID
            **kwargs: Fields to update
            
        Returns:
            Updated User object if found, None otherwise
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"User not found for update: {user_id}")
                return None
            
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info(f"User updated: {user.email}")
            return user
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating user {user_id}: {e}")
            raise

    async def delete_user(self, user_id: UUID) -> bool:
        """
        Delete user by ID.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if user was deleted, False if not found
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"User not found for deletion: {user_id}")
                return False
            
            await self.db.delete(user)
            await self.db.commit()
            
            logger.info(f"User deleted: {user.email}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")
            raise

    async def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """
        List all users with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of User objects
        """
        try:
            result = await self.db.execute(
                select(User).offset(skip).limit(limit)
            )
            users = result.scalars().all()
            return users
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
