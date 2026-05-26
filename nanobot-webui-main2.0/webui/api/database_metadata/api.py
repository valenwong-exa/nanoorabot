"""FastAPI routes for SQLcl-backed database metadata tree access."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from webui.api.database_metadata.metadata_service import DatabaseMetadataService
from webui.api.deps import get_current_user

router = APIRouter()
service = DatabaseMetadataService()


class OpenDatabaseMetadataRequest(BaseModel):
    connectionId: str
    sqlclConnectionName: str
    displayName: str


class OpenDatabaseMetadataResponse(BaseModel):
    success: bool
    fromCache: bool
    connectionId: str
    tree: dict[str, Any]


class DatabaseMetadataNodeRequest(BaseModel):
    connectionId: str
    sqlclConnectionName: str
    nodeId: str
    nodeType: str
    schemaName: str | None = None


class DatabaseMetadataNodeResponse(BaseModel):
    success: bool
    fromCache: bool
    connectionId: str
    node: dict[str, Any]


@router.post("/open", response_model=OpenDatabaseMetadataResponse)
async def open_database_metadata(
    body: OpenDatabaseMetadataRequest,
    _user: dict[str, Any] = Depends(get_current_user),
) -> OpenDatabaseMetadataResponse:
    try:
        result = await asyncio.to_thread(
            service.open_connection,
            connection_id=body.connectionId,
            sqlcl_connection_name=body.sqlclConnectionName,
            display_name=body.displayName,
        )
        return OpenDatabaseMetadataResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/load-node", response_model=DatabaseMetadataNodeResponse)
async def load_database_metadata_node(
    body: DatabaseMetadataNodeRequest,
    _user: dict[str, Any] = Depends(get_current_user),
) -> DatabaseMetadataNodeResponse:
    try:
        result = await asyncio.to_thread(
            service.load_node,
            connection_id=body.connectionId,
            sqlcl_connection_name=body.sqlclConnectionName,
            node_id=body.nodeId,
            node_type=body.nodeType,
            schema_name=body.schemaName,
        )
        return DatabaseMetadataNodeResponse(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/refresh-node", response_model=DatabaseMetadataNodeResponse)
async def refresh_database_metadata_node(
    body: DatabaseMetadataNodeRequest,
    _user: dict[str, Any] = Depends(get_current_user),
) -> DatabaseMetadataNodeResponse:
    try:
        result = await asyncio.to_thread(
            service.refresh_node,
            connection_id=body.connectionId,
            sqlcl_connection_name=body.sqlclConnectionName,
            node_id=body.nodeId,
            node_type=body.nodeType,
            schema_name=body.schemaName,
        )
        return DatabaseMetadataNodeResponse(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
