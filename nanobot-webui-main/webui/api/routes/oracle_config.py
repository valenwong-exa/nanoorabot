"""Oracle DB config routes."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from webui.api.deps import get_services, require_admin
from webui.api.gateway import ServiceContainer
from webui.api.models import (
    OracleConfigRequest,
    OracleConfigResponse,
    OracleConnectionTestResponse,
)

router = APIRouter()


def _to_response(svc: ServiceContainer, config) -> OracleConfigResponse:
    return OracleConfigResponse(
        user=config.user,
        password=config.password,
        host=config.host,
        port=config.port,
        serviceName=config.service_name,
        dsn=config.dsn,
        connectString=config.connect_string,
        configPath=str(svc.oracle_config.config_path) if svc.oracle_config.config_path else None,
        updatedAt=config.updated_at,
    )


@router.get("", response_model=OracleConfigResponse)
async def get_oracle_config(
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> OracleConfigResponse:
    try:
        config = svc.oracle_config.load()
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return _to_response(svc, config)


@router.put("", response_model=OracleConfigResponse)
async def save_oracle_config(
    body: OracleConfigRequest,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> OracleConfigResponse:
    try:
        config = svc.oracle_config.save(body.model_dump())
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return _to_response(svc, config)


@router.post("/test", response_model=OracleConnectionTestResponse)
async def test_oracle_connection(
    body: OracleConfigRequest,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> OracleConnectionTestResponse:
    try:
        result = await asyncio.to_thread(svc.oracle_config.test_connection, body.model_dump())
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Oracle connection failed: {exc}",
        ) from exc
    return OracleConnectionTestResponse(
        success=bool(result.get("success")),
        message=str(result.get("message", "")),
        dsn=str(result.get("dsn", "")),
        serverVersion=result.get("server_version"),
        characterSet=result.get("character_set"),
        isRac=result.get("is_rac"),
        isMultitenant=result.get("is_multitenant"),
    )
