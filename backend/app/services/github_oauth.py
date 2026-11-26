"""Short-lived GitHub OAuth exchange and installation verification."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings


class GitHubOAuthError(Exception):
    """Raised when GitHub cannot complete or verify OAuth."""


def _request_json(request: Request) -> dict:
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        raise GitHubOAuthError("GitHub authorization could not be verified.") from exc

    if not isinstance(payload, dict):
        raise GitHubOAuthError("GitHub returned an invalid response.")

    return payload


def exchange_github_oauth_code(code: str) -> str:
    """Exchange a one-time authorization code for an in-memory access token."""
    if not settings.GITHUB_APP_CLIENT_ID or not settings.GITHUB_APP_CLIENT_SECRET:
        raise GitHubOAuthError("GitHub OAuth is not configured.")

    body = json.dumps({
        "client_id": settings.GITHUB_APP_CLIENT_ID,
        "client_secret": settings.GITHUB_APP_CLIENT_SECRET.get_secret_value(),
        "code": code,
        "redirect_uri": settings.GITHUB_APP_CALLBACK_URL,
    }).encode("utf-8")

    request = Request(
        "https://github.com/login/oauth/access_token",
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    payload = _request_json(request)
    token = payload.get("access_token")

    if not isinstance(token, str) or not token or payload.get("error"):
        raise GitHubOAuthError("GitHub did not issue an access token.")

    return token


def find_user_installation(access_token: str, installation_id: int) -> dict | None:
    """Find an installation accessible to the authenticated GitHub user."""
    for page in range(1, 101):
        query = urlencode({"per_page": 100, "page": page})

        request = Request(
            f"https://api.github.com/user/installations?{query}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "SherlskyyCommand",
            },
        )

        payload = _request_json(request)
        installations = payload.get("installations")

        if not isinstance(installations, list):
            raise GitHubOAuthError("GitHub returned an invalid installation list.")

        for installation in installations:
            if (
                isinstance(installation, dict)
                and installation.get("id") == installation_id
            ):
                return installation

        if len(installations) < 100:
            return None

    raise GitHubOAuthError("GitHub installation list exceeded the safety limit.")
