from __future__ import annotations

import secrets
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


PUBLIC_PREFIXES = (
    "/api/health",
    "/static/",
    "/captures/",
)
PUBLIC_EXACT = {"/", "/favicon.ico"}


def generate_token() -> str:
    return secrets.token_urlsafe(24)


def extract_token(request: Request) -> str | None:
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    for header_name in ("x-jarvis-token", "x-api-token"):
        header = request.headers.get(header_name)
        if header:
            return header.strip() or None
    q = request.query_params.get("token")
    return q.strip() if q else None


def is_public_path(path: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    return any(path == p or path.startswith(p) for p in PUBLIC_PREFIXES)


class ApiTokenMiddleware(BaseHTTPMiddleware):
    """api_token doluysa /api/* (health hariç) Bearer / X-Jarvis-Token ister."""

    def __init__(self, app, token_getter: Callable[[], str]):
        super().__init__(app)
        self._token_getter = token_getter

    async def dispatch(self, request: Request, call_next) -> Response:
        expected = (self._token_getter() or "").strip()
        if not expected or is_public_path(request.url.path):
            return await call_next(request)
        got = extract_token(request)
        if not got or not secrets.compare_digest(got, expected):
            return JSONResponse(
                {"detail": "Geçersiz veya eksik API token"},
                status_code=401,
            )
        return await call_next(request)
