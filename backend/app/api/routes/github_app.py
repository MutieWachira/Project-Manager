"""Public GitHub App Setup URL and OAuth callback routes."""

from datetime import UTC, datetime
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import (
    GitHubInstallationState,
    IntegrationStatus,
    IntegrationType,
    Project,
    ProjectIntegration,
    ProjectMember,
    ProjectRole,
    User,
    UserSession,
)
from app.services.github_installation import (
    consume_installation_state_for_callback,
    consume_oauth_state,
    create_oauth_state,
)
from app.services.github_oauth import (
    GitHubOAuthError,
    exchange_github_oauth_code,
    find_user_installation,
)

router = APIRouter(prefix="/github", tags=["GitHub App"])


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _frontend_result(project_id: UUID, result: str) -> RedirectResponse:
    target = (
        f"{settings.FRONTEND_URL.rstrip('/')}/dashboard/projects/{project_id}"
        f"?{urlencode({'github': result})}"
    )
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)


def _validate_initiator(
    db: Session,
    state_record: GitHubInstallationState,
) -> tuple[ProjectIntegration, Project]:
    """Revalidate the initiating account, session, and project permissions."""
    now = datetime.now(UTC)

    user = db.get(User, state_record.user_id)
    session = db.get(UserSession, state_record.session_id)
    project = db.get(Project, state_record.project_id)

    integration = db.scalar(
        select(ProjectIntegration).where(
            ProjectIntegration.id == state_record.integration_id,
            ProjectIntegration.project_id == state_record.project_id,
        )
    )

    if (
        user is None
        or not user.is_active
        or user.email_verified_at is None
        or session is None
        or session.user_id != state_record.user_id
        or session.revoked_at is not None
        or _as_utc(session.expires_at) <= now
        or project is None
        or integration is None
        or integration.integration_type != IntegrationType.GITHUB
    ):
        raise HTTPException(
            status_code=400,
            detail="GitHub authorization is no longer valid.",
        )

    # Project creators are owners; other users need an active manager/owner role.
    if project.created_by_id != user.id:
        membership = db.scalar(
            select(ProjectMember).where(
                ProjectMember.project_id == project.id,
                ProjectMember.user_id == user.id,
            )
        )

        if (
            membership is None
            or membership.role not in (ProjectRole.OWNER, ProjectRole.MANAGER)
        ):
            raise HTTPException(
                status_code=403,
                detail="Project management permission is required.",
            )

    return integration, project


@router.get("/setup", summary="Complete GitHub App installation setup")
def github_setup(
    installation_id: int = Query(gt=0),
    setup_action: str = Query(),
    state: str = Query(min_length=20, max_length=256),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if setup_action not in {"install", "update"}:
        raise HTTPException(status_code=400, detail="Unsupported GitHub setup action.")

    state_record = consume_installation_state_for_callback(db, state)

    if state_record is None:
        raise HTTPException(
            status_code=400,
            detail="GitHub installation state is invalid or expired.",
        )

    # Commit consumption immediately so the installation state cannot be replayed.
    db.commit()

    _validate_initiator(db, state_record)

    oauth_state = create_oauth_state(db, state_record, installation_id)
    db.commit()

    query = urlencode({
        "client_id": settings.GITHUB_APP_CLIENT_ID,
        "redirect_uri": settings.GITHUB_APP_CALLBACK_URL,
        "state": oauth_state,
        "allow_signup": "false",
    })

    return RedirectResponse(
        f"https://github.com/login/oauth/authorize?{query}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/callback", summary="Verify GitHub App installation authorization")
def github_callback(
    state: str = Query(min_length=20, max_length=256),
    code: str | None = Query(default=None, max_length=512),
    error: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    state_record = consume_oauth_state(db, state)

    if state_record is None:
        raise HTTPException(
            status_code=400,
            detail="GitHub OAuth state is invalid or expired.",
        )

    # OAuth state is single-use, including denied or failed attempts.
    db.commit()

    integration, project = _validate_initiator(db, state_record)

    if error or not code or state_record.installation_id is None:
        return _frontend_result(project.id, "error")

    try:
        access_token = exchange_github_oauth_code(code)
        installation = find_user_installation(
            access_token,
            state_record.installation_id,
        )
    except GitHubOAuthError:
        return _frontend_result(project.id, "error")

    # The installation ID is trusted only after GitHub confirms it belongs
    # to this authenticated user and to our configured GitHub App.
    if (
        installation is None
        or str(installation.get("app_id")) != str(settings.GITHUB_APP_ID)
        or not isinstance(installation.get("account"), dict)
    ):
        return _frontend_result(project.id, "error")

    account = installation["account"]
    login = account.get("login")

    if not isinstance(login, str) or not login.strip():
        return _frontend_result(project.id, "error")

    # Store public installation metadata only. Never persist the OAuth token.
    integration.configuration = {
        "github_installation_id": state_record.installation_id,
        "github_account_login": login,
        "github_account_type": account.get("type"),
        "repository_selection": installation.get("repository_selection"),
    }
    integration.external_reference = login
    integration.status = IntegrationStatus.CONNECTED
    integration.last_seen_at = datetime.now(UTC)

    db.commit()
    return _frontend_result(project.id, "connected")
