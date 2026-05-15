# =============================================================================
# User Service - Business Logic Layer
# Handles authentication and user management logic
# =============================================================================

from typing import Optional, Tuple
from uuid import UUID
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.schemas.auth import UserRegisterRequest, UserResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)


class UserService:
    """Service for user authentication and management."""
    
    def __init__(self, db: AsyncSession):
        """Initialize with database session and repository."""
        self.db = db
        self.repo = UserRepository(db)

    async def register_user(
        self,
        user_data: UserRegisterRequest,
        role: UserRole = UserRole.STUDENT,
    ) -> Tuple[User, str, str]:
        """
        Register a new user and return tokens.
        
        Args:
            user_data: User registration data
            role: User role (default: STUDENT)
            
        Returns:
            Tuple of (User, access_token, refresh_token)
            
        Raises:
            ValueError: If email already exists
        """
        try:
            # Create user
            user = await self.repo.create_user(user_data, role)
            
            # Generate tokens
            access_token = create_access_token({"sub": str(user.id)})
            refresh_token = create_refresh_token({"sub": str(user.id)})
            
            logger.info(f"User registered successfully: {user.email}")
            return user, access_token, refresh_token
            
        except ValueError as e:
            logger.warning(f"Registration failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during registration: {e}")
            raise

    async def login_user(
        self,
        email: str,
        password: str,
    ) -> Tuple[User, str, str]:
        """
        Authenticate user and return tokens.
        
        Args:
            email: User email
            password: User password (plain text)
            
        Returns:
            Tuple of (User, access_token, refresh_token)
            
        Raises:
            ValueError: If credentials are invalid
        """
        try:
            # Get user by email
            user = await self.repo.get_user_by_email(email)
            
            if not user:
                logger.warning(f"Login failed - user not found: {email}")
                raise ValueError("Invalid email or password")
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"Login failed - user inactive: {email}")
                raise ValueError("User account is inactive")
            
            # Verify password
            if not verify_password(password, user.hashed_password):
                logger.warning(f"Login failed - invalid password: {email}")
                raise ValueError("Invalid email or password")
            
            # Update last login
            await self.repo.update_user(user.id, last_login=None)  # Will be set by DB timestamp
            
            # Generate tokens
            access_token = create_access_token({"sub": str(user.id)})
            refresh_token = create_refresh_token({"sub": str(user.id)})
            
            logger.info(f"User logged in successfully: {email}")
            return user, access_token, refresh_token
            
        except ValueError as e:
            raise
        except Exception as e:
            logger.error(f"Error during login: {e}")
            raise

    async def refresh_access_token(self, refresh_token: str) -> str:
        """
        Generate new access token from refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token
            
        Raises:
            ValueError: If refresh token is invalid
        """
        try:
            payload = decode_refresh_token(refresh_token)
            
            if not payload:
                raise ValueError("Invalid or expired refresh token")
            
            user_id = payload.get("sub")
            
            # Verify user still exists and is active
            user = await self.repo.get_user_by_id(UUID(user_id))
            if not user or not user.is_active:
                logger.warning(f"Refresh token used by inactive/deleted user: {user_id}")
                raise ValueError("User no longer exists or is inactive")
            
            # Create new access token
            new_access_token = create_access_token({"sub": user_id})
            
            logger.debug(f"Access token refreshed for user: {user_id}")
            return new_access_token
            
        except ValueError as e:
            raise
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            raise

    async def change_password(
        self,
        user_id: UUID,
        old_password: str,
        new_password: str,
    ) -> bool:
        """
        Change user password.
        
        Args:
            user_id: User UUID
            old_password: Current password (plain text)
            new_password: New password (plain text)
            
        Returns:
            True if password changed successfully
            
        Raises:
            ValueError: If old password is incorrect
        """
        try:
            user = await self.repo.get_user_by_id(user_id)
            
            if not user:
                logger.warning(f"Password change failed - user not found: {user_id}")
                raise ValueError("User not found")
            
            # Verify old password
            if not verify_password(old_password, user.hashed_password):
                logger.warning(f"Password change failed - invalid old password: {user_id}")
                raise ValueError("Invalid old password")
            
            # Hash new password
            new_hashed_password = hash_password(new_password)
            
            # Update password
            await self.repo.update_user(user_id, hashed_password=new_hashed_password)
            
            logger.info(f"Password changed for user: {user_id}")
            return True
            
        except ValueError as e:
            raise
        except Exception as e:
            logger.error(f"Error changing password for user {user_id}: {e}")
            raise

    async def get_user_profile(self, user_id: UUID) -> Optional[UserResponse]:
        """
        Get user profile information.
        
        Args:
            user_id: User UUID
            
        Returns:
            UserResponse if user found, None otherwise
        """
        try:
            user = await self.repo.get_user_by_id(user_id)
            if not user:
                logger.warning(f"User profile not found: {user_id}")
                return None
            
            return UserResponse.from_orm(user)
            
        except Exception as e:
            logger.error(f"Error getting user profile for {user_id}: {e}")
            return None
