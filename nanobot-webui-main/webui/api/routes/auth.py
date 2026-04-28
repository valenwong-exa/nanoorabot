"""Auth routes: login, current user, change password."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from webui.api.auth import create_access_token, verify_password
from webui.api.deps import get_current_user, get_user_store
from webui.api.models import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    UserInfo,
)
from webui.api.users import UserStore

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    user_store: Annotated[UserStore, Depends(get_user_store)],
) -> TokenResponse:
    user = user_store.get_by_username(body.username)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    token = create_access_token(user["id"], user["username"], user["role"])
    return TokenResponse(
        access_token=token,
        user=UserInfo(
            id=user["id"],
            username=user["username"],
            role=user["role"],
            created_at=user["created_at"],
        ),
    )


@router.get("/me", response_model=UserInfo)
async def me(current_user: Annotated[dict, Depends(get_current_user)]) -> UserInfo:
    return UserInfo(
        id=current_user["id"],
        username=current_user["username"],
        role=current_user["role"],
        created_at=current_user["created_at"],
    )


@router.put("/password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    user_store: Annotated[UserStore, Depends(get_user_store)],
) -> None:
    user_store.update_password(current_user["id"], body.new_password)
