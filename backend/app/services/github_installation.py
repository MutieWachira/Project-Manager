"""Secure, short-lived state management for GitHub App installations."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import GitHubInstallationState


STATE_TTL = timedelta(minutes=10)


def _hash_state(raw_state: str) -> str:
    """Hash a raw state value before it is stored or queried."""
    return hashlib.sha256(raw_state.encode("utf-8")).hexdigest()


def create_installation_state(
    db: Session,
    *,
    project_id: UUID,
    integration_id: UUID,
    user_id: UUID,
    session_id: UUID,
) -> str:
    """Create a one-time state bound to its initiating user and session.

    The raw value is returned once for the GitHub redirect URL.
    Only its SHA-256 hash is stored in the database.
    """
    raw_state = secrets.token_urlsafe(32)
    now = datetime.now(UTC)

    state_record = GitHubInstallationState(
        project_id=project_id,
        integration_id=integration_id,
        user_id=user_id,
        session_id=session_id,
        state_hash=_hash_state(raw_state),
        expires_at=now + STATE_TTL,
    )

    db.add(state_record)
    db.flush()

    return raw_state


def consume_installation_state(
    db: Session,
    raw_state: str,
    *,
    user_id: UUID,
    session_id: UUID,
) -> GitHubInstallationState | None:
    """Atomically consume a valid state exactly once.

    The caller must commit the transaction immediately after a successful
    result. A failed or mismatched state is not consumed.
    """
    if not raw_state or len(raw_state) > 256:
        return None

    now = datetime.now(UTC)

    statement = (
        update(GitHubInstallationState)
        .where(
            GitHubInstallationState.state_hash == _hash_state(raw_state),
            GitHubInstallationState.user_id == user_id,
            GitHubInstallationState.session_id == session_id,
            GitHubInstallationState.consumed_at.is_(None),
            GitHubInstallationState.expires_at > now,
        )
        .values(consumed_at=now)
        .returning(GitHubInstallationState)
    )

    result = db.execute(statement)
    return result.scalar_one_or_none()


def consume_installation_state_for_callback(
    db: Session, raw_state: str
) -> GitHubInstallationState | None:
    """Atomically consume the browser-returned installation state."""
    if not raw_state or len(raw_state) > 256:
        return None

    now = datetime.now(UTC)
    statement = (
        update(GitHubInstallationState)
        .where(
            GitHubInstallationState.state_hash == _hash_state(raw_state),
            GitHubInstallationState.consumed_at.is_(None),
            GitHubInstallationState.expires_at > now,
        )
        .values(consumed_at=now)
        .returning(GitHubInstallationState)
    )
    return db.execute(statement).scalar_one_or_none()


def create_oauth_state(
    db: Session,
    state_record: GitHubInstallationState,
    installation_id: int,
) -> str:
    """Create a separate one-time state for the OAuth callback."""
    raw_state = secrets.token_urlsafe(32)
    now = datetime.now(UTC)

    state_record.oauth_state_hash = _hash_state(raw_state)
    state_record.oauth_expires_at = now + STATE_TTL
    state_record.oauth_consumed_at = None
    state_record.installation_id = installation_id

    db.flush()
    return raw_state


def consume_oauth_state(
    db: Session, raw_state: str
) -> GitHubInstallationState | None:
    """Atomically consume a valid OAuth callback state exactly once."""
    if not raw_state or len(raw_state) > 256:
        return None

    now = datetime.now(UTC)
    statement = (
        update(GitHubInstallationState)
        .where(
            GitHubInstallationState.oauth_state_hash == _hash_state(raw_state),
            GitHubInstallationState.oauth_consumed_at.is_(None),
            GitHubInstallationState.oauth_expires_at > now,
        )
        .values(oauth_consumed_at=now)
        .returning(GitHubInstallationState)
    )
    return db.execute(statement).scalar_one_or_none()
