"""Authentication API endpoints."""

import logging
from datetime import UTC, datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.tokens import create_session_access_token
from app.services.refresh_token_rotation import (
    InvalidRefreshTokenError,
    rotate_refresh_token,
)
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    MFAChallengeVerifyRequest,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegistrationResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.services.authentication import authenticate_user, register_user
from app.services.email_verification import verify_email_token
from app.services.mfa import get_mfa_status
from app.services.mfa_login_challenges import (
    MFAChallengeError,
    create_mfa_login_challenge,
    verify_mfa_login_challenge,
)
from app.services.sessions import create_user_session
from app.services.session_revocation import revoke_session_by_refresh_token

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
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Authenticate credentials and either require MFA or create a session."""

    try:
        user = authenticate_user(db, credentials)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        mfa_status = get_mfa_status(db, user.id)

        if mfa_status.enabled:
            challenge = create_mfa_login_challenge(
                db,
                user.id,
                client_type=credentials.client_type,
            )

            return LoginResponse(
                mfa_required=True,
                challenge_token=challenge.challenge_token,
                challenge_expires_at=challenge.expires_at,
            )

        created_session = create_user_session(
            db,
            user,
            client_type=credentials.client_type,
            device_name=credentials.device_name,
            user_agent=request.headers.get("user-agent"),
        )

        access_token = create_session_access_token(
            subject=str(user.id),
            session_id=created_session.session_id,
        )

        result = LoginResponse(
            access_token=access_token,
            refresh_token=(
                created_session.refresh_token
                if credentials.client_type == "mobile"
                else None
            ),
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            session_id=str(created_session.session_id),
            session_expires_at=created_session.expires_at,
        )

        if credentials.client_type == "web":
            response.set_cookie(
                key=settings.REFRESH_TOKEN_COOKIE_NAME,
                value=created_session.refresh_token,
                max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
                httponly=True,
                secure=settings.refresh_token_cookie_secure,
                samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
                path=settings.REFRESH_TOKEN_COOKIE_PATH,
            )

        return result

    except HTTPException:
        raise

    except MFAChallengeError as exc:
        logger.warning("MFA challenge creation was rejected.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to complete login.",
        ) from exc

    except Exception as exc:
        logger.exception("Login request failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process your login request.",
        ) from exc


@router.post(
    "/mfa/verify",
    response_model=LoginResponse,
    summary="Verify an MFA login challenge",
)
def verify_mfa_login(
    mfa_request: MFAChallengeVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Complete login after successful authenticator verification."""

    try:
        result = verify_mfa_login_challenge(
            db,
            mfa_request.challenge_token,
            mfa_request.code,
            device_name=mfa_request.device_name,
            user_agent=request.headers.get("user-agent"),
        )

        login_response = LoginResponse(
            mfa_required=False,
            access_token=result.access_token,
            refresh_token=(
                result.refresh_token if result.client_type == "mobile" else None
            ),
            token_type=result.token_type,
            expires_in=result.expires_in,
            session_id=str(result.session_id),
            session_expires_at=result.session_expires_at,
        )

        if result.client_type == "web":
            response.set_cookie(
                key=settings.REFRESH_TOKEN_COOKIE_NAME,
                value=result.refresh_token,
                max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
                httponly=True,
                secure=settings.refresh_token_cookie_secure,
                samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
                path=settings.REFRESH_TOKEN_COOKIE_PATH,
            )

        return login_response

    except MFAChallengeError as exc:
        logger.warning("MFA login verification was rejected.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA verification failed or the challenge has expired.",
        ) from exc

    except Exception as exc:
        logger.exception("MFA login verification request failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to complete MFA login.",
        ) from exc


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Rotate an authentication refresh token",
)
def refresh_session(
    request: Request,
    response: Response,
    refresh_request: RefreshRequest | None = None,
    db: Session = Depends(get_db),
) -> RefreshResponse:
    """Rotate a web-cookie or mobile-body refresh token."""

    cookie_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    body_token = refresh_request.refresh_token if refresh_request is not None else None

    # Never allow clients to submit credentials through both channels.
    if cookie_token and body_token:
        response.delete_cookie(
            key=settings.REFRESH_TOKEN_COOKIE_NAME,
            path=settings.REFRESH_TOKEN_COOKIE_PATH,
            secure=settings.refresh_token_cookie_secure,
            httponly=True,
            samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh request.",
        )

    if cookie_token:
        # Cookie-based refresh is exclusively for the browser client.
        origin = request.headers.get("origin")

        if origin != settings.FRONTEND_URL.rstrip("/"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Request origin is not permitted.",
            )

        raw_token = cookie_token
        expected_client_type = "web"

    elif body_token:
        raw_token = body_token
        expected_client_type = "mobile"

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    try:
        rotated = rotate_refresh_token(
            db,
            raw_token,
            expected_client_type=expected_client_type,
        )

        access_token = create_session_access_token(
            subject=str(rotated.user_id),
            session_id=rotated.session_id,
        )

        result = RefreshResponse(
            access_token=access_token,
            refresh_token=(
                rotated.refresh_token if rotated.client_type == "mobile" else None
            ),
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            session_id=str(rotated.session_id),
            session_expires_at=rotated.session_expires_at,
        )

        if rotated.client_type == "web":
            remaining_seconds = max(
                0,
                int((rotated.expires_at - datetime.now(UTC)).total_seconds()),
            )

            response.set_cookie(
                key=settings.REFRESH_TOKEN_COOKIE_NAME,
                value=rotated.refresh_token,
                max_age=remaining_seconds,
                httponly=True,
                secure=settings.refresh_token_cookie_secure,
                samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
                path=settings.REFRESH_TOKEN_COOKIE_PATH,
            )

        return result

    except InvalidRefreshTokenError as exc:
        response.delete_cookie(
            key=settings.REFRESH_TOKEN_COOKIE_NAME,
            path=settings.REFRESH_TOKEN_COOKIE_PATH,
            secure=settings.refresh_token_cookie_secure,
            httponly=True,
            samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        ) from exc

    except Exception as exc:
        logger.exception("Refresh-token rotation failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to refresh the authentication session.",
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


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Log out and revoke the authentication session",
)
def logout_session(
    request: Request,
    response: Response,
    logout_request: LogoutRequest | None = None,
    db: Session = Depends(get_db),
) -> LogoutResponse:
    """Revoke a web-cookie or mobile-body authentication session."""

    cookie_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    body_token = logout_request.refresh_token if logout_request is not None else None

    # Credentials must be supplied through exactly one channel.
    if cookie_token and body_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid logout request.",
        )

    if cookie_token:
        origin = request.headers.get("origin")

        if origin != settings.FRONTEND_URL.rstrip("/"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Request origin is not permitted.",
            )

        raw_token = cookie_token
        expected_client_type = "web"

    elif body_token:
        raw_token = body_token
        expected_client_type = "mobile"

    else:
        raw_token = None
        expected_client_type = None

    try:
        if raw_token is not None:
            revoke_session_by_refresh_token(
                db,
                raw_token,
                expected_client_type=expected_client_type,
            )

        # Clear the browser cookie using the same path and security
        # attributes used when the cookie was originally created.
        response.delete_cookie(
            key=settings.REFRESH_TOKEN_COOKIE_NAME,
            path=settings.REFRESH_TOKEN_COOKIE_PATH,
            secure=settings.refresh_token_cookie_secure,
            httponly=True,
            samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
        )

        return LogoutResponse(message="You have been logged out.")

    except Exception as exc:
        logger.exception("Authentication session logout failed.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to complete logout.",
        ) from exc
