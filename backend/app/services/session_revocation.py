"""Authentication session revocation."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.refresh_tokens import hash_refresh_token
from app.models import RefreshToken, UserSession


def revoke_session_by_refresh_token(
    db: Session,
    raw_token: str,
    *,
    expected_client_type: str,
) -> bool:
    """
    Revoke the session associated with a refresh token.

    All refresh tokens belonging to the session are revoked.
    Repeated logout requests for an already-revoked session
    are treated as successful.
    """

    if (
        not isinstance(raw_token, str)
        or not raw_token
        or expected_client_type not in {"web", "mobile"}
    ):
        return False

    try:
        token_record = db.scalar(
            select(RefreshToken)
            .where(RefreshToken.token_hash == hash_refresh_token(raw_token))
            .with_for_update()
        )

        if token_record is None:
            return False

        session = db.scalar(
            select(UserSession)
            .where(UserSession.id == token_record.session_id)
            .with_for_update()
        )

        if session is None:
            return False

        if session.client_type != expected_client_type:
            return False

        now = datetime.now(UTC)

        if session.revoked_at is None:
            session.revoked_at = now
            session.revoke_reason = "user_logout"

        active_tokens = db.scalars(
            select(RefreshToken)
            .where(
                RefreshToken.session_id == session.id,
                RefreshToken.revoked_at.is_(None),
            )
            .with_for_update()
        ).all()

        for existing_token in active_tokens:
            existing_token.revoked_at = now

        db.commit()

        return True

    except Exception:
        db.rollback()
        raise
