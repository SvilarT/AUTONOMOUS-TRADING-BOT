import hmac
import secrets
from typing import Optional

from fastapi import Request, Response

from runtime_config import DEBUG

SESSION_COOKIE_NAME = "atb_session"
CSRF_COOKIE_NAME = "atb_csrf"
SESSION_COOKIE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


def bearer_token_from_request(request: Request) -> Optional[str]:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token.strip()
    return None


def session_token_from_request(request: Request) -> Optional[str]:
    return bearer_token_from_request(request) or request.cookies.get(SESSION_COOKIE_NAME)


def csrf_tokens_match(request: Request) -> bool:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get("X-CSRF-Token")
    return bool(cookie_token and header_token and hmac.compare_digest(cookie_token, header_token))


def set_browser_session_cookies(response: Response, access_token: str) -> str:
    csrf_token = secrets.token_urlsafe(32)
    secure = not DEBUG
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=access_token,
        max_age=SESSION_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=secure,
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=SESSION_COOKIE_MAX_AGE_SECONDS,
        httponly=False,
        secure=secure,
        samesite="strict",
        path="/",
    )
    return csrf_token


def clear_browser_session_cookies(response: Response) -> None:
    secure = not DEBUG
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", secure=secure, samesite="strict")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/", secure=secure, samesite="strict")
