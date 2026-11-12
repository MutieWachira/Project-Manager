"""Reusable API dependencies."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tokens import InvalidTokenError, decode_access_token
from app.db.session import get_db
from app.models import User


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the currently authenticated user from a JWT."""

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (InvalidTokenError, ValueError, TypeError):
        raise unauthorized from None

    user = db.scalar(
        select(User).where(User.id == user_id)
    )

    if user is None or not user.is_active:
        raise unauthorized

    return user
