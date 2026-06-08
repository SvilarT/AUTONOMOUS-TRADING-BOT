import os

os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("JWT_SECRET", "test-secret-for-browser-session-more-than-thirty-two-characters")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("RUNTIME_ROLE", "api")
os.environ.setdefault("API_EMBED_BOT_MANAGER", "false")

from starlette.requests import Request
from starlette.responses import Response

from services.browser_session_v2 import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME, csrf_tokens_match, set_browser_session_cookies


def build_request(*, cookie: str = "", csrf_header: str = "") -> Request:
    headers = []
    if cookie:
        headers.append((b"cookie", cookie.encode("utf-8")))
    if csrf_header:
        headers.append((b"x-csrf-token", csrf_header.encode("utf-8")))
    scope = {"type": "http", "method": "POST", "path": "/api/bot/start", "headers": headers}
    return Request(scope)


def test_browser_session_sets_httponly_session_and_readable_csrf_cookie():
    response = Response()
    csrf = set_browser_session_cookies(response, "signed-jwt")
    rendered = "\n".join(response.headers.getlist("set-cookie"))
    assert SESSION_COOKIE_NAME in rendered
    assert CSRF_COOKIE_NAME in rendered
    assert "HttpOnly" in rendered
    assert csrf


def test_csrf_requires_matching_cookie_and_header():
    token = "csrf-token"
    assert csrf_tokens_match(build_request(cookie=f"{CSRF_COOKIE_NAME}={token}", csrf_header=token))
    assert not csrf_tokens_match(build_request(cookie=f"{CSRF_COOKIE_NAME}={token}", csrf_header="wrong"))
