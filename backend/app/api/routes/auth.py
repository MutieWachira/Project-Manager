"""Authentication API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import (
    RegisterRequest,
    RegistrationResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.services.authentication import register_user
from app.services.email_verification import verify_email_token
from app.schemas.auth import LoginRequest, LoginResponse
from app.services.authentication import authenticate_user
from app.core.config import settings
from app.api.dependencies import get_current_user
from app.models import User
from app.schemas.auth import CurrentUserResponse


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Register a new account",
)
def register(
    registration: RegisterRequest,
    db: Session = Depends(get_db),
) -> RegistrationResponse:
    """Register an account and initiate email verification."""

    try:
        register_user(db, registration)

    except Exception as exc:
        logger.exception("Account registration request failed.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process your registration request.",
        ) from exc

    return RegistrationResponse(
        message=(
            "If your registration can be completed, "
            "check your email for further instructions."
        )
    )


@router.post(
    "/verify-email",
    response_model=VerifyEmailResponse,
    summary="Verify an email address",
)
def verify_email(
    request: VerifyEmailRequest,
    db: Session = Depends(get_db),
) -> VerifyEmailResponse:
    """Verify an account using a valid, single-use email token."""

    try:
        user = verify_email_token(db, request.token)

        if user is None:
            db.rollback()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification link is invalid or has expired.",
            )

        db.commit()

    except HTTPException:
        raise

    except Exception as exc:
        db.rollback()

        logger.exception("Email verification request failed.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to verify your email address.",
        ) from exc

    return VerifyEmailResponse(
        message="Your email address has been successfully verified."
    )

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate an account",
)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Authenticate an account and issue an access token."""

    try:
        access_token = authenticate_user(db, credentials)

        if access_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return LoginResponse(
            access_token=access_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Login request failed.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process your login request.",
        ) from exc

@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Get the current authenticated user",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> CurrentUserResponse:
    """Return the authenticated user's public account information."""

    return CurrentUserResponse(
        id=str(current_user.id),
        full_name=current_user.full_name,
        email=current_user.email,
        is_active=current_user.is_active,
        email_verified=current_user.email_verified_at is not None,
    )
    