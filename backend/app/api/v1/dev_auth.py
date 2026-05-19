"""
DEV-ONLY auth bypass.

Replaces JWT authentication with a fixed admin user so every endpoint
can be tested in Swagger without registering or logging in first.

HOW TO RE-ENABLE REAL AUTH LATER:
  In any route file, swap:
      current_user_id: UUID = Depends(get_dev_user_id)
  back to:
      current_user_id: UUID = Depends(get_current_user)
"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import Depends
from loguru import logger

from app.db.session import get_db
from app.models.user import User, UserRole
from app.core.security import hash_password

# Fixed UUID that will always represent the "dev admin" test user
DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


async def get_dev_user_id(db: AsyncSession = Depends(get_db)) -> UUID:
    """
    Returns DEV_USER_ID. Creates the dev admin user in the DB if it does not
    exist yet, so the FK constraint on documents.user_id is always satisfied.
    No token / login needed — works directly in Swagger.
    """
    result = await db.execute(select(User).where(User.id == DEV_USER_ID))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=DEV_USER_ID,
            email="dev@uniconnect.local",
            full_name="Dev Admin (Testing)",
            hashed_password=hash_password("devpassword"),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.commit()
        logger.info("Dev admin user created for testing")

    return DEV_USER_ID
