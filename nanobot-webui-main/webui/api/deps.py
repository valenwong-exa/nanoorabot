"""FastAPI dependency callables."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from webui.api.gateway import ServiceContainer
from webui.api.users import UserStore

_bearer = HTTPBearer(auto_error=False)


async def get_services(request: Request) -> ServiceContainer:
    container: ServiceContainer | None = request.app.state.services
    if container is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Services not initialised")
    return container


async def get_user_store(request: Request) -> UserStore:
    return request.app.state.user_store  # type: ignore[no-any-return]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    user_store: Annotated[UserStore, Depends(get_user_store)],
) -> dict:
    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing authorisation token")

    from webui.api.auth import decode_access_token

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    user = user_store.get_by_id(payload["sub"])
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


async def require_admin(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return current_user
