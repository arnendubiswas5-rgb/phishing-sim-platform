"""Middleware that records successful state-changing admin actions.

Any POST/PUT/PATCH/DELETE to /api/v1 that returns a 2xx is written to
audit_logs with the acting user, the action, the resource type, and the
client IP. GETs and non-API paths are ignored.
"""
import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.database import AsyncSessionLocal
from app.models.audit import AuditLog
from app.models.user import User
from app.utils.security import TokenError, decode_access_token

logger = logging.getLogger(__name__)

_API_PREFIX = "/api/v1/"
_METHOD_ACTION = {"POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete"}
# Endpoints that mutate but aren't "admin actions" worth auditing (and, for
# login, have no authenticated user yet).
_SKIP_PATHS = {"/api/v1/auth/login", "/api/v1/auth/refresh"}


def _client_ip(request: Request) -> str | None:
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    return request.client.host if request.client else None


def _resource_from_path(path: str) -> tuple[str, str | None]:
    """/api/v1/campaigns/<id>/launch -> ("campaigns", "<id>")."""
    rest = path[len(_API_PREFIX):] if path.startswith(_API_PREFIX) else path
    segments = [s for s in rest.split("/") if s]
    resource_type = segments[0] if segments else "unknown"
    resource_id = segments[1] if len(segments) > 1 else None
    return resource_type, resource_id


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        action = _METHOD_ACTION.get(request.method)
        path = request.url.path
        if (
            action is None
            or not path.startswith(_API_PREFIX)
            or path in _SKIP_PATHS
            or response.status_code >= 400
        ):
            return response

        # Best-effort: never let audit bookkeeping break the actual request.
        try:
            await self._write_log(request, response.status_code, action, path)
        except Exception:
            logger.exception("Failed to write audit log for %s %s", request.method, path)

        return response

    async def _write_log(self, request: Request, status_code: int, action: str, path: str) -> None:
        user_id: uuid.UUID | None = None
        tenant_id: uuid.UUID | None = None

        auth = request.headers.get("authorization", "")
        token = auth[7:] if auth.lower().startswith("bearer ") else None

        async with AsyncSessionLocal() as db:
            if token:
                try:
                    payload = decode_access_token(token)
                    user_id = uuid.UUID(payload["sub"])
                except (TokenError, KeyError, ValueError):
                    user_id = None
                if user_id is not None:
                    user = await db.get(User, user_id)
                    if user is not None:
                        tenant_id = user.tenant_id
                    else:
                        user_id = None

            resource_type, resource_id = _resource_from_path(path)
            db.add(
                AuditLog(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    method=request.method,
                    path=path,
                    status_code=status_code,
                    ip_address=_client_ip(request),
                )
            )
            await db.commit()
