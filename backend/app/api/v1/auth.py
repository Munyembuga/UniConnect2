# =============================================================================
# Authentication API Router - v1
# Endpoints for user registration, login, token refresh, profile, etc.
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from loguru import logger

from app.db.session import get_db
from app.services.user import UserService
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
)
from app.core.security import decode_access_token
from app.models.user import UserRole

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _get_token_from_header(authorization: str = None) -> str:
    """Extract bearer token from Authorization header."""
    if not authorization:
        return None
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]


async def get_current_user(
    token: str = Depends(_get_token_from_header),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    """
    Dependency to extract and validate current user from JWT token.
    
    Args:
        token: JWT token from Authorization header
        db: Database session
        
    Returns:
        User UUID
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        return UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================================================
# ROUTES
# ============================================================================

@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="User Registration",
    description="Register a new user account",
)
async def register(
    user_data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Register a new user account.
    
    - **email**: User email address (must be unique)
    - **full_name**: User's full name
    - **password**: Password (minimum 8 characters)
    
    Returns access and refresh tokens on successful registration.
    """
    try:
        service = UserService(db)
        user, access_token, refresh_token = await service.register_user(
            user_data,
            role=UserRole.STUDENT,
        )
        
        return {
            "message": "User registered successfully",
            "user": UserResponse.from_orm(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 1800,
        }
        
    except ValueError as e:
        logger.warning(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate user and return JWT tokens",
)
async def login(
    credentials: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user with email and password.
    
    Returns:
    - access_token: JWT access token (30 minutes expiration)
    - refresh_token: JWT refresh token (7 days expiration)
    - token_type: "bearer"
    - expires_in: Token expiration in seconds
    """
    try:
        service = UserService(db)
        user, access_token, refresh_token = await service.login_user(
            credentials.email,
            credentials.password,
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=1800,  # 30 minutes
        )
        
    except ValueError as e:
        logger.warning(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


@router.post(
    "/refresh-token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Generate a new access token using refresh token",
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Generate a new access token using a valid refresh token.
    
    The refresh token must be valid and not expired.
    """
    try:
        service = UserService(db)
        new_access_token = await service.refresh_access_token(request.refresh_token)
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=request.refresh_token,
            token_type="bearer",
            expires_in=1800,
        )
        
    except ValueError as e:
        logger.warning(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Retrieve authenticated user's profile information",
)
async def get_profile(
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Get the profile of the currently authenticated user.
    
    Requires: Valid JWT access token in Authorization header
    """
    try:
        service = UserService(db)
        user_profile = await service.get_user_profile(current_user_id)
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found",
            )
        
        return user_profile
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile",
        )


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change Password",
    description="Change authenticated user's password",
)
async def change_password(
    request: ChangePasswordRequest,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Change the password of the authenticated user.
    
    Requires: Valid JWT access token in Authorization header
    """
    try:
        service = UserService(db)
        await service.change_password(
            current_user_id,
            request.old_password,
            request.new_password,
        )
        
        return {"message": "Password changed successfully"}
        
    except ValueError as e:
        logger.warning(f"Password change failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        )
