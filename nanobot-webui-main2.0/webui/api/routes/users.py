"""Users routes (admin only)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from webui.api.deps import get_user_store, require_admin
from webui.api.models import CreateUserRequest, UserInfo
from webui.api.users import UserStore

router = APIRouter()


@router.get("", response_model=list[UserInfo])
async def list_users(
    _admin: Annotated[dict, Depends(require_admin)],
    user_store: Annotated[UserStore, Depends(get_user_store)],
) -> list[UserInfo]:
    return [UserInfo(**u) for u in user_store.list_users()]


@router.post("", response_model=UserInfo, status_code=201)
async def create_user(
    body: CreateUserRequest,
    _admin: Annotated[dict, Depends(require_admin)],
    user_store: Annotated[UserStore, Depends(get_user_store)],
) -> UserInfo:
    try:
        user = user_store.create_user(body.username, body.password, body.role)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return UserInfo(**user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    current_admin: Annotated[dict, Depends(require_admin)],
    user_store: Annotated[UserStore, Depends(get_user_store)],
) -> None:
    if user_id == current_admin["id"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete your own account")

    target = user_store.get_by_id(user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if target.get("role") == "admin" and user_store.admin_count() <= 1:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot delete the last admin account"
        )

    user_store.delete_user(user_id)
