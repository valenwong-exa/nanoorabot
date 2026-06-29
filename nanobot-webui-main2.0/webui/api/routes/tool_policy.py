"""Dangerous tool policy routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from webui.api.deps import get_services, require_admin
from webui.api.gateway import ServiceContainer
from webui.api.models import ToolPolicyRequest, ToolPolicyResponse

router = APIRouter()


def _to_response(svc: ServiceContainer, config) -> ToolPolicyResponse:
    return ToolPolicyResponse(
        version=config.version,
        name=config.name,
        source=config.source,
        description=config.description,
        rules=config.rules,
        configPath=str(svc.tool_policy.policy_path) if svc.tool_policy.policy_path else None,
        updatedAt=config.updated_at,
    )


@router.get("", response_model=ToolPolicyResponse)
async def get_tool_policy(
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> ToolPolicyResponse:
    try:
        config = svc.tool_policy.load()
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return _to_response(svc, config)


@router.put("", response_model=ToolPolicyResponse)
async def save_tool_policy(
    body: ToolPolicyRequest,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> ToolPolicyResponse:
    try:
        config = svc.tool_policy.save(body.model_dump())
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return _to_response(svc, config)
