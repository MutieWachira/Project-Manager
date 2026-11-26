import pytest

from app.services import github_oauth
from app.services.github_oauth import GitHubOAuthError


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.body


@pytest.mark.parametrize(
    "body",
    [b"[]", b'"unexpected"', b"123", b"true", b"null"],
)
def test_request_json_rejects_non_object_json(monkeypatch, body):
    monkeypatch.setattr(
        github_oauth,
        "urlopen",
        lambda request, timeout: FakeResponse(body),
    )

    with pytest.raises(GitHubOAuthError, match="invalid response"):
        github_oauth._request_json(
            github_oauth.Request("https://example.test")
        )


def test_request_json_returns_object_payload(monkeypatch):
    monkeypatch.setattr(
        github_oauth,
        "urlopen",
        lambda request, timeout: FakeResponse(
            b'{"access_token":"test-token"}'
        ),
    )

    result = github_oauth._request_json(
        github_oauth.Request("https://example.test")
    )

    assert result == {"access_token": "test-token"}


def test_request_json_wraps_invalid_json(monkeypatch):
    monkeypatch.setattr(
        github_oauth,
        "urlopen",
        lambda request, timeout: FakeResponse(b"not-json"),
    )

    with pytest.raises(GitHubOAuthError, match="could not be verified"):
        github_oauth._request_json(
            github_oauth.Request("https://example.test")
        )


def test_find_user_installation_rejects_invalid_installations_field(monkeypatch):
    monkeypatch.setattr(
        github_oauth,
        "urlopen",
        lambda request, timeout: FakeResponse(b'{"installations":{}}'),
    )

    with pytest.raises(GitHubOAuthError, match="invalid installation list"):
        github_oauth.find_user_installation("test-token", 123)
